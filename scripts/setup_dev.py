"""Create the local .env files that connect all five members' code (development only).

    python scripts/setup_dev.py            # create missing .env files, keep existing ones
    python scripts/setup_dev.py --force    # rewrite them

Ports:  Member 2 backend :8000 · Member 1 AI :8001 · Member 3 verification :8002 · app :5173
Secrets (encryption key, staff key, dashboard key) are generated here and stay in the
git-ignored .env files. Set GEMINI_API_KEY in your environment first to use the real AI;
without it Member 1 and Member 3 run in their keyless modes.
"""
from __future__ import annotations

import base64
import os
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORCE = "--force" in sys.argv
GEMINI = os.environ.get("GEMINI_API_KEY", "").strip()


def env_lines(example: Path, overrides: dict[str, str]) -> str:
    """Copy the member's .env.example, replacing the keys we set."""
    out, seen = [], set()
    for line in example.read_text(encoding="utf-8").splitlines():
        key = line.split("=", 1)[0].strip()
        if "=" in line and not line.lstrip().startswith("#") and key in overrides:
            out.append(f"{key}={overrides[key]}")
            seen.add(key)
        else:
            out.append(line)
    out += [f"{k}={v}" for k, v in overrides.items() if k not in seen]
    return "\n".join(out) + "\n"


def write(target: Path, text: str) -> bool:
    if target.exists() and not FORCE:
        print(f"  kept     {target.relative_to(ROOT)}")
        return False
    target.write_text(text, encoding="utf-8")
    print(f"  wrote    {target.relative_to(ROOT)}")
    return True


def read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    pairs = (l.split("=", 1) for l in path.read_text(encoding="utf-8").splitlines()
             if "=" in l and not l.lstrip().startswith("#"))
    return {k.strip(): v.strip() for k, v in pairs}


def main() -> None:
    print("Aapke Liye: local setup")
    staff_key = secrets.token_urlsafe(24)
    # One dashboard key shared by Member 3 (checks it) and Member 2 (sends it for /official).
    dashboard_key = (read_env(ROOT / "Member-3/.env").get("DASHBOARD_API_KEY")
                     or secrets.token_urlsafe(24))

    write(ROOT / "Member-1/.env", env_lines(ROOT / "Member-1/.env.example", {
        "CLAIM_AI_MODE": "live" if GEMINI else "mock",
        "GEMINI_API_KEY": GEMINI,
    }))

    write(ROOT / "Member-2/backend/.env", env_lines(ROOT / "Member-2/backend/.env.example", {
        "APP_ENV": "development",
        "MOCK_SERVICES": "false",
        "MOCK_MEMBER1": "false",
        "MOCK_MEMBER3": "false",
        "STORAGE_ENCRYPTION_KEY": base64.urlsafe_b64encode(os.urandom(32)).decode(),
        "STAFF_API_KEYS": f"officer-dev:{staff_key}",
        "MEMBER1_AI_URL": "http://localhost:8001",
        "MEMBER3_VERIFY_URL": "http://localhost:8002",
        "SERVICE_TIMEOUT_SECONDS": "120",   # first Whisper run can be slow
        "CORS_ORIGINS": "http://localhost:5173,http://127.0.0.1:5173",
        "MEMBER3_DASHBOARD_KEY": dashboard_key,
    }))

    write(ROOT / "Member-3/.env", env_lines(ROOT / "Member-3/.env.example", {
        "GEMINI_API_KEY": GEMINI,
        "DASHBOARD_API_KEY": dashboard_key,
        "PHONE_HASH_KEY": secrets.token_hex(32),
        "DASHBOARD_CORS_ORIGINS": "null,http://localhost:5173,http://localhost:5500,http://127.0.0.1:5500",
        "MEMBER2_API_URL": "http://localhost:8000",
    }))

    app_env = ROOT / "Member-4/frontend/.env"
    write(app_env, "VITE_API_URL=http://localhost:8000\nVITE_MESH_URL=http://localhost:8002\n")
    if "VITE_MESH_URL" not in app_env.read_text(encoding="utf-8"):   # .env made before the mesh
        with app_env.open("a", encoding="utf-8") as f:
            f.write("VITE_MESH_URL=http://localhost:8002\n")
        print("  added    VITE_MESH_URL to Member-4/frontend/.env")

    # Member 3's mesh keys (open sealed claims, sign receipts): made once, kept in Member-3/.env
    if not read_env(ROOT / "Member-3/.env").get("MESH_PRIVATE_KEY"):
        import subprocess
        py = ROOT / "Member-3/.venv/Scripts/python.exe"
        r = subprocess.run([str(py if py.exists() else sys.executable),
                            str(ROOT / "Member-3/scripts/make_mesh_keys.py")],
                           cwd=ROOT / "Member-3", capture_output=True, text=True)
        print("  mesh     " + (r.stdout.strip() or r.stderr.strip()[-200:]))

    m2 = read_env(ROOT / "Member-2/backend/.env")
    m3 = read_env(ROOT / "Member-3/.env")
    print()
    print("Staff key for the Officials screen (/official):")
    print("  " + m2.get("STAFF_API_KEYS", "").split(":", 1)[-1])
    print("Dashboard key for Member-5/dashboard/index.html:")
    print("  " + m3.get("DASHBOARD_API_KEY", ""))
    print("AI mode:", "live (Gemini)" if read_env(ROOT / "Member-1/.env").get("CLAIM_AI_MODE") == "live"
          else "mock (keyword rules; type answers, voice needs live mode)")


if __name__ == "__main__":
    main()
