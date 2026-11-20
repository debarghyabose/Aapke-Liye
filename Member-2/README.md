# ⚙️ Member 2: Core Backend (CTO)

**Name:** _your name_ · **GitHub:** _@handle_

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
