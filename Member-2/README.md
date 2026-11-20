# 📴 Member 2: Offline & Sync Engineer

**Name:** _your name_ · **GitHub:** _@handle_

## Your job
Make sure **no claim is ever lost**. The app must open, finish and save a claim with zero network, then send it by itself when signal returns.

## Workflow steps you own
| Step | What |
|---|---|
| ◇ | **Network works?** 5-second test |
| 4b | Estimate relief from cached SDRF rates (shown as "estimated") |
| 7 | Draft PDF + QR on the phone when offline |
| — | **Save on phone first** (IndexedDB, always) |
| ◇ | **Network now?** → waiting badge + offline reference number |
| — | Retries: on app open, when signal returns, every 30 s |
| — | Send in order: **claim JSON → audio → photos** |

## Tasks
- [ ] Service worker: cache the app so it opens offline and stays fresh
- [ ] Web app manifest so the PWA can be installed
- [ ] IndexedDB storage for claims, media and settings
- [ ] 5-second network test (don't trust the signal icon)
- [ ] Save every claim on the phone **before** any upload
- [ ] Sync queue: JSON first, then audio, then photos; resume after interruptions
- [ ] Retry triggers (app open, `online` event, 30 s timer) with back-off
- [ ] Generate the claim ID (UUID) on the phone so retries never create duplicates
- [ ] Cache SDRF rates with a version number; calculate the estimate exactly like the server does
- [ ] Draft PDF + QR on the phone
- [ ] Shrink audio and photos before saving (low storage, 2G networks)
- [ ] If the network drops mid-conversation, hand what's filled so far to the guided-tap flow

## Timeline
| Week | Focus |
|---|---|
| 1 | IndexedDB storage, service worker |
| 2 | Network test, save-first flow, first sync of claim JSON |
| 3 | Media uploads in order, retries and back-off |
| 4 | SDRF estimator, draft PDF + QR |
| 5 | Mid-flow fallback, background sync, compression |
| 6 | Tests: 2G, killing the app mid-upload, airplane mode, storage limits |

## You work closely with
- **Member 1:** screens that save and show sync status
- **Member 4:** the upload endpoints and the server's relief calculation

## Done when
In airplane-mode and kill-the-app tests, **0 claims are lost and 0 duplicates** reach the server, and the claim JSON gets through on a 2G connection in ≤ 5 s.
