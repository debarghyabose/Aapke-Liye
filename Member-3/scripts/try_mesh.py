"""Act out the mesh on this computer: phone A seals a claim offline, phone B delivers it.

Before running: Member 2 on port 8000 and Member 3 on port 8002 with the mesh keys
(scripts/make_mesh_keys.py). Then, from Member-3/:
    python scripts/try_mesh.py            # text-only claim (fits in one QR code)
    python scripts/try_mesh.py --photo    # with a damage photo (too big for a QR code: shared as a file)

Set STAFF_KEY (one of Member 2's STAFF_API_KEYS) to also see the claim as an official would.
"""
import argparse
import base64
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import config  # noqa: E402
from app.mesh import seal, verify_receipt  # noqa: E402

QR_MAX_CHARS = 2800          # same limit as offline-client/mesh.js
PHOTO = ROOT / "data" / "demo" / "stage" / "puri_flooded_home.jpg"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8002")
    ap.add_argument("--photo", action="store_true", help="include a damage photo")
    args = ap.parse_args()

    print("📶 Phone A, earlier while online: downloads the server's mesh key")
    r = httpx.get(f"{args.url}/mesh/public-key", timeout=10)
    if r.status_code != 200:
        sys.exit(f"Mesh not available ({r.status_code}): {r.text[:200]}")
    key = r.json()

    payload = {"consent": True, "consent_text_version": "mesh-v1", "language": "en",
               "fields": {"name": "Mesh Demo Claimant", "phone": "+91 90000 54321", "village": "Satbhaya",
                          "district": "Puri", "state": "Odisha", "date_of_incident": "2026-11-15",
                          "losses": [{"category": "house", "item": "fully_damaged_plain"}]},
               "submit": True}
    if args.photo:
        payload["photos"] = [{"data": base64.b64encode(PHOTO.read_bytes()).decode(), "content_type": "image/jpeg"}]
    env = seal(payload, key["public_key_spki"], str(uuid4()), priority="urgent")
    text = json.dumps(env)
    print(f"\n✈️  Phone A, airplane mode: seals claim {env['claim_id']} ({len(text):,} characters)")
    print("   → shows it as a QR code" if len(text) <= QR_MAX_CHARS else "   → too big for a QR code: shares it as a file")
    print(f"   A relay sees only: priority={env['priority']}, created_at={env['created_at']}; the rest is sealed")

    print("\n🚶 Phone B carries it, gets signal, delivers:")
    r = httpx.post(f"{args.url}/mesh/envelopes", content=text,
                   headers={"Content-Type": "application/json"}, timeout=120)
    print(f"   HTTP {r.status_code}: {r.json().get('status') or r.json()}")
    if r.status_code != 200:
        return
    receipt = r.json()["receipt"]
    print(f"   Receipt: \"{receipt['message']}\" (claim {receipt['reference']})")

    again = httpx.post(f"{args.url}/mesh/envelopes", content=text,
                       headers={"Content-Type": "application/json"}, timeout=60).json()
    print(f"\n🚶 Phone C carries the same envelope later: {again['status']} (no second claim)")

    print(f"\n📱 Phone A gets the receipt back: signature valid = {verify_receipt(receipt, key['receipt_public_key'])}")
    print("   → shows \"Delivered ✓\"")

    staff = os.environ.get("STAFF_KEY")
    if staff:
        c = httpx.get(f"{config.MEMBER2_API_URL}/staff/claims/{receipt['reference']}",
                      headers={"X-Staff-Key": staff}, timeout=20)
        if c.status_code == 200:
            claim = c.json()
            print(f"\n👮 Official sees claim {claim['id']}: status {claim['status']}, "
                  f"{claim['fields'].get('name')} of {claim['fields'].get('village')}, "
                  f"{len(claim.get('photos') or [])} photo(s), relief ₹{(claim.get('relief') or {}).get('total')}")
        else:
            print(f"\n👮 Official view: HTTP {c.status_code}")


if __name__ == "__main__":
    main()
