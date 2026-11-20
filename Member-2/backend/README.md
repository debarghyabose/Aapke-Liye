# ⚙️ Member 2 — Core Backend (FastAPI)

Claims, audio/photo uploads, SDRF relief calculation, proof substitution and the relief form PDF.
Calls Member 1 (AI) and Member 3 (photo verification); serves Member 4 (frontend).

## Setup (local development)

```bash
cd Member-2/backend
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # Windows: copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

- Open http://localhost:8000/docs to try every endpoint.
- Tests: `python -m pytest -q`. Members 1 and 3 are mocked at the HTTP level with respx.
- No Member 1/3 running yet? Set `MOCK_SERVICES=true` in `.env`. `app/dev_mocks.py` then gives
  clearly fake `[DEV MOCK]` answers. Production refuses to start with this on.
- Development uses SQLite (`aapke_liye.db`) and creates tables on startup. Encrypted files go
  to `storage/`.

## Production

```bash
cp .env.example .env     # set APP_ENV=production and real secrets (see below)
docker compose up -d --build
curl http://localhost:8000/health
```

The image runs `alembic upgrade head`, then `uvicorn --workers $WEB_CONCURRENCY` as a non-root user.
Data lives in two volumes: `pgdata` (Postgres/PostGIS) and `storage` (encrypted uploads and PDFs).
Back up both, plus `STORAGE_ENCRYPTION_KEY`, because files cannot be decrypted without it.

With `APP_ENV=production` the app **refuses to start** if any of these hold:
- `MOCK_SERVICES=true`.
- `MEMBER1_AI_URL`, `DATABASE_URL`, `STORAGE_ENCRYPTION_KEY` or `STAFF_API_KEYS` is missing.
- The encryption key is invalid.
- A staff key is shorter than 24 characters.
- `CORS_ORIGINS` is empty or `*`.

Behind a reverse proxy:
- Cap upload bodies at the proxy (nginx `client_max_body_size 16m`).
- Set `FORWARDED_ALLOW_IPS` to the proxy's IP so per-IP rate limits see real client IPs.

Rate limits are kept in memory per worker. For several workers or servers, put the limit at the
proxy, or point slowapi at Redis.

Schema changes: edit `app/models.py`, then `alembic revision --autogenerate -m "..."`, review
the file, and commit it.

### Environment variables

| Variable | Default | Notes |
|---|---|---|
| `APP_ENV` | `development` | `development` or `production` |
| `MOCK_SERVICES` | `false` | `true` = fake Member 1/3 answers. Refused in production |
| `DATABASE_URL` | SQLite file | `postgresql://user:pass@host:5432/db`. Required in production |
| `STORAGE_DIR` | `./storage` | Encrypted audio, photos and PDFs (`/data/storage` in Docker) |
| `STORAGE_ENCRYPTION_KEY` | dev key file | Fernet key(s), comma-separated. The first encrypts, all decrypt (rotation). Required in production |
| `STAFF_API_KEYS` | — | `label:key,label2:key2`. The label is logged, never the key. Required in production |
| `MEMBER1_AI_URL` | — | e.g. `http://member1:8001`. Required in production |
| `MEMBER3_VERIFY_URL` | — | e.g. `http://member3:8002`. If unset, photos stay `pending` |
| `SERVICE_TIMEOUT_SECONDS` | `30` | Read timeout for Member 1/3 calls (connect timeout 5s, 2 retries) |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Comma-separated. `*` refused in production |
| `RATE_LIMIT_CREATE` | `10/minute` | Per IP, `POST /claims` |
| `RATE_LIMIT_UPLOAD` | `30/minute` | Per IP, audio/photo uploads, retry, reverify |
| `LOG_LEVEL` | `INFO` | JSON logs on stdout |
| `POSTGRES_PASSWORD`, `FORWARDED_ALLOW_IPS`, `WEB_CONCURRENCY` | — | docker-compose only |

Generate secrets:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"   # STORAGE_ENCRYPTION_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"                                 # a staff key
```

## API (for Member 4)

Every claim call except `POST /claims` needs the header **`X-Claim-Token`**, using the
`claim_token` returned once by `POST /claims`. Store it on the device with the claim ID. **It cannot
be recovered.** A wrong or missing token returns `404 {"detail":"Claim not found"}`, the same as
a claim that doesn't exist. Staff actions need **`X-Staff-Key`**. Every response carries
`X-Request-ID`. Send your own (letters, digits, `.`, `_` and `-`; up to 64) to trace a request
across services.

| Method | Path | Headers | Body | Result |
|---|---|---|---|---|
| POST | `/claims` | — | JSON `{"language","disaster_type"?,"consent":true,"consent_text_version"}` | 201 claim + `claim_token` |
| GET | `/claims/{id}` | X-Claim-Token | — | Full claim |
| POST | `/claims/{id}/audio` | X-Claim-Token | multipart `audio` | Fields filled by Member 1. **503** if Member 1 is down (audio kept) |
| POST | `/claims/{id}/text` | X-Claim-Token | JSON `{"text"}` | Typed / tapped answer through Member 1's claim AI. 503 if Member 1 is down |
| POST | `/claims/{id}/audio/retry` | X-Claim-Token | — | Re-sends pending recordings. 409 if none are pending |
| POST | `/claims/{id}/photos` | X-Claim-Token | multipart `photo`, `lat`?, `lon`?, `taken_at`? | Photo added. Same photo again = no-op |
| POST | `/claims/{id}/photos/{photo_id}/reverify` | X-Claim-Token | — | Re-checks a `pending` photo. 503 if Member 3 is still down |
| PATCH | `/claims/{id}` | X-Claim-Token | JSON `{"fields":{...}}` | Review-screen edits. Relief recalculated |
| POST | `/claims/{id}/submit` | X-Claim-Token | — | Validates, builds PDF, status → Submitted |
| GET | `/claims/{id}/pdf` | X-Claim-Token | — | Relief form PDF |
| GET | `/status/{id}` | X-Claim-Token | — | Status + timeline |
| PUT | `/status/{id}` | X-Staff-Key | JSON `{"status","note"?}` | Officials move the claim along |
| GET | `/staff/claims?status=` | X-Staff-Key | — | Officials' queue: submitted claims, newest first |
| GET | `/staff/claims/{id}` | X-Staff-Key | — | Officials' view (adds `duplicate_of_claim_id` on photos) |
| GET | `/health`, `/rules/sdrf` | — | — | Health and current relief rules |

Languages: `en hi bn te mr ta`. Timestamps are UTC ISO 8601 with `Z`
(e.g. `2026-11-20T04:30:00.000Z`). Show them in IST on screen.

**Errors.** `detail` is always a user-safe sentence, except the submit 422 (below).

| Code | When |
|---|---|
| 404 | Unknown claim or wrong token |
| 401 | Missing or wrong staff key |
| 409 | Claim already submitted (edits, uploads, re-submit), max 10 photos, or status change not allowed |
| 413 | Audio over 15 MB, photo over 10 MB, request over 16 MB |
| 415 | Not webm/ogg/mp3/wav/m4a audio, or not jpeg/png/webp photo (content type and file bytes are both checked) |
| 422 | Bad input, or consent missing |
| 429 | Rate limit |
| 503 | Member 1 down. Show `detail` and offer **Try again** → `POST /audio/retry` (also sends `Retry-After`) |

**Status flow:** `Draft → Submitted → Verified → Approved → Paid`. `Rejected` is allowed from
Submitted or Verified. Only `/submit` moves Draft → Submitted.

### Document vault + DigiLocker (demo), for the `/prepare` page

A family saves papers and "before" photos **before** a disaster. All files are encrypted.

| Call | Headers | Body | Returns |
|---|---|---|---|
| `POST /households` | none | none | `{household_id, household_token}`. The token is shown **once**; keep it on the phone |
| `POST /households/{id}/documents` | `X-Household-Token` | form: `doc_type`, `file` (JPEG/PNG/WebP/PDF, ≤10 MB) | the document |
| `GET /households/{id}/documents` | `X-Household-Token` | none | `[{id, doc_type, content_type, source, created_at, file_url}]` |
| `GET /households/{id}/documents/{doc_id}/file` | `X-Household-Token` | none | the file (decrypted) |
| `DELETE /households/{id}/documents/{doc_id}` | `X-Household-Token` | none | 204; the file is deleted too |
| `POST /claims/{id}/household` | `X-Claim-Token` **and** `X-Household-Token` | `{"household_id": "HH-…"}` | the claim, with `household_id` and `documents_in_vault` |

- `doc_type`: `aadhaar`, `ration_card`, `land_record`, `bank_passbook`, `house_ownership`, `voter_id`, `death_certificate` (the keys of `rules/proof_substitution.json`), or `baseline_photo` (image only: house, fields or livestock in normal times).
- `source` is `upload` or `digilocker_mock`. **Always show `digilocker_mock` as "DigiLocker (demo)"**, never as a real DigiLocker document.
- After linking, vault documents are no longer "lost": they leave `proof_suggestions` and the PDF lists them as "Available in vault".
- **Before/after:** if the household has a `baseline_photo`, every claim photo gets `verification.before_after` from Member 1's `/v1/damage/compare`: `{status: "complete", same_property, damage_score (0-100), level, damaged_items, reason, confidence, needs_human_review, baseline_document_id}`, or `{status: "unavailable"}` if Member 1 is down. Photos uploaded before linking are compared when the household is linked.
- **Hilly area:** `PATCH /claims/{id}` with `{"fields": {"is_hilly": true}}` → a fully damaged house uses the hilly rate (₹1,30,000 instead of ₹1,20,000).

**DigiLocker (demo) flow** (`DIGILOCKER_MODE=mock`):
1. `GET /households/{id}/digilocker/start?return_to=<your page URL>` with `X-Household-Token` → `{mode, demo: true, banner, consent_url}`.
2. Open `BACKEND_URL + consent_url` in the browser (`window.location`). It is a consent page with a red **"Demo: DigiLocker mock"** banner and Allow / Deny.
3. Allow → a sample Aadhaar and ration card (PDFs marked DEMO) are added with `source=digilocker_mock`, then the browser returns to `return_to?digilocker=added` (or `=denied`). `return_to` must start with one of `CORS_ORIGINS`; otherwise a "you can close this page" page is shown. Then call `GET /households/{id}/documents` again.

Real DigiLocker later: only `app/services/digilocker.py` changes (same four steps: authorization URL → exchange code → list issued → fetch file).

### Examples (from a real dev run)

```http
POST /claims
Content-Type: application/json

{"language":"bn","disaster_type":"flood","consent":true,"consent_text_version":"v1"}
```
```json
201
{"id":"AL-4JFT5OS2M55O","language":"bn","disaster_type":"flood","transcript":null,"fields":{},
 "missing_fields":[],"follow_up_questions":[],"relief":null,"proof_suggestions":[],"status":"Draft",
 "pdf_url":null,"photos":[],"recordings":[],
 "history":[{"status":"Draft","note":null,"at":"2026-11-20T07:21:10.375Z"}],
 "consent_text_version":"v1","consent_given_at":"2026-11-20T07:21:10.363Z","submitted_at":null,
 "created_at":"2026-11-20T07:21:10.372Z","updated_at":"2026-11-20T07:21:10.372Z",
 "claim_token":"lC9DI3ZoSpO_WkN-Jndn3APnWpcuAvndlLjD6kEbVGI"}
```

```bash
curl -X POST $API/claims/$ID/audio -H "X-Claim-Token: $TOKEN" -F "audio=@rec.webm;type=audio/webm"
```
The full claim comes back. The parts the review screen uses:
```json
{"transcript":"…","fields":{"name":"…","village":"…","losses":[{"category":"house","item":"fully_damaged_plain","quantity":1}],"documents_lost":["aadhaar"]},
 "missing_fields":["phone","date_of_incident"],
 "follow_up_questions":["What is your phone number?","On which date did the disaster reach your house?"],
 "relief":{"rules_version":"sample-2022-26","estimate_only":true,"total":198605,
           "lines":[{"category":"house","item":"fully_damaged_plain","quantity":1.0,"rate":120000,"unit":"per house","amount":120000,"note":null}],
           "unmatched":[{"category":"boat","item":"trawler","quantity":1,"reason":"Unknown category 'boat'"}]},
 "proof_suggestions":[{"document":"aadhaar","alternatives":["Voter ID, ration card or any other photo ID if available","…"]}],
 "recordings":[{"id":1,"status":"processed"}]}
```
If Member 1 is down: `503 {"detail":"We could not process your recording right now. It has been saved safely; please try again in a few minutes."}`.
The recording shows as `{"status":"pending"}` in `recordings`.

```bash
curl -X POST $API/claims/$ID/photos -H "X-Claim-Token: $TOKEN" \
  -F "photo=@photo.jpg;type=image/jpeg" -F lat=22.16 -F lon=88.80 -F taken_at=2026-11-20T10:00:00+05:30
```
```json
"photos":[{"id":1,"sha256":"c49f…","lat":22.16,"lon":88.8,"taken_at":"2026-11-20T04:30:00.000Z",
           "verification":{"damage_detected":true,"damage_score":0.8,"gps_ok":true,"timestamp_ok":true,"notes":[],"status":"complete"}}]
```
If Member 3 is down, `verification` is `{"status":"pending"}` and the claim carries on. `taken_at`
without an offset is read as IST.

```http
PATCH /claims/{id}
X-Claim-Token: …
Content-Type: application/json

{"fields":{"name":"রিনা দাস","phone":"+91 98000 00000","date_of_incident":"2026-11-15"}}
```
Allowed keys: `name phone village district state disaster_type date_of_incident (YYYY-MM-DD)
losses documents_lost bank_account_available`. Unknown keys return 422. `losses` replaces the whole
list. Each loss is `{"category","item","quantity"(default 1),"damage_percent"?}`, with the
categories and items from `GET /rules/sdrf`.

`POST /claims/{id}/submit` when details are missing:
```json
422
{"detail":{"message":"Some details are missing or need correcting",
           "missing_fields":["phone","date_of_incident"],
           "invalid_fields":{"phone":"Must be a 10-digit Indian mobile number"}}}
```
Required: `name, phone (10-digit Indian mobile), village, district, state, date_of_incident (not
in the future), losses (at least one)`. On success the phone is normalised to 10 digits,
`status` becomes `Submitted` and `pdf_url` is set. After that, edits and uploads return 409.

```http
PUT /status/{id}
X-Staff-Key: …
Content-Type: application/json

{"status":"Verified","note":"Field visit done"}
```
```json
{"claim_id":"AL-4JFT5OS2M55O","status":"Verified","updated_at":"2026-11-20T07:21:12.029Z",
 "timeline":[{"status":"Draft","note":null,"at":"2026-11-20T07:21:10.375Z"},
             {"status":"Submitted","note":null,"at":"2026-11-20T07:21:11.691Z"},
             {"status":"Verified","note":"Field visit done","at":"2026-11-20T07:21:12.029Z"}]}
```

## Contracts for Member 1 and Member 3

These are unchanged from v0.1 apart from the notes below. They also appear at the top of
`app/services/integrations.py`.

**Member 1** `POST {MEMBER1_AI_URL}/process`, multipart: `audio=<file>`, `language=<code>`
```json
{"transcript": "…",
 "fields": {"name": "…", "phone": "…", "village": "…", "district": "…", "state": "…",
            "disaster_type": "flood", "date_of_incident": "YYYY-MM-DD",
            "losses": [{"category": "house", "item": "fully_damaged_plain", "quantity": 1, "damage_percent": 100}],
            "documents_lost": ["aadhaar"], "bank_account_available": true},
 "missing_fields": ["phone"], "follow_up_questions": ["What is your phone number?"]}
```

**Member 3** `POST {MEMBER3_VERIFY_URL}/verify`, multipart: `photo=<file>`, `lat`, `lon`, `taken_at`, `claim_id`,
and `phone` when the claim has a valid one (for Member 3's "one phone, many claims" fraud check;
Member 3 keeps only a keyed fingerprint, never the number)
```json
{"damage_detected": true, "damage_score": 0.8, "gps_ok": true, "timestamp_ok": true,
 "duplicate": false, "notes": []}
```

Notes for both teams:
- The uploaded filename is ours (`recording.webm`, `photo.jpg`), never the user's. The part's
  content type is the real detected type.
- `taken_at` is sent as UTC ISO 8601 with `Z`. Empty `lat`, `lon` and `taken_at` are left out.
- Every call carries `X-Request-ID`. Please log it.
- Replies must be JSON with status 2xx. Timeouts, connection errors and 5xx are retried twice
  (0.5s, then 1s). A 4xx is not retried.
- From Member 1, unknown keys and invalid values (e.g. `"quantity":"two"`) are ignored. Those
  fields stay missing for the review screen. `null` never overwrites a known value.
- Member 3's `duplicate` is shown to officials only.
- Optional: `GET /health` on your service. Our `/health` reports you as `ok` for any non-5xx reply.

## Member 5's files

- `rules/sdrf_rules.json` holds **sample** rates. Replace it with no code change; its structure is
  checked at startup. While `version` starts with `sample`, `/health` shows a warning and the
  PDF prints "Estimated amount — subject to official verification".
- `rules/proof_substitution.json` holds the substitute proofs.
- `rules/labels.json` holds the PDF wording: item, category and document labels, and the
  consent statement for each `consent_text_version`.

## Layout

```
app/main.py              app, middleware (request ID, CORS, body limit), /health
app/config.py            env settings + production safety checks
app/db.py, models.py     async SQLAlchemy: claims, audio_recordings, photos, claim_status_events, audit_log
app/security.py          claim tokens, staff keys, rate limiter
app/uploads.py           type / magic-byte / size checks
app/storage.py           Fernet-encrypted file storage (UUID names)
app/logs.py              JSON logs + X-Request-ID
app/dev_mocks.py         DEVELOPMENT ONLY fake Member 1/3 answers
app/routers/             claims.py (claimant), status.py (tracking), staff.py (officials)
app/services/            relief.py (SDRF), integrations.py (Members 1/3), validation.py, pdf_builder.py (fpdf2)
fonts/                   Noto Sans fonts (Latin, Bengali, Devanagari, Tamil, Telugu, Symbols 2) + OFL licences
migrations/              Alembic
```

## Privacy (DPDP Act)

- Consent and its text version are stored with a timestamp before any data is collected.
- Uploads and PDFs are encrypted at rest.
- Claim data is reachable only with the claim's token, or a staff key.
- Every action, reads included, goes to `audit_log` with actor, action, request ID and IDs only:
  no names, phone numbers, transcripts or addresses.
- Application logs never contain personal data, tokens, keys or client IPs.
