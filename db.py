"""Akses database PostgreSQL. Semua SQL memakai sintaks umum (juga jalan di SQLite untuk pengujian)."""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))


def load_env():
    """Baca file .env (KEY=VALUE) bila ada. Variabel yang sudah diset tidak ditimpa."""
    try:
        with open(os.path.join(BASE, ".env"), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    except OSError:
        pass


def connect():
    import psycopg

    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL belum diisi (lihat file .env)")
    return psycopg.connect(url, autocommit=True)


def init():
    with open(os.path.join(BASE, "schema.sql"), encoding="utf-8") as f:
        statements = [s.strip() for s in f.read().split(";") if s.strip()]
    with connect() as c:
        for s in statements:
            c.execute(s)


def fetch_sections():
    with connect() as c:
        rows = c.execute("SELECT section, data FROM site_content").fetchall()
    out = {}
    for name, data in rows:
        try:
            out[name] = json.loads(data)
        except ValueError:
            continue
    return out


def save_section(name, data_json):
    with connect() as c:
        c.execute(
            "INSERT INTO site_content (section, data) VALUES (%s, %s) "
            "ON CONFLICT (section) DO UPDATE SET data = EXCLUDED.data, updated_at = CURRENT_TIMESTAMP",
            (name, data_json),
        )


def seed_section(name, data_json):
    with connect() as c:
        c.execute(
            "INSERT INTO site_content (section, data) VALUES (%s, %s) ON CONFLICT (section) DO NOTHING",
            (name, data_json),
        )


def delete_section(name):
    with connect() as c:
        c.execute("DELETE FROM site_content WHERE section = %s", (name,))


def get_admin(username):
    with connect() as c:
        return c.execute(
            "SELECT username, password_hash FROM admins WHERE username = %s", (username,)
        ).fetchone()


def put_admin(username, password_hash):
    with connect() as c:
        c.execute(
            "INSERT INTO admins (username, password_hash) VALUES (%s, %s) "
            "ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash",
            (username, password_hash),
        )


def check():
    with connect() as c:
        s = c.execute("SELECT COUNT(*) FROM site_content").fetchone()[0]
        a = c.execute("SELECT COUNT(*) FROM admins").fetchone()[0]
    return "Koneksi OK. Bagian konten: %d, akun admin: %d" % (s, a)
