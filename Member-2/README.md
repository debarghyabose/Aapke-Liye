# ⚙️ Member 2: Core Backend (CTO)

**Name:** _your name_ · **GitHub:** _@handle_

## 🚀 Current sprint (2 hours) — your tasks

### Document vault + DigiLocker (mock)
- [x] Tables `households` and `vault_documents` (migration `0003`). Files are encrypted with the existing Fernet storage.
- [x] `POST /households` → `household_token` (shown once, like `claim_token`). `POST/GET/DELETE /households/{id}/documents`. Types match `rules/proof_substitution.json` (`aadhaar`, `ration_card`, `land_record`, `bank_passbook`, …), plus `baseline_photo`.
- [x] **DigiLocker (mock, clearly labelled).** `DIGILOCKER_MODE=mock` (default). `GET /households/{id}/digilocker/start` → a page that looks like DigiLocker's consent screen with a **"Demo: DigiLocker mock"** banner → `GET /digilocker/callback` adds sample documents (Aadhaar, ration card) to the vault with `source=digilocker_mock`. Keep the same function shape as the real API (start → callback → list issued documents → fetch file), so switching to real DigiLocker later only changes `app/services/digilocker.py`. Never show mock documents as real: the PDF and the app say "DigiLocker (demo)".
- [x] `POST /claims/{id}/household` links a claim to a household. On submit, vault documents count as available: remove them from `documents_lost` and list them on the PDF.
- [x] **Before/after:** when a claim photo is uploaded and the household has a `baseline_photo`, call Member 1's `/v1/damage/compare` and save the result in the photo's verification.
- [x] **Hilly-area rate (10 min):** add `is_hilly: bool` to `ClaimFields`; when true, `relief.py` turns `fully_damaged_plain` into `fully_damaged_hilly` (₹1,30,000).
- [x] Tests: token required, file is encrypted, vault Aadhaar is not "lost", delete really deletes, hilly rate.
- **Status:** done on branch `member-2/vault` (125 tests pass). API for Member 4: [backend/README.md → Document vault](backend/README.md#document-vault--digilocker-demo-for-the-prepare-page).
- **Done when:** a household saved its Aadhaar before the flood, the claim links to it, and the PDF says "available in vault" instead of "lost".

**Rules:** work on your own branch `member-2/<feature>`, edit only your own folder (ask the owner otherwise), never commit `.env`, run your tests before pushing, then open a pull request into `main`. The team lead merges all four and builds the final web app (with mobile UI).
Full plan, timeline, demo script and what to cut if time runs out: [docs/next-features-plan.md](../docs/next-features-plan.md)

---

## Your job
Build the server that holds everything together, and connect every member's part.

## Phase 1: Core demo (build first)
- [ ] **FastAPI server** and the **PostgreSQL** database
- [ ] APIs: upload audio and photos, save the claim, return the result
- [ ] **Form builder:** fill the official relief form PDF from the claim data
- [ ] Calculate the relief amount using Member 5's SDRF rules (JSON)
- [ ] Connect Member 1 (AI), Member 3 (verification) and Member 4 (frontend)

## Phase 2: Roadmap features (after the demo works)
| Feature | What to do |
|---|---|
| Disaster document vault | Encrypted storage for ID, land records and bank details, plus DigiLocker linking |
| Household pre-registration | APIs for volunteers or panchayats to register families in advance, so claims are half-filled |
| Bulk mode | One NGO worker files claims for many families |
| DBT payment confirmation | Check that the relief money actually reached the account |
| Escalation trigger | If a claim is stuck in one status too long, start the escalation letter (written by Member 1's AI) |

## You work with
- **Everyone:** you own the APIs the others call
