"""Skema isi website, validasi input admin, dan perhitungan warna tema."""
import copy
import json
import os
import re
from urllib.parse import urlparse

BASE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE, "defaults.json"), encoding="utf-8") as _f:
    DEFAULTS = json.load(_f)


def F(k, label, t="text", **o):
    d = {"k": k, "label": label, "type": t}
    d.update(o)
    return d


SCENES = [["rack", "Rak server dan jaringan"], ["browser", "Tampilan website"], ["dash", "Dasbor atau sistem"]]
ORDER = ["site", "hero", "about", "services", "products", "projects", "clients", "contact"]
SECTIONS = {
    "site": {"label": "Umum, Logo, dan Warna", "kind": "object",
             "desc": "Nama perusahaan, slogan, logo, warna, dan pengaturan mesin pencari.",
             "fields": [
                 F("brand_name", "Nama merek (singkat)", req=1, help="Dipakai di footer dan teks alternatif logo."),
                 F("company_name", "Nama perusahaan di header", req=1, help="Kata pertama berwarna utama, sisanya berwarna hijau."),
                 F("legal_name", "Nama badan usaha", help="Tampil di footer dan bagian kontak."),
                 F("slogan", "Slogan di bawah nama perusahaan"),
                 F("logo", "Logo", "image", help="Disarankan PNG transparan, lebar sekitar 400 px."),
                 F("favicon", "Ikon tab browser (favicon)", "image", help="Kosongkan untuk memakai logo."),
                 F("color_accent", "Warna aksen (tombol dan sorotan)", "color"),
                 F("color_green", "Warna kedua (hijau)", "color"),
                 F("color_brand", "Warna judul dan merek", "color"),
                 F("cta_label", "Teks tombol di menu atas"),
                 F("footer", "Teks footer"),
                 F("meta_title", "Judul halaman untuk Google", max=120),
                 F("meta_description", "Deskripsi halaman untuk Google", "textarea", max=300)]},
    "hero": {"label": "Bagian Utama (Hero)", "kind": "object",
             "desc": "Judul besar di halaman depan, tombol, dan gambar samping.",
             "fields": [
                 F("title", "Judul", req=1), F("text", "Penjelasan singkat", "textarea"),
                 F("btn1_label", "Tombol 1: teks"), F("btn1_link", "Tombol 1: tautan", "link"),
                 F("btn2_label", "Tombol 2: teks"), F("btn2_link", "Tombol 2: tautan", "link"),
                 F("tags", "Label di bawah gambar", "lines", help="Satu baris satu label."),
                 F("image", "Gambar hero (opsional)", "image", help="Kosongkan untuk memakai ilustrasi bawaan.")]},
    "about": {"label": "Tentang Perusahaan", "kind": "object",
              "desc": "Profil singkat dan nilai perusahaan.",
              "fields": [
                  F("title", "Judul", req=1), F("text", "Isi", "textarea"), F("button_label", "Teks tombol"),
                  F("pillars", "Nilai perusahaan", "lines", help="Satu baris: Judul | Keterangan")]},
    "services": {"label": "Layanan", "kind": "list", "items_label": "Daftar layanan", "item_name": "layanan", "title_key": "title",
                 "desc": "Kartu layanan yang tampil di halaman depan.",
                 "head": [F("title", "Judul bagian", req=1), F("subtitle", "Kalimat pengantar", "textarea")],
                 "item": [F("title", "Nama layanan", req=1), F("points", "Poin layanan", "lines", help="Satu baris satu poin."),
                          F("badge", "Lencana (opsional)", help="Contoh: Segera hadir")]},
    "products": {"label": "Katalog Produk dan Paket", "kind": "list", "items_label": "Daftar produk", "item_name": "produk", "title_key": "name",
                 "desc": "Produk bertanda unggulan tampil di depan. Sisanya muncul lewat tombol Lihat Produk Lainnya.",
                 "head": [F("title", "Judul bagian", req=1), F("subtitle", "Kalimat pengantar", "textarea"),
                          F("note", "Catatan di bawah katalog", "textarea"),
                          F("more_label", "Teks tombol buka semua"), F("less_label", "Teks tombol tutup"),
                          F("btn_label", "Teks tombol pesan"), F("wa_text", "Awal pesan WhatsApp")],
                 "item": [F("category", "Kategori", req=1, max=60), F("name", "Nama produk", req=1),
                          F("price", "Harga (angka rupiah, 0 = Hubungi kami)", "number"),
                          F("price_label", "Label harga", help="Contoh: Harga atau Mulai dari"),
                          F("points", "Spesifikasi atau isi paket", "lines", help="Satu baris satu poin."),
                          F("featured", "Tampilkan di depan (unggulan)", "bool"),
                          F("image", "Foto produk (opsional)", "image")]},
    "projects": {"label": "Portofolio", "kind": "list", "items_label": "Daftar proyek", "item_name": "proyek", "title_key": "title",
                 "desc": "Unggah foto pengerjaan. Tanpa foto, tampil ilustrasi bawaan.",
                 "head": [F("title", "Judul bagian", req=1), F("subtitle", "Kalimat pengantar", "textarea"),
                          F("note", "Catatan di bawah portofolio", "textarea")],
                 "item": [F("title", "Nama proyek", req=1), F("description", "Keterangan"),
                          F("image", "Foto proyek", "image"),
                          F("scene", "Ilustrasi bila tanpa foto", "select", options=SCENES),
                          F("color", "Warna ilustrasi", "color")]},
    "clients": {"label": "Dipercaya Oleh", "kind": "list", "items_label": "Daftar klien", "item_name": "klien", "title_key": "name",
                "desc": "Instansi dan perusahaan yang sudah memakai jasa Anda.",
                "head": [F("title", "Judul bagian", req=1)],
                "item": [F("name", "Nama klien", req=1), F("sector", "Sektor dan proyek"),
                         F("initials", "Inisial (opsional)", max=3), F("logo", "Logo klien (opsional)", "image")]},
    "contact": {"label": "Kontak", "kind": "object",
                "desc": "Nomor WhatsApp, Instagram, alamat, dan jam layanan.",
                "fields": [
                    F("title", "Judul", req=1), F("text", "Kalimat pengantar", "textarea"),
                    F("whatsapp", "Nomor WhatsApp (format 62...)", "digits", help="Hanya angka, contoh: 6285156315663"),
                    F("whatsapp_display", "Tampilan nomor", help="Contoh: +62 851 5631 5663"),
                    F("wa_message", "Pesan awal WhatsApp"), F("wa_button", "Teks tombol WhatsApp"),
                    F("instagram", "Instagram (tanpa @)", "handle"), F("email", "Email", "email"),
                    F("address", "Alamat", "textarea"), F("hours", "Jam layanan")]},
}


_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _val(f, v, pos):
    t, label = f["type"], f["label"]
    where = " (item %d)" % pos if pos else ""
    if t == "bool":
        return v is True
    if t == "number":
        if isinstance(v, bool):
            raise ValueError('"%s" harus berupa angka%s.' % (label, where))
        try:
            n = int(float(v if v not in (None, "") else 0))
        except (TypeError, ValueError):
            raise ValueError('"%s" harus berupa angka%s.' % (label, where))
        if not 0 <= n <= 10 ** 12:
            raise ValueError('"%s" di luar batas%s.' % (label, where))
        return n
    if t == "lines":
        if isinstance(v, str):
            v = v.splitlines()
        if not isinstance(v, list):
            v = []
        out = [re.sub(r"\s+", " ", _CTRL.sub("", str(x))).strip() for x in v]
        out = [x for x in out if x]
        if len(out) > 30 or any(len(x) > 200 for x in out):
            raise ValueError('"%s" terlalu banyak atau terlalu panjang%s.' % (label, where))
        return out
    s = "" if v is None else (v if isinstance(v, str) else str(v))
    s = _CTRL.sub("", s)
    if t == "textarea":
        s = s.replace("\r\n", "\n").strip()
        mx = f.get("max", 2000)
    else:
        s = re.sub(r"\s+", " ", s).strip()
        mx = f.get("max", 300)
    if len(s) > mx:
        raise ValueError('"%s" terlalu panjang (maks %d karakter)%s.' % (label, mx, where))
    if t == "color":
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", s):
            raise ValueError('"%s" harus berupa kode warna seperti #19a1c8%s.' % (label, where))
        s = s.lower()
    elif t == "image":
        if s and (not re.fullmatch(r"/(uploads|static)/[A-Za-z0-9_./-]+", s) or ".." in s):
            raise ValueError('"%s" tidak valid. Unggah gambar lewat tombol unggah%s.' % (label, where))
    elif t == "link":
        if s:
            ok = (s[0] in "#/" and not s.startswith("//") and " " not in s)
            if not ok:
                p = urlparse(s)
                ok = (p.scheme in ("http", "https") and bool(p.netloc)) or (p.scheme in ("mailto", "tel") and bool(p.path))
            if not ok:
                raise ValueError('"%s" bukan tautan yang valid%s.' % (label, where))
    elif t == "digits":
        s = re.sub(r"\D", "", s)
        if s and not 8 <= len(s) <= 15:
            raise ValueError('"%s" harus 8-15 angka%s.' % (label, where))
    elif t == "handle":
        s = s.lstrip("@")
        if not re.fullmatch(r"[A-Za-z0-9_.]{0,30}", s):
            raise ValueError('"%s" hanya boleh huruf, angka, titik, dan garis bawah%s.' % (label, where))
    elif t == "email":
        if s and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", s):
            raise ValueError('"%s" bukan email yang valid%s.' % (label, where))
    elif t == "select":
        valid = [o[0] for o in f["options"]]
        if s not in valid:
            s = valid[0]
    if f.get("req") and not s:
        raise ValueError('"%s" wajib diisi%s.' % (label, where))
    return s


def _obj(fields, d, pos=None):
    if not isinstance(d, dict):
        raise ValueError("Data tidak valid.")
    return {f["k"]: _val(f, d.get(f["k"]), pos) for f in fields}


def clean(name, data):
    sec = SECTIONS[name]
    if sec["kind"] == "object":
        return _obj(sec["fields"], data)
    out = _obj(sec["head"], data)
    items = data.get("items")
    if not isinstance(items, list) or len(items) > 200:
        raise ValueError("Daftar item tidak valid (maks 200).")
    out["items"] = [_obj(sec["item"], it, i + 1) for i, it in enumerate(items) if isinstance(it, dict)]
    return out


def merge(name, stored):
    d = copy.deepcopy(DEFAULTS[name])
    if isinstance(stored, dict):
        d.update(stored)
    return d


def _rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def _hex(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(x))) for x in c)


def mix(a, b, t):
    return _hex([x + (y - x) * t for x, y in zip(_rgb(a), _rgb(b))])


def _lum(h):
    def f(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = _rgb(h)
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def on(h):
    return "#0b1a22" if _lum(h) > 0.3 else "#ffffff"


def theme_css(site):
    a, g, b = site["color_accent"], site["color_green"], site["color_brand"]
    navy_d = mix(a, "#ffffff", 0.2)
    light = ("--accent:%s;--on-accent:%s;--green:%s;--on-green:%s;--brand:%s;--navy:%s;--on-navy:%s;--gt:%s;--panel:%s"
             % (a, on(a), g, on(g), b, b, on(b), mix(g, "#000000", 0.3), mix(b, "#000000", 0.18)))
    dark = "--navy:%s;--on-navy:%s;--gt:%s;--panel:%s" % (navy_d, on(navy_d), mix(g, "#ffffff", 0.3), mix(b, "#000000", 0.35))
    return ":root{%s}@media (prefers-color-scheme:dark){:root{%s}}" % (light, dark)
