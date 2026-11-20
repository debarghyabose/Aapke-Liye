"""Make pretend phone calls to the IVR line on this computer: no phone, no Twilio.

The real call logic (app/ivr.py) runs against the real Member 2 backend; what the caller
would hear is printed, and key presses come from the script (or from you with --call).

Before running: Member 2 on port 8000. Then, from Member-3/:
    python scripts/try_ivr.py           # scripted demo: three calls from the same phone
    python scripts/try_ivr.py --call    # one call where you press the keys
"""
import argparse
import asyncio
import io
import os
import sys
import wave
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import config  # noqa: E402
from app.ivr import Ivr  # noqa: E402
from app.store import Store  # noqa: E402
from app.whatsapp import Member2  # noqa: E402

CALLER = "+919000012345"          # demo number, not a real person's


def silent_wav(seconds: float = 3.0) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
        w.writeframes(b"\x00\x00" * int(8000 * seconds))
    return buf.getvalue()


async def call(line: Ivr, sid: str, keys: list[str] | None, voice: bytes) -> None:
    """One call. keys=None: ask the person at the keyboard for each key press."""
    print(f"\n📞 ===== Call {sid} from {CALLER} =====")
    keys = list(keys) if keys is not None else None
    xml = await line.incoming(sid, CALLER)
    while True:
        root = ET.fromstring(xml)
        gather, rec = root.find("Gather"), root.find("Record")
        # Play what comes before the key press or recording; what follows is only heard if the
        # caller does nothing, so it is skipped here.
        for el in root:
            for say in el.iter("Say"):
                print(f"  🔊 [{say.get('language')}] {say.text}")
            if el.tag in ("Gather", "Record"):
                break
        if rec is not None:
            print("  🎙️  (beep) caller speaks, then presses #")
            action = rec.get("action")
            lang = parse_qs(urlparse(action).query).get("lang", ["en"])[0]
            xml, process = line.recorded(sid, lang, f"local://{sid}", 25)
            for say in ET.fromstring(xml).iter("Say"):
                print(f"  🔊 [{say.get('language')}] {say.text}")
            print("  📴 call ends")
            if process:
                print("  ⏳ after the call: recording sent to Member 2 (speech AI)...")
                await line.process_recording(sid, f"local://{sid}")
            return
        if gather is None:
            print("  📴 call ends")
            return
        if keys is None:
            digit = input("  ⌨️  press a key (Enter = no key): ").strip()[:1]
        else:
            digit = keys.pop(0) if keys else ""
            print(f"  ⌨️  caller presses {digit or '(nothing)'}")
        if not digit:
            print("  📴 caller hangs up")
            return
        action = gather.get("action")
        path, q = urlparse(action).path, parse_qs(urlparse(action).query)
        lang = q.get("lang", ["en"])[0]
        if path == "/ivr/language":
            xml = line.language(sid, CALLER, digit)
        elif path == "/ivr/consent":
            xml = await line.consent(sid, CALLER, lang, digit)
        elif path == "/ivr/menu":
            xml = line.menu(sid, CALLER, digit)
        else:
            xml = await line.incoming(sid, CALLER)


async def as_app_and_official(line: Ivr) -> None:
    """Between calls: a volunteer fills the missing date in the app, submits; an official approves."""
    row = line.store.ivr_latest_claim(CALLER)
    claim_id, token = row["claim_id"], line._token(row)
    base, h = config.MEMBER2_API_URL, {"X-Claim-Token": token}
    async with httpx.AsyncClient(timeout=60) as c:
        r1 = await c.patch(f"{base}/claims/{claim_id}", headers=h, json={"fields": {"date_of_incident": "2026-11-15"}})
        r2 = await c.post(f"{base}/claims/{claim_id}/submit", headers=h)
        print(f"\n✏️  Volunteer in the app: adds the date (HTTP {r1.status_code}), submits (HTTP {r2.status_code})")
        key = os.environ.get("STAFF_KEY", "")
        if key:
            for status in ("Verified", "Approved"):
                r = await c.put(f"{base}/status/{claim_id}", headers={"X-Staff-Key": key}, json={"status": status})
                print(f"👮 Official sets {status} (HTTP {r.status_code})")
        else:
            print("  (set STAFF_KEY to also act as the official)")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--call", action="store_true", help="one call where you press the keys")
    ap.add_argument("--db", default=str(Path(os.environ.get("TEMP", ".")) / "aapke_liye_try_ivr.db"))
    ap.add_argument("--fresh", action="store_true", help="forget earlier pretend calls")
    args = ap.parse_args()
    try:
        httpx.get(f"{config.MEMBER2_API_URL}/health", timeout=5).raise_for_status()
    except Exception:
        sys.exit(f"Member 2 is not running at {config.MEMBER2_API_URL} (start it on port 8000 first).")
    if args.fresh or not args.call:
        Path(args.db).unlink(missing_ok=True)
    voice = silent_wav()

    async def local_download(url: str) -> bytes:
        return voice

    line = Ivr(Store(args.db), Member2(config.MEMBER2_API_URL), local_download)
    if args.call:
        await call(line, f"CALL-{os.getpid()}", None, voice)
        return
    await call(line, "CALL-1", ["1", "1"], voice)          # English, agree, record
    await call(line, "CALL-2", ["1"], voice)               # returning: record more details
    await as_app_and_official(line)
    await call(line, "CALL-3", [""], voice)                # hears the new status, hangs up


if __name__ == "__main__":
    asyncio.run(main())
