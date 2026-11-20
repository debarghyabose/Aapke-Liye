"""Saved results of every /verify call (SQLite), for the dashboard and duplicate checks.

Without this the service forgot everything on restart: the dashboard had no data and a
photo re-used after a restart was not caught as a duplicate.
"""
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
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
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""

# Columns added after the first release: created on older databases at startup.
LATER_COLUMNS = {
    "phone_hash": "TEXT",               # keyed fingerprint of the phone number, never the number
    "nearby_claims": "TEXT",            # JSON [{"claim_id", "distance_m"}]: possibly the same house
    "phone_other_claims": "INTEGER",    # other claims from the same phone in the last 24 h
    "in_flood": "INTEGER",              # satellite flood map: 1 inside, 0 outside, NULL no map here
    "flood_distance_km": "REAL",        # distance to the mapped flooding
    "flood_map": "TEXT",                # which flood map file was used
    "building_found": "INTEGER",        # building map: 1 found, 0 none nearby, NULL no data
    "building_distance_m": "REAL",
    "satellite_damage_grade": "TEXT",   # e.g. Copernicus EMS grading: Destroyed / Damaged / ...
}


class Store:
    def __init__(self, path: str):
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._db.executescript(SCHEMA)
            have = {r["name"] for r in self._db.execute("PRAGMA table_info(photo_checks)")}
            for col, kind in LATER_COLUMNS.items():
                if col not in have:
                    self._db.execute(f"ALTER TABLE photo_checks ADD COLUMN {col} {kind}")
            self._db.commit()
        self._phone_key = self._load_phone_key()

    # ------------------------------------------------------------ phone fingerprints

    def _load_phone_key(self) -> bytes:
        """HMAC key for phone fingerprints: PHONE_HASH_KEY from .env, else a random key
        made once and kept in this database. Without a key, 10-digit numbers could be
        recovered from plain hashes by trying them all."""
        if config.PHONE_HASH_KEY:
            return config.PHONE_HASH_KEY.encode()
        with self._lock:
            row = self._db.execute("SELECT value FROM meta WHERE key = 'phone_key'").fetchone()
            if row:
                return bytes.fromhex(row["value"])
            key = secrets.token_bytes(32)
            self._db.execute("INSERT INTO meta (key, value) VALUES ('phone_key', ?)", (key.hex(),))
            self._db.commit()
            return key

    def phone_fingerprint(self, phone: Optional[str]) -> Optional[str]:
        """Same number in any format (+91, spaces, dashes) -> same fingerprint."""
        digits = re.sub(r"\D", "", phone or "")
        if len(digits) < 10:
            return None
        return hmac.new(self._phone_key, digits[-10:].encode(), hashlib.sha256).hexdigest()

    # ------------------------------------------------------------ fraud lookups

    def nearby_other_claims(self, lat: Optional[float], lon: Optional[float], claim_id: Optional[str],
                            radius_m: float) -> list[dict]:
        """Other claims with a photo located within radius_m. Closest first.
        A full scan is fine for a demo; with many claims use PostGIS (ST_DWithin)."""
        if lat is None or lon is None:
            return []
        from app.exif_check import distance_km

        with self._lock:
            rows = self._db.execute(
                "SELECT claim_id, lat, lon FROM photo_checks WHERE lat IS NOT NULL AND claim_id IS NOT NULL "
                "AND (? IS NULL OR claim_id != ?)", (claim_id, claim_id)).fetchall()
        best: dict[str, float] = {}
        for r in rows:
            d = distance_km(lat, lon, r["lat"], r["lon"]) * 1000
            if d <= radius_m and d < best.get(r["claim_id"], float("inf")):
                best[r["claim_id"]] = d
        return [{"claim_id": c, "distance_m": round(d, 1)} for c, d in sorted(best.items(), key=lambda x: x[1])]

    def other_claims_for_phone(self, fingerprint: Optional[str], claim_id: Optional[str],
                               hours: float = 24) -> list[str]:
        if not fingerprint:
            return []
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(timespec="seconds")
        with self._lock:
            rows = self._db.execute(
                "SELECT DISTINCT claim_id FROM photo_checks WHERE phone_hash = ? AND checked_at >= ? "
                "AND claim_id IS NOT NULL AND (? IS NULL OR claim_id != ?)",
                (fingerprint, since, claim_id, claim_id)).fetchall()
        return [r["claim_id"] for r in rows]

    # ------------------------------------------------------------ rows

    def record(self, **row) -> None:
        row = {**row, "notes": json.dumps(row.get("notes", []), ensure_ascii=False),
               "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        if "nearby_claims" in row:
            row["nearby_claims"] = json.dumps(row["nearby_claims"] or [])
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
            d["nearby_claims"] = json.loads(d.get("nearby_claims") or "[]")
            d.pop("phone_hash", None)  # never leaves the service
            for k in ("gps_ok", "timestamp_ok"):
                d[k] = bool(d[k])
            for k in ("real_photo", "in_flood", "building_found"):
                d[k] = None if d.get(k) is None else bool(d[k])
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
