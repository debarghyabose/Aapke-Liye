# 🖥️ Member 5: Officials Dashboard & DevOps

**Name:** _your name_ · **GitHub:** _@handle_

## Your job
Build the officials' side (the paying customer) and get everything running on Google Cloud: one FastAPI service on **Cloud Run in Mumbai**.

## Workflow steps you own
| Step | What |
|---|---|
| — | **Officials' dashboard:** filter by block and status, show the original filing time |
| — | **Ask your claims:** question in plain words → Gemini → **read-only** SQL |
| ◇ | **Proof enough?** → **Approve** (relief released) or **Flag for field visit** |
| — | Deployment, CI, monitoring |

## Tasks
- [ ] Claim list with filters (district, block, status), sorted by **original filing time**, not sync time
- [ ] Claim detail page: form, photos, audio, AI checks, map pin
- [ ] Approve / Flag for field visit / Reject, with a note
- [ ] "Ask your claims": turn the question into SQL, allow only a single SELECT, run it on a **read-only database user** with a time limit and a row limit
- [ ] Login for officials
- [ ] Google Cloud setup: Cloud Run (`asia-south1`, Mumbai), AlloyDB, Cloud Storage, Secret Manager
- [ ] Dockerfile and deploy script
- [ ] GitHub Actions: run tests and deploy on every merge to `main`
- [ ] Logs, error alerts, basic usage numbers
- [ ] Demo data and the live demo script

## Timeline
| Week | Focus |
|---|---|
| 1 | GitHub setup, CI, Cloud Run skeleton, Google Cloud project |
| 2 | Dashboard list page, officials login, database + storage provisioned |
| 3 | Filters, claim detail page |
| 4 | Approve / flag / reject, claim history |
| 5 | "Ask your claims" on the read-only user |
| 6 | Monitoring, demo data, run the live demo |

## You work closely with
- **Member 4:** the API and database the dashboard reads
- **Member 3:** the prompt for "Ask your claims"

## Done when
An official can find any claim, ask a plain-language question and get a correct table back, then approve or flag the claim. The whole app deploys to Cloud Run automatically.
