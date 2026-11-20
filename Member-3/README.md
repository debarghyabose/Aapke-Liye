# 🛰️ Member 3: Verification + Offline + Channels

**Name:** _your name_ · **GitHub:** _@handle_

## Your job
Make claims trustworthy for officials, make sure no claim is lost when the network drops, and reach people without smartphones.

## Phase 1: Core demo (build first)
- [ ] **Damage vision:** AI checks the damage photos
- [ ] **Basic verification:** check that the GPS location and timestamp look right
- [ ] **Basic duplicate check:** flag the same photo or claim sent twice
- [ ] **Offline sync:** queue uploads so nothing is lost when the network drops

## Phase 2: Roadmap features (after the demo works)
| Feature | What to do |
|---|---|
| Satellite verification | Check the claim location against Sentinel-1 / ISRO Bhuvan flood and damage maps, using PostGIS |
| Advanced fraud detection | Flag the same photo, house or person claiming twice |
| WhatsApp bot | File a claim by sending a voice note on WhatsApp |
| IVR / missed-call line | Feature-phone users call in and speak their claim |
| Voice/SMS status updates | Send each status change to the user in their own language |
| Dashboard data | Provide the map and damage data for the government dashboard that Member 5 designs |

## You work with
- **Member 2:** stores your verification results
- **Member 5:** uses your data for the dashboard
