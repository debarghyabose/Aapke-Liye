# 🎨 Member 4: Frontend + Claim Tracking

**Name:** _your name_ · **GitHub:** _@handle_

## Your job
You are the **only frontend person**: you build every screen in the demo. You also own one small backend piece, claim tracking. Everything is kept simple on purpose.

## Frontend: 5 screens
1. [ ] **Language picker:** 6 buttons
2. [ ] **Speak & snap:** one big record button and a camera button
3. [ ] **Review:** shows the extracted fields with "Correct ✓ / Edit"
4. [ ] **Your claim:** PDF download and claim ID
5. [ ] **Track my claim:** status timeline, Submitted → Verified → Approved → Paid

## Backend: claim tracking only
- [ ] One table `claims_status`: `claim_id`, `status`, `updated_at`
- [ ] `GET /status/{claim_id}`: get a claim's status
- [ ] `PUT /status/{claim_id}`: change a claim's status

## Why it stays simple
- No AI, no PDF generation, no offline logic. Members 1, 2 and 3 handle those on the backend.
- You only **call** their APIs: send the audio, get the claim back, show it.
- Plain HTML/CSS/JS or React with ready-made UI components.
- Start on day 1 with **fake JSON data**, then switch to the real APIs once they're ready.
- The government dashboard is a mock-up made by Member 5, so it's not on your list.

## You work with
- **Member 2:** gives you the API endpoints
- **Member 1:** follow-up questions to show on screen
