# Website Waysolve + Dashboard Admin

Website profil perusahaan (Flask) dengan dashboard admin untuk mengatur semua isinya: logo, nama perusahaan, slogan,
warna, hero, tentang, layanan, katalog produk, portofolio (dengan foto), klien, dan kontak.
Data disimpan di PostgreSQL, foto di folder `uploads/`. Dijalankan lewat gunicorn di belakang nginx.

## Pasang di Ubuntu (nginx + PostgreSQL)

```bash
# 1. Paket
sudo apt update && sudo apt install -y python3-venv python3-pip postgresql nginx unzip

# 2. Database (ganti GANTI_SANDI_DB dengan sandi huruf dan angka saja)
sudo -u postgres psql -c "CREATE USER waysolve WITH PASSWORD 'GANTI_SANDI_DB';"
sudo -u postgres psql -c "CREATE DATABASE waysolve OWNER waysolve;"

# 3. Pasang aplikasi
sudo unzip waysolve-cms.zip -d /opt/ && sudo mv /opt/waysolve-cms /opt/waysolve
cd /opt/waysolve
sudo python3 -m venv venv
sudo venv/bin/pip install -r requirements.txt

# 4. Pengaturan: isi SECRET_KEY dan sandi database di .env
sudo cp .env.example .env
python3 -c "import secrets; print(secrets.token_hex(32))"     # salin hasilnya ke SECRET_KEY
sudo nano .env
sudo chown -R www-data:www-data /opt/waysolve
sudo chmod 600 /opt/waysolve/.env

# 5. Siapkan database dan akun admin
sudo -u www-data venv/bin/python manage.py check-db
sudo -u www-data venv/bin/python manage.py init-db
sudo -u www-data venv/bin/python manage.py create-admin admin

# 6. Jalankan sebagai layanan
sudo cp deploy/waysolve.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now waysolve
curl http://127.0.0.1:8000/healthz        # harus menjawab: ok

# 7. nginx (ganti waysolve.example dengan domain Anda)
sudo cp deploy/nginx-waysolve.conf /etc/nginx/sites-available/waysolve
sudo nano /etc/nginx/sites-available/waysolve
sudo ln -s /etc/nginx/sites-available/waysolve /etc/nginx/sites-enabled/waysolve
sudo nginx -t && sudo systemctl reload nginx
```

Website: `http://domain-anda/`  Dashboard: `http://domain-anda/admin`

## HTTPS (disarankan, wajib sebelum dipakai umum)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d domain-anda
sudo sed -i 's/^COOKIE_SECURE=0/COOKIE_SECURE=1/' /opt/waysolve/.env
sudo systemctl restart waysolve
```

## Pemakaian sehari-hari

- Masuk di `/admin`, pilih bagian di menu kiri, ubah, lalu klik **Simpan**. Website langsung berubah.
- **Kembalikan bawaan** mengembalikan satu bagian ke isi awal.
- Foto: PNG, JPG, GIF, atau WEBP, maksimal 5 MB. Portofolio tanpa foto memakai ilustrasi bawaan.
- Produk bertanda **unggulan** tampil di depan, sisanya muncul lewat tombol Lihat Produk Lainnya.
- Lupa kata sandi: jalankan lagi `sudo -u www-data venv/bin/python manage.py create-admin NAMA_ADMIN`.
- Log: `sudo journalctl -u waysolve -f`

## Cadangan dan pembaruan

```bash
sudo -u postgres pg_dump waysolve > waysolve-$(date +%F).sql     # database
sudo tar czf uploads-$(date +%F).tgz -C /opt/waysolve uploads    # foto
sudo systemctl restart waysolve                                    # setelah mengubah kode atau .env
```

## Pengujian

`python3 -m unittest discover -s tests -v` (butuh Flask saja; memakai SQLite sebagai pengganti sementara PostgreSQL).
