"""Mesh "lite": sealed claims carried phone to phone (fake Member 2, no network)."""
import base64
import json
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import config, mesh
from app.whatsapp import Member2Error

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def keys():
    return mesh.new_keys()


class FakeMember2:
    def __init__(self):
        self.calls = []
        self.down = False

    async def create_claim(self, language, consent_text_version=None):
        if self.down:
            raise Member2Error(503, "down")
        self.calls.append(("create", language, consent_text_version))
        return {"id": f"AL-M{len(self.calls)}", "claim_token": "tok"}

    async def update_fields(self, claim_id, token, fields):
        if "bogus" in fields:
            raise Member2Error(422, "unknown field")
        self.calls.append(("fields", fields))

    async def upload_audio(self, claim_id, token, data, ctype):
        self.calls.append(("audio", data, ctype))

    async def upload_photo(self, claim_id, token, data, ctype, lat, lon, taken_at=None):
        self.calls.append(("photo", data, lat, lon, taken_at))

    async def submit(self, claim_id, token):
        self.calls.append(("submit", claim_id))


@pytest.fixture
def m2(monkeypatch, keys):
    monkeypatch.setattr(config, "MESH_PRIVATE_KEY", keys[0])
    monkeypatch.setattr(config, "MESH_RECEIPT_KEY", keys[1])
    fake = FakeMember2()
    mesh.set_member2(fake)
    yield fake
    mesh.set_member2(None)


def client():
    from app.main import app
    return TestClient(app)


def pubkey():
    return client().get("/mesh/public-key").json()


PAYLOAD = {"consent": True, "consent_text_version": "v1", "language": "bn",
           "fields": {"name": "Rina Das", "village": "Satbhaya"},
           "audio": {"data": base64.b64encode(b"webm-voice").decode(), "content_type": "audio/webm"},
           "photos": [{"data": base64.b64encode(b"jpeg-bytes").decode(), "content_type": "image/jpeg",
                       "lat": 19.81, "lon": 85.83, "taken_at": "2026-11-20T09:00:00+05:30"}],
           "submit": True}


def sealed(payload=PAYLOAD, **kw):
    return mesh.seal(payload, pubkey()["public_key_spki"], kw.pop("claim_id", str(uuid4())), **kw)


def post(env):
    return client().post("/mesh/envelopes", json=env)


def test_public_key_and_limits(m2):
    k = pubkey()
    assert k["alg"] == "RSA-OAEP-256+A256GCM" and k["receipt_alg"] == "Ed25519"
    assert k["max_payload_bytes"] == 1572864 and k["ttl_seconds"] == 604800   # Member-5/rules/mesh_policy.json
    assert "private" not in json.dumps(k).lower()


def test_valid_envelope_becomes_claim_with_signed_receipt(m2):
    env = sealed()
    r = post(env)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "submitted"
    assert ("create", "bn", "v1") in m2.calls
    assert ("fields", {"name": "Rina Das", "village": "Satbhaya"}) in m2.calls
    assert ("audio", b"webm-voice", "audio/webm") in m2.calls
    assert ("photo", b"jpeg-bytes", 19.81, 85.83, "2026-11-20T09:00:00+05:30") in m2.calls
    receipt = body["receipt"]
    assert receipt["claim_id"] == env["claim_id"] and receipt["reference"] == "AL-M1"
    assert receipt["message"] == "Your claim reached the relief office"
    assert mesh.verify_receipt(receipt, pubkey()["receipt_public_key"])
    assert client().get(f"/mesh/receipts/{env['claim_id']}").json()["signature"]


def test_forged_receipt_fails_verification(m2):
    receipt = post(sealed()).json()["receipt"]
    assert not mesh.verify_receipt({**receipt, "received_at": "2030-01-01T00:00:00Z"}, pubkey()["receipt_public_key"])


def test_tampered_header_rejected(m2):
    env = sealed(priority="normal")
    r = post({**env, "priority": "urgent"})         # a relay tries to jump the queue
    assert r.status_code == 400 and "changed on the way" in r.json()["detail"]
    assert m2.calls == []


def test_tampered_ciphertext_rejected(m2):
    env = sealed()
    ct = bytearray(base64.b64decode(env["ct"]))
    ct[10] ^= 1
    assert post({**env, "ct": base64.b64encode(bytes(ct)).decode()}).status_code == 400
    assert m2.calls == []


def test_envelope_for_another_server_rejected(m2):
    other_private, _ = mesh.new_keys()
    from cryptography.hazmat.primitives import serialization
    pub = serialization.load_der_private_key(base64.b64decode(other_private), None).public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    env = mesh.seal(PAYLOAD, base64.b64encode(pub).decode(), str(uuid4()))
    assert post(env).status_code == 400


def test_expired_envelope_rejected(m2):
    old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(timespec="seconds")
    r = post(sealed(created_at=old))
    assert r.status_code == 410 and m2.calls == []


def test_future_envelope_rejected(m2):
    soon = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(timespec="seconds")
    assert post(sealed(created_at=soon)).status_code == 400


def test_oversized_envelope_rejected(m2):
    env = sealed()
    big = {**env, "ct": base64.b64encode(b"x" * (mesh.max_payload() + 1000)).decode()}
    assert post(big).status_code == 413 and m2.calls == []


def test_duplicate_envelope_filed_once(m2):
    env = sealed()
    first, second = post(env).json(), post(env).json()
    assert second["status"] == "duplicate"
    assert second["receipt"]["reference"] == first["receipt"]["reference"]
    assert [c for c in m2.calls if c[0] == "create"] == [("create", "bn", "v1")]


def test_missing_consent_rejected(m2):
    r = post(sealed({**PAYLOAD, "consent": False}))
    assert r.status_code == 422 and m2.calls == []


def test_invalid_field_dropped_others_kept(m2):
    post(sealed({**PAYLOAD, "fields": {"name": "Rina", "bogus": 1}, "submit": False}))
    assert ("fields", {"name": "Rina"}) in m2.calls


def test_member2_down_keeps_envelope_for_retry(m2):
    env = sealed()
    m2.down = True
    r = post(env)
    assert r.status_code == 503 and r.headers["retry-after"] == "60"
    assert client().get(f"/mesh/receipts/{env['claim_id']}").status_code == 404
    m2.down = False
    assert post(env).json()["status"] == "submitted"


def test_bad_envelopes_rejected(m2):
    assert client().post("/mesh/envelopes", content=b"not json").status_code == 400
    assert post({"v": 2}).status_code == 400
    assert post({**sealed(), "claim_id": "../../etc"}).status_code == 400
    assert post({**sealed(), "priority": "vip"}).status_code == 400


def test_mesh_off_without_keys(monkeypatch):
    monkeypatch.setattr(config, "MESH_PRIVATE_KEY", "")
    assert client().get("/mesh/public-key").status_code == 503
    assert client().post("/mesh/envelopes", json={}).status_code == 503


def test_cors_lets_member4_app_post(m2):
    r = client().options("/mesh/envelopes", headers={"Origin": "http://localhost:5173",
                                                     "Access-Control-Request-Method": "POST",
                                                     "Access-Control-Request-Headers": "content-type"})
    assert r.status_code == 200 and r.headers["access-control-allow-origin"] == "http://localhost:5173"


# ---------------------------------------------------------------- the real browser helper (Node)

NODE_SCRIPT = """
import { sealClaim, envelopeText, parseEnvelope, verifyReceipt } from %s;
const key = JSON.parse(process.argv[2]);
if (process.argv[3]) {
  console.log(JSON.stringify({ ok: await verifyReceipt(JSON.parse(process.argv[3]), key) }));
} else {
  const env = await sealClaim(%s, key, { priority: "urgent" });
  const { text, fitsInQr } = envelopeText(env);
  console.log(JSON.stringify({ env: parseEnvelope(text), fitsInQr }));
}
"""


@pytest.mark.skipif(not shutil.which("node"), reason="Node.js not installed")
def test_browser_helper_seals_envelopes_the_server_opens(m2, tmp_path):
    js_url = json.dumps((ROOT / "offline-client" / "mesh.js").resolve().as_uri())
    payload = {"consent": True, "language": "hi", "fields": {"name": "Ramesh"}, "submit": True}
    script = tmp_path / "seal.mjs"
    script.write_text(NODE_SCRIPT % (js_url, json.dumps(payload)), encoding="utf-8")
    key = json.dumps(pubkey())
    out = json.loads(subprocess.run(["node", str(script), key], capture_output=True, text=True,
                                    check=True, timeout=60).stdout)
    assert out["fitsInQr"] is True                  # a text-only claim fits in one QR code
    r = post(out["env"])
    assert r.status_code == 200, r.text
    assert ("fields", {"name": "Ramesh"}) in m2.calls and r.json()["status"] == "submitted"
    ok = json.loads(subprocess.run(["node", str(script), key, json.dumps(r.json()["receipt"])],
                                   capture_output=True, text=True, check=True, timeout=60).stdout)
    assert ok == {"ok": True}                       # the phone can verify the server's receipt
