# 🗄️ Member 4: Backend & Data Engineer

**Name:** _your name_ · **GitHub:** _@handle_

## Your job
Build the FastAPI server and the database: receive claims safely, store them, calculate relief and produce the final relief form. You also own the **claim format** that the whole team builds on.

## Workflow steps you own
| Step | What |
|---|---|
| — | **Claim JSON format**: agreed with everyone in week 1 |
| 7 | Final relief form **PDF + claim ID + QR** |
| 8 | Save claim in **AlloyDB**, media in **Cloud Storage** (upsert by claim ID) |
| — | Server: recheck relief amount, final PDF + status |

## Tasks
- [ ] Write and freeze the claim JSON format with the whole team (week 1)
- [ ] FastAPI app with a health check (used by the phone's network test)
- [ ] Database tables: claims, media, claim history
- [ ] Claim upload that is safe to repeat (upsert by claim ID, no duplicates)
- [ ] Audio/photo upload to Cloud Storage, stored by file hash so re-uploads do nothing
- [ ] Claim status endpoint for the phone
- [ ] Relief calculation from SDRF rates, matching the phone's estimate exactly
- [ ] Final PDF + QR that renders correctly in all 6 scripts (bundle Noto fonts)
- [ ] Background pipeline: claim arrives → AI recheck → relief → PDF → status
- [ ] Flag possible duplicate claims for review (never auto-reject)
- [ ] Tests for the API and the relief calculation

## Timeline
| Week | Focus |
|---|---|
| 1 | Claim format (whole team), database design |
| 2 | Claim upload + status API |
| 3 | Media uploads to Cloud Storage, relief calculation |
| 4 | Final PDF + QR, status pipeline |
| 5 | Duplicate detection, integration tests |
| 6 | Load test (500 claims), bug fixes |

## You work closely with
- **Member 2:** uploads and retries from the phone
- **Member 3:** where AI runs on the server
- **Member 5:** the data the dashboard reads

## Done when
Sending the same claim many times gives **one** record, relief amounts match the phone's estimate for standard cases, and every synced claim gets a final PDF and status.
