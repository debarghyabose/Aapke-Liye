# 🔗 shared/ — the contract

Everything here will be read by **both** the phone and the server. Changing it changes the whole app.

| Planned file | What | Read by |
|---|---|---|
| `schemas/claim.schema.json` | JSON Schema for a claim (v1) — fields in [`docs/DATA_MODEL.md`](../docs/DATA_MODEL.md) | PWA, FastAPI, Gemini prompt |
| `sdrf/sdrf_rates.json` | Relief rates used for estimates, with `version` + `effective_from` | PWA estimator (M2), `relief.py` (M4) |
| `sdrf/test_vectors.json` | Sample claims + expected relief — both calculators must pass | JS + Python tests |

**Owner:** 🗄️ M4 · **Changes need approval from:** M1, M2, M3, M4 (see CODEOWNERS).
**Due:** schema v1 frozen by end of week 1 ([work plan](../docs/WORK_PLAN.md)).

> ⚠️ Take SDRF rates from the latest MHA SDRF/NDRF notification for your state, and verify them before production use.
