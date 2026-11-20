"""Saved results of every /verify call (SQLite), for the dashboard and duplicate checks.

Without this the service forgot everything on restart: the dashboard had no data and a
photo re-used after a restart was not caught as a duplicate.
"""
import json
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional

from app import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS photo_checks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id        TEXT,
    lat             REAL,
    lon             REAL,
    gps_source      TEXT,            -- exif | phone | none
    gps_mismatch_km REAL,            -- photo GPS vs phone GPS, when both exist
    gps_ok          INTEGER NOT NULL,
    timestamp_ok    INTEGER NOT NULL,
    damage_type     TEXT NOT NULL,
    severity        REAL NOT NULL,   -- 0..1
    sdrf_category   TEXT,
    real_photo      INTEGER,         -- 1, 0 or NULL (not assessed)
    duplicate_of    TEXT,            -- other claim_id with the same photo
    hash_distance   INTEGER,         -- 0 = identical, higher = less alike
    phash           TEXT NOT NULL,   -- perceptual hash (hex)
    notes           TEXT NOT NULL,   -- JSON list
    checked_at      TEXT NOT NULL    -- UTC ISO 8601
);
CREATE INDEX IF NOT EXISTS ix_checks_claim ON photo_checks (claim_id);
"""


class Store:
    def __init__(self, path: str):
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._db.executescript(SCHEMA)

    def record(self, **row) -> None:
        row = {**row, "notes": json.dumps(row.get("notes", []), ensure_ascii=False),
               "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        cols = ", ".join(row)
        marks = ", ".join(f":{k}" for k in row)
        with self._lock:
            self._db.execute(f"INSERT INTO photo_checks ({cols}) VALUES ({marks})", row)
            self._db.commit()

    def all_checks(self) -> list[dict]:
        with self._lock:
            rows = self._db.execute("SELECT * FROM photo_checks ORDER BY id").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["notes"] = json.loads(d["notes"])
            for k in ("gps_ok", "timestamp_ok"):
                d[k] = bool(d[k])
            d["real_photo"] = None if d["real_photo"] is None else bool(d["real_photo"])
            out.append(d)
        return out

    def hashes(self) -> list[tuple[str, Optional[str]]]:
        with self._lock:
            return [(r["phash"], r["claim_id"]) for r in
                    self._db.execute("SELECT phash, claim_id FROM photo_checks").fetchall()]


_store: Optional[Store] = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store(config.DB_PATH)
    return _store


def set_store(store: Store) -> None:
    """For tests."""
    global _store
    _store = store
