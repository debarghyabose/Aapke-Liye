"""Phase 2: tokens, staff keys, consent, uploads, encryption at rest, rate limits, audit."""
import json
import re
import sqlite3
from pathlib import Path

import pytest

from app.security import limiter
from conftest import CONSENT, DB_FILE, JPEG, STAFF, STORAGE, WEBM, new_claim, submitted_claim

PNG = b"\x89PNG\r\n\x1a\n" + b"fake-png"


def test_claim_id_is_long_and_random(client):
    ids = {new_claim(client)[0] for _ in range(3)}
    assert len(ids) == 3
    assert all(re.fullmatch(r"AL-[A-Z2-7]{12}", i) for i in ids)


@pytest.mark.parametrize("headers", [{}, {"X-Claim-Token": "wrong"}])
def test_token_required_everywhere(client, headers):
    cid, _ = new_claim(client)
    calls = [
        ("get", f"/claims/{cid}", {}),
        ("patch", f"/claims/{cid}", {"json": {"fields": {"phone": "9800000000"}}}),
        ("post", f"/claims/{cid}/audio", {"files": {"audio": ("a.webm", WEBM, "audio/webm")}}),
        ("post", f"/claims/{cid}/audio/retry", {}),
        ("post", f"/claims/{cid}/photos", {"files": {"photo": ("p.jpg", JPEG, "image/jpeg")}}),
        ("post", f"/claims/{cid}/photos/1/reverify", {}),
        ("post", f"/claims/{cid}/submit", {}),
        ("get", f"/claims/{cid}/pdf", {}),
        ("get", f"/status/{cid}", {}),
    ]
    for method, url, kwargs in calls:
        r = getattr(client, method)(url, headers=headers, **kwargs)
        assert r.status_code == 404, (method, url, r.status_code)
        assert r.json()["detail"] == "Claim not found"   # same as a claim that doesn't exist
    assert client.get("/claims/AL-AAAAAAAAAAAA", headers=headers).json() == r.json()


def test_token_of_another_claim_is_rejected(client):
    cid, _ = new_claim(client)
    _, other = new_claim(client)
    assert client.get(f"/claims/{cid}", headers=other).status_code == 404


def test_staff_key_required_for_status_change(client):
    cid, h = new_claim(client)
    body = {"status": "Rejected"}
    assert client.put(f"/status/{cid}", json=body).status_code == 401
    assert client.put(f"/status/{cid}", json=body, headers={"X-Staff-Key": "nope"}).status_code == 401
    assert client.put(f"/status/{cid}", json=body, headers=h).status_code == 401  # claim token ≠ staff
    assert _audit_rows(cid, "status_changed") == []


@pytest.mark.parametrize("body", [
    {"language": "bn"},
    {"language": "bn", "consent": False, "consent_text_version": "v1"},
    {"language": "bn", "consent": True},
    {"language": "bn", "consent": True, "consent_text_version": ""},
])
def test_consent_required(client, body):
    assert client.post("/claims", json=body).status_code == 422


def test_consent_is_stored(client):
    cid, h = new_claim(client)
    claim = client.get(f"/claims/{cid}", headers=h).json()
    assert claim["consent_text_version"] == "v1" and claim["consent_given_at"]


def test_upload_too_large(client):
    cid, h = new_claim(client)
    big = b"\x1a\x45\xdf\xa3" + b"0" * (15 * 1024 * 1024)
    r = client.post(f"/claims/{cid}/audio", headers=h, files={"audio": ("a.webm", big, "audio/webm")})
    assert r.status_code == 413
    big = b"\xff\xd8\xff" + b"0" * (10 * 1024 * 1024)
    r = client.post(f"/claims/{cid}/photos", headers=h, files={"photo": ("p.jpg", big, "image/jpeg")})
    assert r.status_code == 413
    huge = b"0" * (17 * 1024 * 1024)      # rejected from Content-Length before parsing
    r = client.post(f"/claims/{cid}/photos", headers=h, files={"photo": ("p.jpg", huge, "image/jpeg")})
    assert r.status_code == 413


@pytest.mark.parametrize("field, name, data, ctype", [
    ("photo", "p.txt", b"hello", "text/plain"),                       # type not allowed
    ("photo", "p.jpg", b"MZ\x90\x00 windows exe", "image/jpeg"),      # magic bytes wrong
    ("photo", "p.jpg", WEBM, "image/jpeg"),                           # audio posing as photo
    ("audio", "a.webm", JPEG, "audio/webm"),                          # photo posing as audio
    ("audio", "a.exe", b"MZ\x90\x00", "application/octet-stream"),
])
def test_upload_wrong_type(client, field, name, data, ctype):
    cid, h = new_claim(client)
    url = f"/claims/{cid}/{'photos' if field == 'photo' else 'audio'}"
    assert client.post(url, headers=h, files={field: (name, data, ctype)}).status_code == 415


def test_path_traversal_filename_is_ignored_and_files_are_encrypted(client):
    cid, h = new_claim(client)
    secret = b"\xff\xd8\xff\xe0 UNIQUE-PLAINTEXT-MARKER"
    r = client.post(f"/claims/{cid}/photos", headers=h,
                    files={"photo": ("../../../evil.jpg", secret, "image/jpeg")})
    assert r.status_code == 200
    storage = Path(STORAGE)
    assert not (storage.parent / "evil.jpg").exists()
    names = [p.name for p in (storage / "photos").iterdir()]
    assert all(re.fullmatch(r"[0-9a-f]{32}", n) for n in names)        # uuid names only
    assert all(b"UNIQUE-PLAINTEXT-MARKER" not in p.read_bytes()
               for p in (storage / "photos").iterdir())                 # encrypted at rest


def test_max_photos_per_claim(client):
    cid, h = new_claim(client)
    for i in range(10):
        r = client.post(f"/claims/{cid}/photos", headers=h,
                        files={"photo": ("p.png", PNG + bytes([i]), "image/png")})
        assert r.status_code == 200
    r = client.post(f"/claims/{cid}/photos", headers=h,
                    files={"photo": ("p.png", PNG + b"x", "image/png")})
    assert r.status_code == 409


def test_rate_limit_on_create(client):
    limiter.enabled = True
    limiter.reset()
    try:
        codes = [client.post("/claims", json={"language": "bn", **CONSENT}).status_code
                 for _ in range(11)]
    finally:
        limiter.enabled = False
    assert codes[:10] == [201] * 10 and codes[10] == 429


def test_audit_log_records_actions_without_personal_data(client):
    cid, h = new_claim(client)
    client.post(f"/claims/{cid}/audio", headers=h, files={"audio": ("a.webm", WEBM, "audio/webm")})
    client.patch(f"/claims/{cid}", headers=h, json={"fields": {"phone": "9800000000"}})
    client.get(f"/claims/{cid}", headers=h)
    client.put(f"/status/{cid}", headers=STAFF, json={"status": "Rejected"})

    with sqlite3.connect(DB_FILE) as db:
        rows = db.execute("SELECT actor, action, detail FROM audit_log WHERE claim_id = ?",
                          (cid,)).fetchall()
    actions = [a for _, a, _ in rows]
    for expected in ["claim_created", "audio_uploaded", "audio_processed", "fields_edited",
                     "claim_viewed"]:
        assert expected in actions
    text = json.dumps(rows)
    for personal in ["Rina", "9800000000", "Gosaba", "Parganas"]:
        assert personal not in text


def _audit_rows(cid, action):
    with sqlite3.connect(DB_FILE) as db:
        return db.execute("SELECT actor FROM audit_log WHERE claim_id = ? AND action = ?",
                          (cid, action)).fetchall()


def test_staff_label_is_logged(client):
    cid, _ = submitted_claim(client)
    assert client.put(f"/status/{cid}", headers=STAFF, json={"status": "Verified"}).status_code == 200
    assert _audit_rows(cid, "status_changed") == [("staff:officer-test",)]
