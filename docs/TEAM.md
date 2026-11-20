# 👥 Team, Roles & Responsibilities

> Fill in your names and GitHub handles below, then update [`.github/CODEOWNERS`](../.github/CODEOWNERS) with the same handles.

| # | Name | GitHub | Role | Backup for |
|---|---|---|---|---|
| M1 | _name_ | `@handle` | 🎨 Citizen App & Experience | M2 |
| M2 | _name_ | `@handle` | 📴 Offline & Sync Engineer | M1 |
| M3 | _name_ | `@handle` | 🤖 AI Engineer | M4 |
| M4 | _name_ | `@handle` | 🗄️ Backend & Data Engineer | M3 |
| M5 | _name_ | `@handle` | 🖥️ Officials Dashboard & DevOps | M4 |

Each member has a **backup** who reviews their PRs and can take over if they are unavailable.

## How the work splits across the workflow

| Workflow step (from the diagram) | Owner | Helper |
|---|---|---|
| 1 · Open app, pick language | M1 | M2 (caching) |
| 2 · Consent, speak / photograph, GPS + time | M1 | M2 (saving) |
| ◇ Network works? (5 s test) | M2 | — |
| 3 · Gemini voice → claim JSON | M3 | M4 (route) |
| ◇ Fields missing? · 4 · Follow-up + Cloud TTS | M3 | M1 (playback UI) |
| 3b · Offline guided taps + prerecorded prompts | M1 | M2 |
| 4b · Estimate from cached SDRF rates | M2 | M4 (same rules on server) |
| 5 · Read-back, user confirms | M1 | M3 (TTS) |
| ◇ Documents lost? · 6 · Substitute proof + vision | M3 | M1 (camera UI) |
| 7 · Relief form PDF + claim ID + QR | M4 (server) | M2 (on-device draft) |
| Save on phone first (IndexedDB) | M2 | — |
| ◇ Network now? · Waiting · retries | M2 | — |
| Send JSON → audio → photos | M2 | M4 (endpoints) |
| 8 · Save in AlloyDB + Cloud Storage (upsert) | M4 | — |
| Server Gemini recheck, final PDF, status | M3 | M4 |
| Officials' dashboard | M5 | M4 (API) |
| Ask your claims (NL → read-only SQL) | M5 | M3 (prompting) |
| ◇ Proof enough? → Approve / Flag | M5 | M4 |
| Cloud Run, CI, secrets, monitoring | M5 | — |

---

## 🎨 M1 — Citizen App & Experience

**Owns:** `frontend/citizen-pwa/src/screens/`, `src/i18n/`, `src/styles.css`, `public/audio/prompts/`, `index.html`

- [ ] Screen router and app shell (big buttons, icons, high contrast)
- [ ] Language picker (6 languages) + persistent choice
- [ ] Consent screen with spoken explanation
- [ ] Capture screen: record voice (MediaRecorder), take photos, show GPS fix
- [ ] Follow-up question playback + "answer by voice" UI
- [ ] Offline guided-tap flow (3b) — question tree that produces the claim JSON
- [ ] Record / source prerecorded prompts in all 6 languages (+ number clips 0–9, hundred, thousand, lakh)
- [ ] Read-back screen: TTS online, stitched clips + on-screen text offline
- [ ] Documents-lost flow (camera for substitute proof)
- [ ] Done screen: claim ID, QR, PDF, sync badge
- [ ] Accessibility: works for low-literacy users, screen reader labels, ≥ 48 px tap targets

## 📴 M2 — Offline & Sync Engineer

**Owns:** `frontend/citizen-pwa/src/offline/`, `public/sw.js`, `public/manifest.webmanifest`, `src/api/`

- [ ] Service worker: app-shell cache, versioned, update in background
- [ ] IndexedDB wrapper (`claims`, `media`, `meta` stores)
- [ ] 5-second network test
- [ ] Sync engine: queue, lock, JSON → audio → photos, back-off
- [ ] Triggers: app open, `online` event, 30 s timer, Background Sync where supported
- [ ] SDRF estimator in JS, passing `shared/sdrf/test_vectors.json`
- [ ] Cache SDRF rates + version in `meta`
- [ ] On-device draft PDF + QR (jsPDF / qrcode)
- [ ] Media compression (Opus 16 kbps, photos ≤ 1280 px)
- [ ] Mid-flow fallback: hand partially extracted claim to guided flow

## 🤖 M3 — AI Engineer

**Owns:** `backend/app/services/gemini.py`, `tts.py`, `vision.py`, `backend/app/api/voice.py`

- [ ] Prompt + structured output: audio → claim JSON (schema-constrained)
- [ ] Missing-field detection and follow-up question generation in 6 languages
- [ ] Cloud TTS wrapper with per-language voices; cache common phrases
- [ ] Vision: substitute-proof check (kind, legibility, plausible match to claimant)
- [ ] Vision: damage-photo sanity check (is this disaster damage?)
- [ ] Server re-check of offline claims: re-extract from audio, diff vs guided taps → `needs_review` if they conflict
- [ ] Evaluation set: 30+ sample recordings across languages, track extraction accuracy
- [ ] Graceful degradation: return `ai_unavailable` fast so the phone falls back

## 🗄️ M4 — Backend & Data Engineer

**Owns:** `backend/app/main.py`, `api/claims.py`, `db/`, `schemas/`, `services/{relief,pdf,storage}.py`, `infra/migrations/`, `shared/schemas/`

- [ ] Freeze `claim.schema.json` v1 with the team (week 1)
- [ ] Pydantic models matching the schema
- [ ] AlloyDB schema + migrations; `claims`, `claim_media`, `claim_events`
- [ ] `PUT /claims/{id}` idempotent upsert, `PUT /media`, `GET /status`
- [ ] Cloud Storage uploads keyed by hash; signed URLs
- [ ] Relief calculation (`relief.py`) from SDRF table, passing shared test vectors
- [ ] Final PDF + QR rendering in all 6 languages (fonts!)
- [ ] Background processing pipeline + status transitions
- [ ] Duplicate-claim detection → `needs_review`
- [ ] Unit + integration tests

## 🖥️ M5 — Officials Dashboard & DevOps

**Owns:** `frontend/officials-dashboard/`, `backend/app/api/officials.py`, `services/nl_sql.py`, `infra/` (except migrations), `.github/`

- [ ] Dashboard: claim list, filters (district, block, status), sort by original filing time
- [ ] Claim detail view: form, photos, audio player, AI checks, map pin
- [ ] Approve / Flag for field visit / Reject with note
- [ ] "Ask your claims": NL → SQL, `SELECT`-only validation, read-only role, timeout, row limit
- [ ] Officials auth (dev token → Google Identity)
- [ ] Dockerfile, Cloud Run deploy script (`asia-south1`), Secret Manager
- [ ] GitHub Actions: lint, test, build, deploy on `main`
- [ ] Logging, error alerts, basic usage metrics
- [ ] Demo data seeding script

---

## 🤝 Shared responsibilities

- **Everyone:** reviews `shared/` changes, joins Wednesday integration check, writes tests for their own code.
- **Contract changes** (`shared/schemas`, `docs/API.md`) need sign-off from M1, M2, M3, M4.
- **Demo & pitch (week 6):** M1 leads the story, M5 runs the live demo, everyone presents their part.
