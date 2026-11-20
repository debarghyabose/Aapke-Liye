# 🎨 Member 4: Frontend + Claim Tracking

**Name:** _your name_ · **GitHub:** _@handle_

## 🚀 Current sprint (2 hours) — your tasks

### Full offline app + screens for the others
- [x] **PWA:** a web app manifest + service worker (`vite-plugin-pwa`) so the app **opens with no internet** once visited, with an install-to-home-screen option.
- [x] **Offline claim start:** if offline, create the claim on the phone (temporary ID), queue the claim creation, recordings, typed answers and photos in IndexedDB (`src/utils/indexedDB.ts`), and send them in order when the signal returns. The upload logic already exists in `OfflineBanner.tsx`; extend it to claim creation and text. Show "Saved on this phone, N items waiting".
- [x] **`/prepare` page** (Member 2's APIs): register household, "My documents" cards (upload / DigiLocker button / delete), baseline photos. On claim step 1: "Use my household".
- [x] **Mesh screen** (Member 3's helper): "Hand to a neighbour" shows a QR code of the sealed claim; "Carry a claim" scans a QR code and uploads it when online; "Delivered ✓" from the receipt.
- [x] **Before/after** side by side on the photo step when Member 2 returns a comparison.
- [x] **"Is your village in a hilly area?"** on the Review screen (Yes / No), saved as `is_hilly` (same pattern as the crop insurance question).
- [x] New text in all six `src/locales/*.json` (run `npm run i18n:check`).
- **Done when:** with Wi-Fi off, the app opens, a claim is filed and saved on the phone, and it uploads by itself when Wi-Fi comes back.

### Mobile UI (the final product is a web app that also works as a phone app)
- [x] Every screen works at 360 px wide with no sideways scrolling; touch targets ≥ 48 px.
- [x] Camera and microphone work on Android Chrome (needs `https` or `localhost`).
- [x] "Add to home screen" installs the app with its own icon and opens full-screen.
- [x] Officials' map and queue are usable on a phone (map above, queue below).

**Rules:** work on your own branch `member-4/<feature>`, edit only your own folder (ask the owner otherwise), never commit `.env`, run your tests before pushing, then open a pull request into `main`. The team lead merges all four and builds the final web app (with mobile UI).
Full plan, timeline, demo script and what to cut if time runs out: [docs/next-features-plan.md](../docs/next-features-plan.md) · Mobile UI checklist: section 6 of the plan.

---

## Your job
You are the **only frontend person**: you build every screen in the demo. You also own one small backend piece, claim tracking. Everything is kept simple on purpose.

## Frontend: 5 screens
1. [x] **Language picker:** 6 buttons
2. [x] **Speak & snap:** one big record button and a camera button
3. [x] **Review:** shows the extracted fields with "Correct ✓ / Edit"
4. [x] **Your claim:** PDF download and claim ID
5. [x] **Track my claim:** status timeline, Submitted → Verified → Approved → Paid

## Backend: claim tracking only
- [x] One table `claims_status`: `claim_id`, `status`, `updated_at`
- [x] `GET /status/{claim_id}`: get a claim's status
- [x] `PUT /status/{claim_id}`: change a claim's status

## Why it stays simple
- No AI, no PDF generation, no offline logic. Members 1, 2 and 3 handle those on the backend.
- You only **call** their APIs: send the audio, get the claim back, show it.
- Plain HTML/CSS/JS or React with ready-made UI components.
- Start on day 1 with **fake JSON data**, then switch to the real APIs once they're ready.
- The government dashboard is a mock-up made by Member 5, so it's not on your list.

## You work with
- **Member 2:** gives you the API endpoints
- **Member 1:** follow-up questions to show on screen
