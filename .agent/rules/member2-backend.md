# Rules for agents working on Member-2/backend

- This is the Aapke Liye core backend: Python 3.11+, FastAPI, SQLAlchemy 2, reportlab.
- Only edit files inside `Member-2/`. Other members' folders belong to them.
- Do not change the API paths or the JSON shapes in `app/services/integrations.py` and
  `README.md` without saying so: Members 1, 3 and 4 code against them.
- Relief amounts come only from `rules/sdrf_rules.json`. Never hard-code rupee amounts in Python.
- After any change, run `python -m pytest -q` and keep it passing; add a test for new endpoints.
- Never commit `.env`, `*.db` or `storage/`.
