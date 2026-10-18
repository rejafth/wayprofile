import io
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
TMP = tempfile.mkdtemp()
os.environ["SECRET_KEY"] = "test-secret-key-0123456789"
os.environ["UPLOAD_DIR"] = os.path.join(TMP, "up")

import app as webapp  # noqa: E402
import content  # noqa: E402
import db  # noqa: E402
import manage  # noqa: E402
import sqlite_shim  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


class T(unittest.TestCase):
    def setUp(self):
        sqlite_shim.install(os.path.join(tempfile.mkdtemp(), "t.db"))
        db.init()
        for n in content.SECTIONS:
            db.seed_section(n, json.dumps(content.DEFAULTS[n]))
        db.put_admin("admin", generate_password_hash("kata-sandi-kuat-1"))
        webapp.FAILS.clear()
        self.c = webapp.app.test_client()

    def token(self):
        self.c.get("/admin/login")
        with self.c.session_transaction() as s:
            return s["csrf"]

    def login(self, pw="kata-sandi-kuat-1", user="admin"):
        return self.c.post("/admin/login", data={"csrf": self.token(), "username": user, "password": pw})

    def h(self):
        with self.c.session_transaction() as s:
            return {"X-CSRF-Token": s["csrf"]}

    def put(self, name, data):
        return self.c.put("/admin/api/content/" + name, json=data, headers=self.h())

    # --- publik ---
    def test_public_page(self):
        r = self.c.get("/")
        self.assertEqual(r.status_code, 200)
        t = r.get_data(as_text=True)
        for s in ["Warajaya", "Solve Techindo", "Kamera IP 4 MP", "Pemkot Surabaya", "Lihat katalog", "wa.me/6285156315663"]:
            self.assertIn(s, t)
        self.assertIn("nonce-", r.headers["Content-Security-Policy"])
        self.assertEqual(self.c.get("/healthz").get_data(as_text=True), "ok")
        self.assertIn("Disallow: /admin", self.c.get("/robots.txt").get_data(as_text=True))
        self.assertEqual(self.c.get("/static/site.css").status_code, 200)
        self.assertEqual(self.c.get("/static/default-logo.png").status_code, 200)

    def test_public_survives_db_down(self):
        def boom():
            raise RuntimeError("down")
        orig = db.connect
        db.connect = boom
        try:
            self.assertEqual(self.c.get("/").status_code, 200)
        finally:
            db.connect = orig

    def test_defaults_valid(self):
        for n in content.SECTIONS:
            self.assertEqual(content.clean(n, content.DEFAULTS[n]), content.DEFAULTS[n])

    # --- auth ---
    def test_api_requires_login(self):
        self.assertEqual(self.c.get("/admin/api/content").status_code, 401)
        self.assertEqual(self.c.get("/admin").status_code, 302)

    def test_login_flow(self):
        self.assertEqual(self.login("salah").status_code, 401)
        self.assertEqual(self.login(user="nobody").status_code, 401)
        r = self.login()
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.c.get("/admin").status_code, 200)
        self.assertIn("Dashboard admin", self.c.get("/admin").get_data(as_text=True))
        self.assertEqual(self.c.get("/admin/api/content").status_code, 200)
        self.c.post("/admin/logout", data={"csrf": self.h()["X-CSRF-Token"]})
        self.assertEqual(self.c.get("/admin/api/content").status_code, 401)

    def test_login_csrf(self):
        self.token()
        r = self.c.post("/admin/login", data={"csrf": "x", "username": "admin", "password": "kata-sandi-kuat-1"})
        self.assertEqual(r.status_code, 400)

    def test_lockout(self):
        for _ in range(5):
            self.login("salah")
        self.assertEqual(self.login().status_code, 429)

    def test_api_csrf_required(self):
        self.login()
        r = self.c.put("/admin/api/content/hero", json=content.DEFAULTS["hero"])
        self.assertEqual(r.status_code, 403)

    # --- simpan & validasi ---
    def test_save_changes_public(self):
        self.login()
        site = dict(content.DEFAULTS["site"], company_name="Nama Baru Perusahaan", slogan="Slogan Baru", color_accent="#ff0000")
        self.assertEqual(self.put("site", site).status_code, 200)
        t = self.c.get("/").get_data(as_text=True)
        self.assertIn("Nama", t)
        self.assertIn("Slogan Baru", t)
        self.assertIn("--accent:#ff0000", t)

    def test_products_featured_and_xss(self):
        self.login()
        p = json.loads(json.dumps(content.DEFAULTS["products"]))
        p["items"].append({"category": "Baru", "name": "<script>alert(1)</script>", "price": 1234567, "price_label": "Harga",
                           "points": ["a", "b"], "featured": True, "image": ""})
        self.assertEqual(self.put("products", p).status_code, 200)
        t = self.c.get("/").get_data(as_text=True)
        self.assertNotIn("<script>alert(1)</script>", t)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", t)
        self.assertIn("Rp1.234.567", t)

    def test_validation_errors(self):
        self.login()
        bad_color = dict(content.DEFAULTS["site"], color_accent="red")
        self.assertEqual(self.put("site", bad_color).status_code, 400)
        bad_link = dict(content.DEFAULTS["hero"], btn1_link="javascript:alert(1)")
        self.assertEqual(self.put("hero", bad_link).status_code, 400)
        bad_img = dict(content.DEFAULTS["site"], logo="http://evil.example/x.png")
        self.assertEqual(self.put("site", bad_img).status_code, 400)
        trav = dict(content.DEFAULTS["site"], logo="/uploads/../secret")
        self.assertEqual(self.put("site", trav).status_code, 400)
        req = dict(content.DEFAULTS["hero"], title="  ")
        self.assertEqual(self.put("hero", req).status_code, 400)
        self.assertEqual(self.put("nonexistent", {}).status_code, 404)
        self.assertEqual(self.c.put("/admin/api/content/hero", data="x", headers=self.h()).status_code, 400)
        bad_wa = dict(content.DEFAULTS["contact"], whatsapp="12")
        self.assertEqual(self.put("contact", bad_wa).status_code, 400)

    def test_control_chars_removed(self):
        self.login()
        r = self.put("hero", dict(content.DEFAULTS["hero"], title="Judul\x00Uji", tags=["a\x00b", "c"]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["data"]["title"], "JudulUji")
        self.assertEqual(r.get_json()["data"]["tags"], ["ab", "c"])

    def test_reset(self):
        self.login()
        self.put("hero", dict(content.DEFAULTS["hero"], title="Judul Lain"))
        self.assertIn("Judul Lain", self.c.get("/").get_data(as_text=True))
        r = self.c.post("/admin/api/reset/hero", headers=self.h())
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("Judul Lain", self.c.get("/").get_data(as_text=True))

    # --- upload ---
    def test_upload(self):
        self.login()
        r = self.c.post("/admin/api/upload", data={"file": (io.BytesIO(PNG), "a.png")}, headers=self.h(), content_type="multipart/form-data")
        self.assertEqual(r.status_code, 200)
        url = r.get_json()["url"]
        self.assertTrue(url.startswith("/uploads/") and url.endswith(".png"))
        self.assertEqual(self.c.get(url).status_code, 200)
        self.assertEqual(self.put("site", dict(content.DEFAULTS["site"], logo=url)).status_code, 200)
        svg = self.c.post("/admin/api/upload", data={"file": (io.BytesIO(b"<svg onload=alert(1)>"), "a.svg")}, headers=self.h(), content_type="multipart/form-data")
        self.assertEqual(svg.status_code, 400)
        big = self.c.post("/admin/api/upload", data={"file": (io.BytesIO(PNG + b"0" * (6 * 1024 * 1024)), "b.png")}, headers=self.h(), content_type="multipart/form-data")
        self.assertEqual(big.status_code, 413)
        self.assertEqual(self.c.get("/uploads/../app.py").status_code, 404)

    # --- password ---
    def test_password_change(self):
        self.login()
        h = self.h()
        self.assertEqual(self.c.post("/admin/api/password", json={"current": "salah", "new": "passwordbaru123"}, headers=h).status_code, 400)
        self.assertEqual(self.c.post("/admin/api/password", json={"current": "kata-sandi-kuat-1", "new": "pendek"}, headers=h).status_code, 400)
        self.assertEqual(self.c.post("/admin/api/password", json={"current": "kata-sandi-kuat-1", "new": "passwordbaru123"}, headers=h).status_code, 200)
        self.c.post("/admin/logout", data={"csrf": h["X-CSRF-Token"]})
        self.assertEqual(self.login("kata-sandi-kuat-1").status_code, 401)
        self.assertEqual(self.login("passwordbaru123").status_code, 302)

    def test_manage_create_admin(self):
        import getpass
        orig = getpass.getpass
        getpass.getpass = lambda prompt="": "sandi-admin-baru-1"
        try:
            self.assertEqual(manage.main(["manage.py", "create-admin", "budi"]), 0)
            self.assertEqual(manage.main(["manage.py", "create-admin", "x"]), 1)
            self.assertEqual(manage.main(["manage.py", "init-db"]), 0)
            self.assertEqual(manage.main(["manage.py", "check-db"]), 0)
        finally:
            getpass.getpass = orig
        self.assertEqual(self.login("sandi-admin-baru-1", "budi").status_code, 302)


if __name__ == "__main__":
    unittest.main(verbosity=2)
