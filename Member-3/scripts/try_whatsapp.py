"""Chat with the WhatsApp bot on this computer: no phone, no Twilio, nothing is sent.

The real bot (app/whatsapp.py) runs against the real Member 2 backend (which calls Member 3's
/verify for photos); its replies are printed here instead of being sent to WhatsApp.

Before running: Member 2 on port 8000 and Member 3 on port 8002. Then, from Member-3/:
    python scripts/try_whatsapp.py            # scripted demo conversation
    python scripts/try_whatsapp.py --chat     # type messages yourself

In --chat, type text, or:
    /voice path/to/audio.ogg     send a voice note (any .ogg/.mp3/.wav/.m4a)
    /photo path/to/photo.jpg     send a photo
    /location 19.81 85.83        share a location
    /edit date_of_incident 2026-11-15   fix a field like the app's Review screen does
    /officer Verified "note"     act as an official: change the claim's status (needs STAFF_KEY)
    /quit
"""
import argparse
import asyncio
import io
import mimetypes
import os
import shlex
import sys
import wave
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import config  # noqa: E402
from app.store import Store  # noqa: E402
from app.whatsapp import Bot, Incoming, Member2  # noqa: E402

PHONE = "whatsapp:+919000012345"          # demo number, not a real person's
PHOTO = ROOT / "data" / "demo" / "photos" / "flood_home_tipomia_assam.jpg"


class PrintTwilio:
    """Stands in for Twilio: prints the bot's replies and 'downloads' local files."""

    async def send(self, to, body):
        print("\n🤖 BOT:\n  " + body.replace("\n", "\n  "))

    async def download(self, url):
        return Path(url).read_bytes()


def silent_wav(seconds: float = 2.0) -> Path:
    """A short silent voice note for the scripted demo."""
    path = Path(os.environ.get("TEMP", ".")) / "aapke_liye_demo_voice.wav"
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(b"\x00\x00" * int(16000 * seconds))
    path.write_bytes(buf.getvalue())
    return path


def media(path: str) -> list:
    ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return [(path, {"audio/x-wav": "audio/wav"}.get(ctype, ctype))]


async def officer(bot: Bot, status: str, note: str) -> None:
    key = os.environ.get("STAFF_KEY", "")
    if not key:
        print("  (set STAFF_KEY to one of Member 2's STAFF_API_KEYS values to act as an official)")
        return
    s = bot.store.wa_get(PHONE)
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.put(f"{config.MEMBER2_API_URL}/status/{s['claim_id']}", headers={"X-Staff-Key": key},
                        json={"status": status, "note": note or None})
    print(f"\n👮 OFFICIAL set claim {s['claim_id']} to {status}: HTTP {r.status_code}")
    sent = await bot.check_statuses()          # what the 60-second status check does
    if not sent:
        print("  (no status message: the status did not change)")


async def send(bot: Bot, line: str) -> bool:
    if not line.strip():
        return True
    if line.startswith("/"):
        cmd, _, rest = line.partition(" ")
        if cmd == "/quit":
            return False
        if cmd in ("/voice", "/photo") and rest.strip():
            path = rest.strip().strip('"')          # keep Windows backslashes as they are
            print(f"\n🙋 YOU: [{cmd[1:]} {Path(path).name}]")
            return await bot.handle(Incoming(PHONE, media=media(path))) or True
        args = shlex.split(rest)
        if cmd == "/voice":
            print("  usage: /voice FILE")
        elif cmd == "/location" and len(args) == 2:
            print(f"\n🙋 YOU: [location {args[0]}, {args[1]}]")
            await bot.handle(Incoming(PHONE, lat=float(args[0]), lon=float(args[1])))
        elif cmd == "/edit" and len(args) == 2:
            s = bot.store.wa_get(PHONE)
            async with httpx.AsyncClient(timeout=20) as c:
                r = await c.patch(f"{config.MEMBER2_API_URL}/claims/{s['claim_id']}",
                                  headers={"X-Claim-Token": bot._token(s)}, json={"fields": {args[0]: args[1]}})
            print(f"\n✏️  REVIEW SCREEN: set {args[0]} = {args[1]}: HTTP {r.status_code}")
        elif cmd == "/officer" and args:
            await officer(bot, args[0], " ".join(args[1:]))
        else:
            print("  commands: /voice FILE, /photo FILE, /location LAT LON, /edit FIELD VALUE, /officer STATUS [note], /quit")
        return True
    print(f"\n🙋 YOU: {line}")
    await bot.handle(Incoming(PHONE, text=line))
    return True


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat", action="store_true", help="type the messages yourself")
    ap.add_argument("--db", default=str(Path(os.environ.get("TEMP", ".")) / "aapke_liye_try_whatsapp.db"),
                    help="where the chat's session is kept (not the service's member3.db)")
    args = ap.parse_args()
    try:
        httpx.get(f"{config.MEMBER2_API_URL}/health", timeout=5).raise_for_status()
    except Exception:
        sys.exit(f"Member 2 is not running at {config.MEMBER2_API_URL} (start it on port 8000 first).")

    bot = Bot(Store(args.db), Member2(config.MEMBER2_API_URL), PrintTwilio())
    if args.chat:
        print("Chat with the bot. Start with 'hi'. /quit to stop.")
        while await send(bot, input("\n> ")):
            pass
        return
    for line in ["NEW", "hi", "1", "YES", f"/voice {silent_wav()}", "/location 19.81 85.83",
                 f"/photo {PHOTO}", "SUBMIT",
                 # The dev stand-in for Member 1 never gives a date; fill it like the Review screen.
                 "/edit date_of_incident 2026-11-15", "SUBMIT", "STATUS", '/officer Verified "Field visit done"']:
        await send(bot, line)


if __name__ == "__main__":
    asyncio.run(main())
