"""Website profil perusahaan + dashboard admin. Jalankan lewat gunicorn: gunicorn app:app"""
import datetime
import functools
import hmac
import json
import os
import secrets
import time
from urllib.parse import quote

from flask import Flask, Response, g, jsonify, redirect, render_template, request, send_from_directory, session
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

import content
import db

BASE = os.path.dirname(os.path.abspath(__file__))
db.load_env()
UPLOAD_DIR = os.environ.get("UPLOAD_DIR") or os.path.join(BASE, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_IMG = 5 * 1024 * 1024

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", ""),
    MAX_CONTENT_LENGTH=MAX_IMG + 512 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE") == "1",
    PERMANENT_SESSION_LIFETIME=datetime.timedelta(hours=12),
)
if len(app.config["SECRET_KEY"]) < 16:
    raise RuntimeError("SECRET_KEY belum diisi atau terlalu pendek (lihat file .env)")
if os.environ.get("TRUST_PROXY", "1") == "1":
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

DUMMY_HASH = generate_password_hash(secrets.token_hex(8))
FAILS = {}


# ---------- helpers ----------
def asset(name):
    p = os.path.join(BASE, "static", name)
    return "/static/%s?v=%d" % (name, int(os.path.getmtime(p)) if os.path.exists(p) else 0)


def wa_link(number, text=""):
    return "https://wa.me/%s?text=%s" % (number, quote(text)) if number else "#kontak"


def pairs(lines):
    out = []
    for line in lines or []:
        a, _, b = line.partition("|")
        out.append((a.strip(), b.strip()))
    return out


def initials(name):
    return "".join(w[0] for w in name.split()[:2]).upper() or "?"


app.jinja_env.globals.update(asset=asset, wa_link=wa_link, pairs=pairs, initials=initials)
app.jinja_env.filters["rupiah"] = lambda n: "Rp" + format(int(n), ",").replace(",", ".")


def load_all(strict=False):
    try:
        stored = db.fetch_sections()
    except Exception:
        if strict:
            raise
        app.logger.exception("Database tidak terbaca, memakai isi bawaan")
        stored = {}
    return {n: content.merge(n, stored.get(n)) for n in content.SECTIONS}


@app.before_request
def _nonce():
    g.nonce = secrets.token_urlsafe(16)


@app.after_request
def _headers(r):
    r.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'nonce-%s' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; script-src 'self'; connect-src 'self'; object-src 'none'; "
        "base-uri 'self'; form-action 'self'; frame-ancestors 'none'" % getattr(g, "nonce", ""))
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["X-Frame-Options"] = "DENY"
    r.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.path.startswith("/admin"):
        r.headers["Cache-Control"] = "no-store"
    return r


# ---------- publik ----------
@app.get("/")
def index():
    c = load_all()
    words = c["site"]["company_name"].split(None, 1)
    cats = []
    for p in c["products"]["items"]:
        if p["category"] not in cats:
            cats.append(p["category"])
    return render_template(
        "index.html", nonce=g.nonce, theme_css=content.theme_css(c["site"]), year=datetime.date.today().year,
        name1=words[0] if words else "", name2=words[1] if len(words) > 1 else "", cats=cats, **c)


@app.get("/uploads/<path:name>")
def uploads(name):
    resp = send_from_directory(UPLOAD_DIR, name, max_age=86400)
    return resp


@app.get("/robots.txt")
def robots():
    return Response("User-agent: *\nDisallow: /admin\n", mimetype="text/plain")


@app.get("/healthz")
def healthz():
    return "ok"


@app.errorhandler(404)
def _404(e):
    return "Halaman tidak ditemukan.", 404


@app.errorhandler(413)
def _413(e):
    return jsonify(error="File terlalu besar (maksimal 5 MB)."), 413


# ---------- login ----------
def _locked(ip):
    n, until = FAILS.get(ip, (0, 0))
    if until and until <= time.time():
        FAILS.pop(ip, None)
        return False
    return until > time.time()


def _fail(ip):
    n, _ = FAILS.get(ip, (0, 0))
    n += 1
    FAILS[ip] = (n, time.time() + 300 if n >= 5 else 0)


def _login_page(error=None, status=200):
    session["csrf"] = session.get("csrf") or secrets.token_urlsafe(24)
    site = load_all()["site"]
    html = render_template("login.html", error=error, csrf=session["csrf"], logo=site["logo"], brand=site["brand_name"])
    return html, status


@app.get("/admin/login")
def login_form():
    if session.get("u"):
        return redirect("/admin")
    return _login_page()


@app.post("/admin/login")
def login():
    ip = request.remote_addr or "?"
    token = request.form.get("csrf", "")
    if not session.get("csrf") or not hmac.compare_digest(token, session["csrf"]):
        session.clear()
        return _login_page("Sesi formulir berakhir. Silakan coba lagi.", 400)
    if _locked(ip):
        return _login_page("Terlalu banyak percobaan. Coba lagi 5 menit lagi.", 429)
    user = request.form.get("username", "").strip()[:64]
    pw = request.form.get("password", "")[:256]
    try:
        row = db.get_admin(user)
    except Exception:
        app.logger.exception("Gagal membaca akun admin")
        return _login_page("Database tidak dapat dihubungi. Periksa konfigurasi server.", 503)
    ok = check_password_hash(row[1] if row else DUMMY_HASH, pw) and row is not None
    if not ok:
        _fail(ip)
        return _login_page("Username atau kata sandi salah.", 401)
    FAILS.pop(ip, None)
    session.clear()
    session["u"] = row[0]
    session["csrf"] = secrets.token_urlsafe(24)
    session.permanent = True
    return redirect("/admin")


@app.post("/admin/logout")
def logout():
    if session.get("csrf") and hmac.compare_digest(request.form.get("csrf", ""), session["csrf"]):
        session.clear()
    return redirect("/admin/login")


@app.get("/admin")
def dashboard():
    if not session.get("u"):
        return redirect("/admin/login")
    site = load_all()["site"]
    return render_template("admin.html", csrf=session["csrf"], user=session["u"], logo=site["logo"],
                           brand=site["brand_name"], schema={"order": content.ORDER, "sections": content.SECTIONS})


# ---------- API admin ----------
def api(fn):
    @functools.wraps(fn)
    def wrapper(*a, **k):
        if not session.get("u"):
            return jsonify(error="Sesi berakhir, silakan login lagi."), 401
        if request.method != "GET" and not hmac.compare_digest(request.headers.get("X-CSRF-Token", ""), session.get("csrf", "")):
            return jsonify(error="Token keamanan tidak cocok. Muat ulang halaman."), 403
        return fn(*a, **k)
    return wrapper


@app.get("/admin/api/content")
@api
def api_content():
    try:
        return jsonify(content=load_all(strict=True))
    except Exception:
        app.logger.exception("Gagal membaca database")
        return jsonify(error="Database tidak dapat dihubungi."), 500


@app.put("/admin/api/content/<name>")
@api
def api_save(name):
    if name not in content.SECTIONS:
        return jsonify(error="Bagian tidak dikenal."), 404
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Data tidak valid."), 400
    try:
        cleaned = content.clean(name, data)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    try:
        db.save_section(name, json.dumps(cleaned, ensure_ascii=False))
    except Exception:
        app.logger.exception("Gagal menyimpan")
        return jsonify(error="Gagal menyimpan ke database."), 500
    return jsonify(data=content.merge(name, cleaned))


@app.post("/admin/api/reset/<name>")
@api
def api_reset(name):
    if name not in content.SECTIONS:
        return jsonify(error="Bagian tidak dikenal."), 404
    try:
        db.save_section(name, json.dumps(content.DEFAULTS[name], ensure_ascii=False))
    except Exception:
        app.logger.exception("Gagal mengembalikan bawaan")
        return jsonify(error="Gagal menyimpan ke database."), 500
    return jsonify(data=content.merge(name, None))


def _sniff(b):
    if b.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if b.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if b[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        return ".webp"
    return None


@app.post("/admin/api/upload")
@api
def api_upload():
    f = request.files.get("file")
    if not f:
        return jsonify(error="Tidak ada file."), 400
    data = f.read(MAX_IMG + 1)
    if len(data) > MAX_IMG:
        return jsonify(error="File terlalu besar (maksimal 5 MB)."), 413
    ext = _sniff(data)
    if not ext:
        return jsonify(error="Format harus PNG, JPG, GIF, atau WEBP."), 400
    name = secrets.token_hex(10) + ext
    with open(os.path.join(UPLOAD_DIR, name), "wb") as out:
        out.write(data)
    return jsonify(url="/uploads/" + name)


@app.post("/admin/api/password")
@api
def api_password():
    d = request.get_json(silent=True) or {}
    cur, new = d.get("current"), d.get("new")
    if not isinstance(cur, str) or not isinstance(new, str):
        return jsonify(error="Data tidak valid."), 400
    if len(new) < 10 or len(new) > 256:
        return jsonify(error="Kata sandi baru minimal 10 karakter."), 400
    try:
        row = db.get_admin(session["u"])
        if not row or not check_password_hash(row[1], cur):
            return jsonify(error="Kata sandi saat ini salah."), 400
        db.put_admin(session["u"], generate_password_hash(new))
    except Exception:
        app.logger.exception("Gagal mengganti kata sandi")
        return jsonify(error="Database tidak dapat dihubungi."), 500
    return jsonify(ok=True)
