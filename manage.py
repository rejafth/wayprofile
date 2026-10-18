"""Perintah pengelolaan: init-db, check-db, create-admin <username>."""
import getpass
import json
import re
import sys

from werkzeug.security import generate_password_hash

import content
import db

db.load_env()


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    try:
        if cmd == "init-db":
            db.init()
            for name in content.SECTIONS:
                db.seed_section(name, json.dumps(content.DEFAULTS[name], ensure_ascii=False))
            print("Database siap. Isi bawaan website sudah dimasukkan.")
        elif cmd == "check-db":
            print(db.check())
        elif cmd == "create-admin":
            user = argv[2] if len(argv) > 2 else input("Username: ").strip()
            if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", user):
                print("Username 3-32 karakter: huruf, angka, titik, minus, garis bawah.")
                return 1
            p1 = getpass.getpass("Kata sandi (min. 10 karakter): ")
            if len(p1) < 10:
                print("Kata sandi minimal 10 karakter.")
                return 1
            if p1 != getpass.getpass("Ulangi kata sandi: "):
                print("Kata sandi tidak sama.")
                return 1
            db.put_admin(user, generate_password_hash(p1))
            print("Akun admin '%s' tersimpan." % user)
        else:
            print("Pemakaian: python manage.py init-db | check-db | create-admin [username]")
            return 1
    except Exception as e:  # noqa: BLE001
        print("Gagal: %s" % e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
