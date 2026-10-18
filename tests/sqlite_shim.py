"""Pengganti sementara koneksi PostgreSQL dengan SQLite, hanya untuk pengujian otomatis."""
import sqlite3

import db


class _Conn:
    def __init__(self, path):
        self.c = sqlite3.connect(path)

    def execute(self, sql, params=()):
        return self.c.execute(sql.replace("%s", "?"), params)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.c.commit()
        self.c.close()


def install(path):
    db.connect = lambda: _Conn(path)
