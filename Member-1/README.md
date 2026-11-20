# 🤖 Member 1: AI/ML (Speech + Claim AI)

Part of **Aapke Liye**. Turns a disaster victim's voice note, in English, Hindi, Bengali,
Marathi, Telugu or Tamil, into a structured relief claim, asks for what is missing, and
drafts follow-up documents.

## 🚀 Current sprint (2 hours) — your tasks

### Gemini speech + before/after (Google AI 20%)
- [x] **Gemini hears the voice note.** In `asr.py`, add `ASR_PROVIDER=gemini|whisper` (default `gemini`). Send the 16 kHz WAV to Gemini as audio and ask for the transcript plus language. Keep Whisper as the fallback when Gemini fails or there's no key. *Even better:* one Gemini call from audio straight to claim fields (skips a step, faster).
- [x] Return `asr_provider: "gemini"` in the turn response, so it shows on stage and in `/health`.
- [x] **Before/after:** make `/v1/damage/compare` real with Gemini (it already exists, tested in mock mode only). Member 2 will call it when a claim photo has a baseline photo from the vault.
- [x] Tests: provider switch, fallback to Whisper, compare in mock and live.
- **Done when:** a Hindi voice note is transcribed by Gemini (Whisper turned off) and the claim fills in.

**✅ Done (branch `member-1/gemini-speech`):**
- `ASR_PROVIDER=gemini` (default) sends the 16 kHz WAV to Gemini; `ASR_FALLBACK=whisper` falls back to local Whisper if Gemini fails (`none` turns it off). Silence is not sent to Whisper. Whisper is only loaded at startup when it is the main provider.
- `/health` shows `"asr": "gemini:<model> (fallback whisper:...)"`; every voice turn returns `asr_provider` (`gemini` / `whisper`), also saved in `claim.transcripts[].asr_provider`.
- Tested live: a Hindi note (Devanagari, 7 s) and a Bengali note (Bengali script) filled name, village, district, state, date, house and livestock; Gemini read a spoken 10-digit phone number correctly.
- `/v1/damage/compare` already used Gemini in live mode; tested live: a different house is reported as `same_property: false` → `needs_human_review: true` (fraud signal); the same photo twice gives score 0. **For Member 2:** call it with `{"baseline_image_base64", "damage_image_base64", "baseline_media_type", "damage_media_type", "context"}`.
- Tests: `tests/test_asr_providers.py` (7 tests).

**Rules:** work on your own branch `member-1/<feature>`, edit only your own folder (ask the owner otherwise), never commit `.env`, run your tests before pushing, then open a pull request into `main`. The team lead merges all four and builds the final web app (with mobile UI).
Full plan, timeline, demo script and what to cut if time runs out: [docs/next-features-plan.md](../docs/next-features-plan.md)

---

## Status

### Phase 1: Core demo
- [x] **Speech to text** in 6 languages with Whisper (runs locally, no key)
- [x] **Claim AI:** Gemini turns speech into claim fields: name, phone, location, disaster, date, losses, amounts
- [x] **Missing fields:** rule-based check plus a follow-up question in the user's language
- [ ] Test with sample recordings in every language. *The 18 scripts and the `eval.py` scorer are ready; real recordings are still needed.*

### Phase 2: Roadmap
| Feature | Status |
|---|---|
| Before/after damage comparison | Built (`/v1/damage/compare`), tested in mock mode only |
| Replacement applications (Aadhaar, ration card, land records) | Built |
| Insurance claims (home, vehicle, crop) | Built |
| Auto-escalation letters (follow-up, grievance, RTI) | Built; **templates in `app/templates/` are placeholders until Member 5's arrive** |

### Works with
- **Member 2:** call `POST /v1/claim/turn` with audio/text + the current claim; store the claim that comes back
- **Member 4:** show `next_question.text` (and play `audio_base64` if present); see `app/static/demo.html`
- **Member 5:** replace the files in `app/templates/`, keeping the `{{placeholders}}`

The full plan, flowchart and architecture are in [docs-playbook.html](docs-playbook.html).

```
audio ─► ffmpeg 16 kHz WAV ─► Whisper (local: language ID + speech to text)
      ─► amount normalizer ─► Gemini extraction (JSON schema) ─► merge into claim
      ─► missing-field rules ─► follow-up question / read-back ─► Member 2 stores, Member 4 shows
```

## Run it

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # CLAIM_AI_MODE=mock works with no keys
uvicorn app.main:app --reload --port 8001
```

Open http://localhost:8001/docs for the interactive API.

| Mode | What it uses | Use it for |
|---|---|---|
| `CLAIM_AI_MODE=mock` | keyword rules, fixed questions, no network | integrating with Members 2 and 4, unit tests |
| `CLAIM_AI_MODE=live` | Whisper (on your PC), Gemini | the real demo |

Live mode needs only `GEMINI_API_KEY` (free from https://aistudio.google.com/apikey) and ffmpeg on PATH
(`winget install ffmpeg`). Whisper needs no key: the model (~1.6 GB for `large-v3-turbo`)
downloads once on first start. Spoken questions (`TTS_ENABLED=1`) use gTTS, also keyless.

## Endpoints

| Method | Path | Called by | Purpose |
|---|---|---|---|
| GET | `/health` | anyone | mode, languages, model |
| GET | `/v1/schema/claim` | Members 2, 4 | JSON schema of the claim |
| POST | `/v1/transcribe` | Member 2 | audio → text (debugging) |
| POST | `/v1/claim/turn` | Member 2 | **main loop**: audio or text + current claim → updated claim + next question |
| POST | `/v1/damage/compare` | Member 2 | baseline + damage photo → score 0–100 |
| GET | `/v1/documents/types` | Member 2 | list of draftable documents |
| POST | `/v1/documents/draft` | Member 2 | claim → reissue request / insurance claim / letter / RTI |
| POST | `/v1/escalation/next` | Member 2 | days pending → which letter to send next |

### The conversation loop

The service is stateless. Member 2 sends the claim back on every turn and stores what comes back.

```jsonc
// turn 1
POST /v1/claim/turn
{"session_id": "s_8f21", "language": "hi", "audio_base64": "<wav/ogg/mp3>"}

// response
{"claim": {...}, "transcript": "मेरा नाम रमेश...", "status": "incomplete",
 "missing_fields": ["location.village", "claimant.phone"],
 "next_question": {"field": "location.village", "text": "आप किस गाँव या शहर में रहते हैं?",
                   "text_en": "Which village or town do you live in?", "audio_base64": null}}

// turn 2..n: send the claim you got back
{"session_id": "s_8f21", "claim": {...}, "audio_base64": "..."}
```

`status` goes `incomplete` → `needs_confirmation` (the question is a read-back summary) →
`complete`. On the read-back screen Member 4 can send `"confirmed": true` (Confirm button) or
`"confirmed": false` (Edit button), or the user can just say "yes" / correct something.
`next_question.field == "repeat"` means the audio was unclear: play the question and record again.
Typed input works too: send `"text"` instead of audio.

## Tests and evaluation

```powershell
pytest                     # 42 offline tests (mock mode)
python eval.py --mock      # golden set, rule-based extractor
python eval.py             # golden set through Gemini (costs a little)
python eval.py --audio     # uses tests/samples/<lang>/<id>.wav when recorded
```

`tests/golden/cases.json` has 18 scripts (3 per language: house, crop, livestock/vehicle/shop).
They double as recording scripts; see `tests/samples/README.md`. Target: 80% field accuracy per
language. Mock mode scores low on non-Latin names and districts by design, because it cannot
transliterate. That is Gemini's job in live mode.

## Layout

```
app/
  main.py        FastAPI routes
  schemas.py     shared contracts (bump SCHEMA_VERSION on breaking changes)
  config.py      env settings
  audio.py       decode / download / ffmpeg to 16 kHz mono WAV
  asr.py         Whisper speech to text + language detection (local, no key)
  tts.py         gTTS: speak questions aloud (no key)
  normalize.py   spoken amounts → numbers in all 6 languages
  extract.py     Gemini extraction (live) / keyword rules (mock) + merge
  gaps.py        required-field rules (never the LLM)
  questions.py   follow-up questions and read-back, 6 languages
  pipeline.py    one conversation turn
  damage.py      Phase 2: before/after photo scoring
  documents.py   Phase 2: drafting + escalation ladder
  templates/     PLACEHOLDER letter templates → replace with Member 5's
tests/           pytest suite, golden cases, sample recordings
eval.py          accuracy report per language
```

## Before the demo

- [ ] Native speakers review every string in `app/questions.py` and `app/languages.py`.
- [ ] Member 5 replaces every file in `app/templates/` (each starts with a PLACEHOLDER line).
- [ ] Start once in live mode with internet so the Whisper model downloads before demo day.
- [ ] If Whisper is slow on your laptop, set `WHISPER_MODEL=small` (faster, less accurate).
- [ ] Record the 18 golden scripts and run `python eval.py --audio`.
- [ ] Watch `timings_ms` in responses; target under 6 s per turn. Try `QUESTION_MODE=template`
      to save one Gemini call per turn.
