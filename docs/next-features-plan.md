# 2-hour sprint: standout features for Aapke Liye

**Start from:** `main` at commit `14d0c64`. Run everything with `.\start-all.ps1`.

## 0. Already connected (don't redo)

The full claim flow works on localhost:
- **Claiming:** voice or typing → Gemini fills the claim → follow-up questions with Listen → photo checks (Gemini damage, GPS, time, Copernicus flood map, duplicates).
- **Review:** SDRF relief with household caps, PMAY-G and PMFBY "may also qualify", lost-document alternatives, and "who needs help first".
- **After submitting:** PDF, ready-to-sign letters (Member 1 + Member 5 templates), and tracking with the next recommended letter (Member 1's escalation ladder).
- **Officials:** `/official` with a live map (Member 3 data + satellite flood extent), fraud flags, vulnerable families first, and status changes.

## 1. What is missing (checked in the code)

| Feature | In the code? | Why it matters for the score |
|---|---|---|
| **Works with no network** | 🟡 Half. Recordings and photos are queued offline, but the **app itself won't open without internet**, and starting a claim needs the server | UX 10%, Innovation 5%, the core promise of a disaster app |
| **Phone-to-phone relay (mesh)** | ❌ Spec only (`Member-5/docs/network_mesh_spec.md`) | Innovation 5%, the strongest story on stage |
| **Document vault + DigiLocker** | ❌ Not at all | Problem fit 15%: papers saved *before* the disaster |
| **Before/after photos** | 🟡 Member 1 has `/v1/damage/compare`, nothing uses it | Google AI 20%, Problem fit 15% |
| **Gemini for speech** | ❌ Speech uses Whisper (OpenAI) | **Google AI 20%**, the biggest scoring risk |

## 1b. Built but still not connected

| # | Piece | Why it's not connected | Owner |
|---|---|---|---|
| 1 | **Hilly-area house rate** (₹1,30,000 vs ₹1,20,000, already in `sdrf_rules.json`) | The app never asks whether the area is hilly, so it always uses the plains rate | Member 2 (backend field) + Member 4 (question on Review) |
| 2 | **WhatsApp bot + IVR line** (`Member-3/app/whatsapp.py`, `ivr.py`, built and tested) | Twilio can't reach localhost. Needs a tunnel (`cloudflared` / `ngrok`) in `PUBLIC_BASE_URL` and the webhook URLs in the Twilio console | Member 3 |
| 3 | **Before/after comparison** (`Member-1` `/v1/damage/compare`) | There's nowhere to keep a "before" photo until the vault exists | Member 1 (make it live) + Member 2 (call it from the vault) |
| 4 | **State top-ups** (`Member-5/rules/states/*.json`) | The files have no top-up amounts yet; only offices and document alternatives | Member 5 adds the amounts; then Member 2 adds them in `relief.py` (outside this sprint) |

## 2. Who does what (about 90 minutes each)

The four tracks barely touch the same files, so they can be built at the same time.

| Member | Track | Main files |
|---|---|---|
| **Member 1** | Gemini speech + before/after AI | `Member-1/app/asr.py`, `pipeline.py`, `damage.py` |
| **Member 2** | Document vault + DigiLocker (mock) | `Member-2/backend/app/routers/vault.py` (new), `models.py`, migration `0003` |
| **Member 3** | Mesh "lite": sealed claim handed phone to phone | `Member-3/app/mesh.py` (new), `Member-3/offline-client/` |
| **Member 4** | Full offline app (PWA) + screens for the other three | `Member-4/frontend/` |

### Member 1: Gemini speech + before/after (Google AI 20%)
- [ ] **Gemini hears the voice note.** In `asr.py`, add `ASR_PROVIDER=gemini|whisper` (default `gemini`). Send the 16 kHz WAV to Gemini as audio and ask for the transcript plus language. Keep Whisper as the fallback when Gemini fails or there's no key. *Even better:* one Gemini call from audio straight to claim fields (skips a step, faster).
- [ ] Return `asr_provider: "gemini"` in the turn response, so it shows on stage and in `/health`.
- [ ] **Before/after:** make `/v1/damage/compare` real with Gemini (it already exists, tested in mock mode only). Member 2 will call it when a claim photo has a baseline photo from the vault.
- [ ] Tests: provider switch, fallback to Whisper, compare in mock and live.
- **Done when:** a Hindi voice note is transcribed by Gemini (Whisper turned off) and the claim fills in.

### Member 2: Document vault + DigiLocker (mock)
- [ ] Tables `households` and `vault_documents` (migration `0003`). Files are encrypted with the existing Fernet storage.
- [ ] `POST /households` → `household_token` (shown once, like `claim_token`). `POST/GET/DELETE /households/{id}/documents`. Types match `rules/proof_substitution.json` (`aadhaar`, `ration_card`, `land_record`, `bank_passbook`, …), plus `baseline_photo`.
- [ ] **DigiLocker (mock, clearly labelled).** `DIGILOCKER_MODE=mock` (default). `GET /households/{id}/digilocker/start` → a page that looks like DigiLocker's consent screen with a **"Demo: DigiLocker mock"** banner → `GET /digilocker/callback` adds sample documents (Aadhaar, ration card) to the vault with `source=digilocker_mock`. Keep the same function shape as the real API (start → callback → list issued documents → fetch file), so switching to real DigiLocker later only changes `app/services/digilocker.py`. Never show mock documents as real: the PDF and the app say "DigiLocker (demo)".
- [ ] `POST /claims/{id}/household` links a claim to a household. On submit, vault documents count as available: remove them from `documents_lost` and list them on the PDF.
- [ ] **Before/after:** when a claim photo is uploaded and the household has a `baseline_photo`, call Member 1's `/v1/damage/compare` and save the result in the photo's verification.
- [ ] **Hilly-area rate (10 min):** add `is_hilly: bool` to `ClaimFields`; when true, `relief.py` turns `fully_damaged_plain` into `fully_damaged_hilly` (₹1,30,000).
- [ ] Tests: token required, file is encrypted, vault Aadhaar is not "lost", delete really deletes, hilly rate.
- **Done when:** a household saved its Aadhaar before the flood, the claim links to it, and the PDF says "available in vault" instead of "lost".

### Member 3: Mesh "lite" (no Android needed today)
A native phone-to-phone mesh takes weeks. For today, the same idea with what a browser can do: a **sealed claim passed by QR code or file** to a neighbour's phone, which uploads it when it has signal.
- [ ] `GET /mesh/public-key` and `POST /mesh/envelopes` in Member 3's service. Generate the key pair once (keys in `.env`). Decrypt the envelope, reject expired or too-large ones (limits in `Member-5/rules/mesh_policy.json`), ignore duplicates by `claim_id`, then file the claim through Member 2's normal `/claims` APIs (as `whatsapp.py` already does).
- [ ] `GET /mesh/receipts/{claim_id}` → a signed receipt, so the first phone can show "Delivered".
- [ ] A small browser helper for Member 4: `sealClaim(claim, publicKey)` (WebCrypto: AES-GCM for the data, RSA-OAEP or X25519 for the key) → envelope JSON (+ text for a QR code).
- [ ] Tests: tampered, expired, duplicate and oversized envelopes rejected; valid envelope becomes a claim.
- [ ] **WhatsApp + IVR live (20 min):** run `cloudflared tunnel --url http://localhost:8002` (or `ngrok http 8002`), put the https URL in `PUBLIC_BASE_URL` in `Member-3/.env`, and set the Twilio WhatsApp sandbox webhook to `<url>/webhook` and the voice number to `<url>/voice`. This makes the computer reachable from the internet while the tunnel runs; stop it after the demo.
- **Done when:** phone A (airplane mode) shows a QR code, phone B scans it, turns on data, and the claim appears on `/official`.

### Member 4: Full offline app + screens for the others
- [ ] **PWA:** a web app manifest + service worker (`vite-plugin-pwa`) so the app **opens with no internet** once visited, with an install-to-home-screen option.
- [ ] **Offline claim start:** if offline, create the claim on the phone (temporary ID), queue the claim creation, recordings, typed answers and photos in IndexedDB (`src/utils/indexedDB.ts`), and send them in order when the signal returns. The upload logic already exists in `OfflineBanner.tsx`; extend it to claim creation and text. Show "Saved on this phone, N items waiting".
- [ ] **`/prepare` page** (Member 2's APIs): register household, "My documents" cards (upload / DigiLocker button / delete), baseline photos. On claim step 1: "Use my household".
- [ ] **Mesh screen** (Member 3's helper): "Hand to a neighbour" shows a QR code of the sealed claim; "Carry a claim" scans a QR code and uploads it when online; "Delivered ✓" from the receipt.
- [ ] **Before/after** side by side on the photo step when Member 2 returns a comparison.
- [ ] **"Is your village in a hilly area?"** on the Review screen (Yes / No), saved as `is_hilly` (same pattern as the crop insurance question).
- [ ] New text in all six `src/locales/*.json` (run `npm run i18n:check`).
- **Done when:** with Wi-Fi off, the app opens, a claim is filed and saved on the phone, and it uploads by itself when Wi-Fi comes back.

## 3. Timeline

| Time | Everyone |
|---|---|
| 0:00–0:10 | Agree on 3 contracts: vault API (Member 2 ↔ Member 4), envelope format + public key (Member 3 ↔ Member 4), `/v1/damage/compare` request (Member 1 ↔ Member 2). Write them into each README. |
| 0:10–1:30 | Build own track, with own tests. Member 4 uses mock data until the APIs are ready. |
| 1:30–1:45 | Merge one member at a time into `main` (Member 1 → Member 2 → Member 3 → Member 4), run every test suite and `.\start-all.ps1` after each. |
| 1:45–2:00 | Rehearse the demo below twice. |

**Rules:** one branch per member (`member-N/<feature>`). Don't edit another member's folder; ask them. Never commit `.env`.

## 4. The demo (about 4 minutes)

1. **Before the flood:** on `/prepare`, register a household, pull Aadhaar from DigiLocker (mock, say "demo" on stage), add a baseline photo of the house.
2. **The flood, no network:** turn Wi-Fi off. The app still opens. Speak in Hindi, add the Puri photo (`Member-3/data/demo/stage/`, regenerate it that morning). It's saved on the phone.
3. **Mesh:** "Hand to a neighbour" → the second phone scans the QR code and turns on data → the claim arrives.
4. **The result:** Gemini filled the claim. Before/after damage score. SDRF ₹ plus PMAY-G/PMFBY. Aadhaar shown as "available in vault", not lost. Download the PDF and the ready letters.
5. **Officials:** `/official` shows the live map with the satellite flood extent; the vulnerable family is at the top; mark Verified; the first phone's Track page updates.

## 5. If time runs out, cut in this order
1. The mesh QR code (keep the spec and Member 5's demo script as the story)
2. DigiLocker mock (keep plain vault upload)
3. Before/after
4. **Never cut:** Gemini speech (Member 1) and the offline app (Member 4). They carry the most points.

## 6. After the sprint: merging into the final product

Each member pushes their branch (`member-N/<feature>`) and opens a pull request into `main`. The team lead then pulls everything, connects the remaining pieces, runs every test suite and `.\start-all.ps1`, and produces the final product: **one web app that also works as a mobile app** (responsive phone layout, installable to the home screen, works offline).

**Mobile UI checklist (Member 4, checked again at merge):**
- [ ] Every screen works at 360 px wide with no sideways scrolling; touch targets ≥ 48 px.
- [ ] Camera and microphone work on Android Chrome (needs `https` or `localhost`; for phones on the same Wi-Fi, use a tunnel or `vite --host` with https).
- [ ] "Add to home screen" installs the app with its own icon and opens full-screen.
- [ ] Officials' map and queue are usable on a phone (map above, queue below).

**Later (not this sprint): real DigiLocker.** Needs the team's organisation to register as a DigiLocker requester (official email domain, use-case review, committee approval; weeks). Then only `app/services/digilocker.py` changes from mock to real OAuth.
