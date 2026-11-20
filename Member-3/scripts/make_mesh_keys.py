"""Create the mesh keys once and save them in Member-3/.env (never printed, never committed).

    python scripts/make_mesh_keys.py

MESH_PRIVATE_KEY (RSA-4096) opens sealed claims; MESH_RECEIPT_KEY (Ed25519) signs delivery
receipts. Phones only ever get the public halves (GET /mesh/public-key). Run it again with
--replace only if a key leaked: envelopes sealed with the old key can no longer be opened.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.mesh import new_keys  # noqa: E402

ENV = ROOT / ".env"
NAMES = ("MESH_PRIVATE_KEY", "MESH_RECEIPT_KEY")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replace", action="store_true", help="replace existing mesh keys")
    args = ap.parse_args()
    lines = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
    have = [n for n in NAMES if any(l.startswith(n + "=") and l.split("=", 1)[1].strip() for l in lines)]
    if have and not args.replace:
        sys.exit(f"{', '.join(have)} already in .env: nothing changed (use --replace only if a key leaked).")
    lines = [l for l in lines if not l.startswith(tuple(n + "=" for n in NAMES))]
    private, receipt = new_keys()
    lines += ["", "# Mesh keys (scripts/make_mesh_keys.py). Secret: never share or commit.",
              f"MESH_PRIVATE_KEY={private}", f"MESH_RECEIPT_KEY={receipt}"]
    ENV.write_text("\n".join(lines).lstrip("\n") + "\n", encoding="utf-8")
    print("Mesh keys saved in Member-3/.env. Restart the service to turn the mesh on.")


if __name__ == "__main__":
    main()
