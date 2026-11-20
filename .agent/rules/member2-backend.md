# Rules for agents working on Member-2/backend

- This is the Aapke Liye core backend: Python 3.11+, FastAPI, async SQLAlchemy 2, Alembic,
  fpdf2 (with uharfbuzz text shaping) for the PDF.
- Only edit files inside `Member-2/`. Other members' folders belong to them.
- Do not change the API paths, headers or JSON shapes in `app/services/integrations.py` and
  `README.md` without saying so: Members 1, 3 and 4 code against them.
- Relief amounts come only from `rules/sdrf_rules.json`. Never hard-code rupee amounts in Python.
- Endpoints are async: no blocking calls inside them (use `run_in_threadpool` for CPU or file work).
- Never put personal data (names, phones, transcripts, addresses), tokens or keys in logs or in
  `audit_log.detail`. Never use a client filename in a path.
- Fake Member 1/3 data lives only in `tests/` and `app/dev_mocks.py` (MOCK_SERVICES=true, dev only).
- Schema change: edit `app/models.py`, then `alembic revision --autogenerate`, review it, commit it.
- After any change, run `python -m pytest -q` and keep it passing; add a test for new endpoints.
- Never commit `.env`, `*.db` or `storage/`. `fonts/` (with its OFL licences) is committed.
