# ⚙️ Member 2 — Core Backend (FastAPI)

Claims, audio/photo uploads, SDRF relief calculation, proof substitution and the relief form PDF.
Calls Member 1 (AI) and Member 3 (verification); serves Member 4 (frontend). Runs with **mocks**
for Members 1 and 3 until their services are ready.

## Run

```bash
cd Member-2/backend
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # Windows: copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs to try every endpoint. Run tests with `python -m pytest -q`.

## API (for Member 4)

| Method | Path | Body | What it does |
|---|---|---|---|
| POST | `/claims` | `{"language":"bn"}` | Start a claim → returns `id` |
| POST | `/claims/{id}/audio` | multipart `audio` | Sends to Member 1, saves fields, returns follow-up questions |
| POST | `/claims/{id}/photos` | multipart `photo`, `lat`, `lon`, `taken_at` | Sends to Member 3, stores result + duplicate check |
| PATCH | `/claims/{id}` | `{"fields":{...}}` | Review-screen edits; relief recalculated |
| POST | `/claims/{id}/submit` | — | Builds PDF, status → Submitted |
| GET | `/claims/{id}` | — | Full claim |
| GET | `/claims/{id}/pdf` | — | Download relief form |
| GET/PUT | `/status/{id}` | `{"status":"Verified"}` | Tracking (Member 4 can take this over) |
| GET | `/health`, `/rules/sdrf` | — | Health check, current relief rules |

Languages: `en hi bn te mr ta`.

## Contracts for teammates
See the docstring at the top of `app/services/integrations.py`: the exact request and response
Member 1 (`POST /process`) and Member 3 (`POST /verify`) must provide. Set `MEMBER1_AI_URL` /
`MEMBER3_VERIFY_URL` in `.env` to switch from mocks to their real services.

## Member 5's files
`rules/sdrf_rules.json` and `rules/proof_substitution.json` hold **sample** numbers. Member 5 replaces
them; no code change needed. Losses use `{"category","item","quantity","damage_percent"}` keys
matching that file.

## Layout
```
app/main.py              app, CORS, routers
app/config.py            env settings
app/db.py, models.py     SQLAlchemy: claims, photos, claim_status_events, audit_log
app/routers/claims.py    claim APIs
app/routers/status.py    tracking APIs
app/services/relief.py   SDRF calculation + proof substitution
app/services/integrations.py  Member 1 / Member 3 clients (+ mocks)
app/services/pdf_builder.py   relief form PDF (reportlab)
```

## Known limits / next
- PDF uses Helvetica, so Bengali/Hindi text in names won't render. Register a Noto Sans font
  (e.g. NotoSansBengali) in `pdf_builder.py` for local-script fields.
- Tables are created on startup (`create_all`); add Alembic if the schema starts changing often.
- No auth yet. Phase 2: vault, pre-registration, bulk mode, DBT check, escalation trigger.
