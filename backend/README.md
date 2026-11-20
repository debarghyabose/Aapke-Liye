# ⚙️ Backend — FastAPI on Cloud Run (Mumbai)

**Owners:** 🗄️ **M4** (API, data, PDF, relief) · 🤖 **M3** (AI services) · 🖥️ **M5** (officials routes, NL → SQL)

One FastAPI service that holds the API, the AI calls and the officials dashboard.
Planned stack: Python 3.12, FastAPI, SQLAlchemy, AlloyDB, Cloud Storage, Gemini, Cloud TTS.

| Folder | Owner | What goes here |
|---|---|---|
| `app/api/` | M4 · M3 · M5 | HTTP routes |
| `app/services/` | M3 · M4 · M5 | Business logic and Google AI calls |
| `app/db/` | M4 | Database models and session |
| `app/schemas/` | M4 | Pydantic models matching `shared/schemas/claim.schema.json` |
| `tests/` | everyone | Tests for your own code |

Planned top-level files: `app/main.py`, `app/config.py`, `requirements.txt`, `Dockerfile` (M5).

Endpoints: [`docs/API.md`](../docs/API.md) · Tables: [`docs/DATA_MODEL.md`](../docs/DATA_MODEL.md)
