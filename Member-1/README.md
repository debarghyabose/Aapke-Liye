# 🎨 Member 1: Citizen App & Experience

**Name:** _your name_ · **GitHub:** _@handle_

## Your job
Build every screen the citizen sees in the phone app (PWA), in all **6 languages** (Hindi, Bengali, Marathi, Tamil, Telugu, English), including the **offline guided-tap flow** that works with no network.

## Workflow steps you own
| Step | What |
|---|---|
| 1 | Open app, pick 1 of 6 languages |
| 2 | Consent, then speak or photograph the damage (show GPS + time) |
| 3b | **Offline:** guided taps + prerecorded voice prompts → claim JSON |
| 4 | Play Gemini's follow-up question, record the spoken answer (with Member 3) |
| 5 | Read the claim back and let the user confirm |
| 6 | Documents-lost screen: camera for substitute proof |
| 7 | Done screen: claim ID, QR, PDF, "waiting for network" badge |

## Tasks
- [ ] App shell and screen navigation: big buttons, icons, high contrast
- [ ] Language picker that remembers the choice
- [ ] Consent screen with a spoken explanation
- [ ] Capture screen: voice recording, photos, GPS fix
- [ ] Follow-up question playback and "answer by voice"
- [ ] Offline guided-tap question flow that produces the same claim JSON as the online path
- [ ] Prerecorded prompts in all 6 languages, plus number clips (0–9, hundred, thousand, lakh) for offline read-back
- [ ] Read-back screen: Cloud TTS online, stitched clips + on-screen text offline
- [ ] Documents-lost flow and done screen
- [ ] Accessibility: works for low-literacy users, tap targets ≥ 48 px, screen-reader labels

## Timeline
| Week | Focus |
|---|---|
| 1 | App shell, language + consent screens |
| 2 | Capture screen (voice + photo + GPS) |
| 3 | Follow-up playback, read-back (online) |
| 4 | Offline guided-tap flow, prerecorded prompts |
| 5 | Documents-lost flow, done screen, accessibility pass |
| 6 | Field test with 3–5 real users, fix what they struggle with |

## You work closely with
- **Member 2:** saving claims offline and the sync badge
- **Member 3:** follow-up questions and text-to-speech

## Done when
A first-time user can file a full claim by voice (online) in ≤ 5 min and by taps (offline) in ≤ 7 min, in any of the 6 languages.
