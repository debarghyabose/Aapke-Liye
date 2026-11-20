# 🛰️ Member 3: Verification + Offline + Channels

**Name:** Debanik Dey · **GitHub:** [DEBANIK07](https://github.com/DEBANIK07)

## Your job
Make claims trustworthy for officials, make sure no claim is lost when the network drops, and reach people without smartphones.

## Phase 1: Core demo (build first)
- [x] **Damage vision:** AI checks the damage photos (Gemini free tier, or Claude)
- [x] **Basic verification:** check that the GPS location and timestamp look right
- [x] **Basic duplicate check:** flag the same photo or claim sent twice (also catches re-saved copies)
- [ ] **Offline sync:** queue uploads so nothing is lost when the network drops
  (`offline-client/queue.js` is built; still to point it at Member 2's API with Member 4)

## Run it

```powershell
cd Member-3
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env      # then put your GEMINI_API_KEY in .env (never in .env.example)
uvicorn app.main:app --port 8002 --reload
```

- Member 2's backend finds this service through `MEMBER3_VERIFY_URL=http://localhost:8002`.
- API docs: http://localhost:8002/docs
- Tests (never use real API quota): `python -m pytest -q`
- Try the AI on your own photo: `python scripts/try_photo.py path\to\photo.jpg`

## API

**`POST /verify`**, called by Member 2 for every claim photo.
Multipart `photo` (required), plus `lat`, `lon`, `taken_at` (ISO 8601) and `claim_id`.

```json
{"damage_detected": true, "damage_score": 0.8, "gps_ok": true, "timestamp_ok": true,
 "duplicate": false, "notes": ["Roof collapsed.", "Suggested SDRF category: kutcha house fully damaged"]}
```

- `notes` explain every problem found, for example GPS far from the phone's location, a photo taken
  before the disaster, a copy of another claim's photo, or an image that is not a genuine photo.
- If the damage AI is only temporarily unavailable (free-tier limit or busy), `/verify` returns
  **503**. Member 2 then keeps the photo as `pending` and can re-check it later.
- Gemini models are tried in order (`GEMINI_MODELS`). A busy model falls through to the next one,
  and the whole check finishes within 25 seconds (Member 2 waits 30).

## Phase 2: Roadmap features (after the demo works)
| Feature | What to do |
|---|---|
| Satellite verification | Check the claim location against Sentinel-1 / ISRO Bhuvan flood and damage maps, using PostGIS |
| Advanced fraud detection | Flag the same photo, house or person claiming twice |
| WhatsApp bot | File a claim by sending a voice note on WhatsApp |
| IVR / missed-call line | Feature-phone users call in and speak their claim |
| Voice/SMS status updates | Send each status change to the user in their own language |
| Dashboard data | Provide the map and damage data for the government dashboard that Member 5 designs |

## You work with
- **Member 2:** stores your verification results
- **Member 5:** uses your data for the dashboard
