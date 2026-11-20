# 🧪 tests/ — everyone

Each member writes tests for their own code. Planned:

| Planned file | Owner | Checks |
|---|---|---|
| `test_claims_api.py` | M4 | Upsert is idempotent; sending twice makes no duplicate |
| `test_relief.py` | M4 | Passes every case in `shared/sdrf/test_vectors.json` |
| `test_gemini.py` | M3 | Extraction on the eval set of sample recordings |
| `test_nl_sql.py` | M5 | Anything but a single SELECT is rejected |
