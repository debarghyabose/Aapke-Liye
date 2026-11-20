# Member 5 Review & Proposals for the Team

**From:** Member 5 (Entitlement, Policy & Pitch)
**Date:** 2026-11-21
**What this is:** a review of Member 5's work: its problems, what to change, and what each member needs to do. Each member's section ends with a full prompt they can paste into their coding agent.

---

## 1. Where things stand

| Member | State today |
|---|---|
| **Member 5** | ✅ **COMPLETE & FULLY TESTED (27/27 tests pass).** All calculation fixes (C1–C6), two-block multi-scheme architecture (I1), statutory citations (I2), network mesh spec (`docs/network_mesh_spec.md`), policy (`rules/mesh_policy.json`), 6-language carrier consent (`rules/labels.json`), and 30-sec demo script (`pitch/demo_script.md`) are implemented. |
| **Member 1** | Works (42/42 tests), but `Member-1/app/templates/*.txt` are still placeholders (`### PLACEHOLDER TEMPLATE ...`). Member 5's real letters are not used. |
| **Member 2** | Works (92/92 tests), but `Member-2/backend/rules/` holds an older copy of Member 5's rules (`sample-2022-26`; proof list has 5 documents, not 8). |
| **Member 3** | Connected the dashboard to live data, added fraud and satellite checks. Already has `POST /sync`. |
| **Member 4** | Nothing built yet (README only). |

Already checked: Members 1 and 2 pass their tests using Member 5's files (42/42 and 91/92). Switching to Member 5's files needs no logic change. The one failing Member 2 test checks old wording (see section 4.2).

---

## 2. Problems found

### 2.1 Calculation errors (found by running the code)

| # | Case | What happens | Should happen | Where |
|---|---|---|---|---|
| C1 | Crop entered as two lines of 2 ha each | ₹34,000 (one 4 ha line gives ₹17,000) | 2 ha cap applies to the **household**, across all crop lines | Member 5 `engine/entitlement.py` **and** Member 2 `app/services/relief.py` |
| C2 | Crop with no damage % | Paid as eligible | Not paid until damage % is known; ask the victim | Member 5 + Member 2 (calculation), Member 1 (ask the question) |
| C3 | PMFBY with 0% damage | ₹65,000 | ₹0 (code treats `0` as `100`) | Member 5 `engine/multi_scheme.py` |
| C4 | 10 large milch animals | ₹3,75,000 | Per-household animal limit, **if** the MHA 2022-26 letter keeps one (older norms: 3 large milch, 30 small milch, 3 large draught, 6 small draught). Check the letter first. | Member 5 `rules/sdrf_rules.json` + both calculators |
| C5 | PMFBY payout | Ignores indemnity level (70/80/90%) that is already in `pmfby.json` | Apply indemnity level; label sum insured as an example, since each district sets its own | Member 5 |
| C6 | PMAY-G amounts | Typed into Python (`120000`, `24750`, `12000`) | Read from `rules/schemes/pmay_g_disaster.json` | Member 5 |

### 2.2 Architecture problems

| # | Problem | Effect | Fix |
|---|---|---|---|
| A1 | Rules and letters are **shared by copying** files into other folders | Copies have already gone out of date (Members 1 and 2) | Members 1 and 2 read Member 5's folder directly via a path setting; keep a local copy only as a fallback for Docker, with a test that fails if it differs |
| A2 | The calculation is **written twice** (Member 2 `relief.py`, Member 5 `entitlement.py`) | Every fix must be made twice; they will drift | Short term: fix both and share one set of test cases. Long term: one calculator (see A3) |
| A3 | **Multi-scheme (PMAY-G + PMFBY) is used only by Member 5's CLI** | The pitch's ₹3,79,750 headline never reaches a real user | Member 2 calls Member 5's engine (pure Python, no dependencies) when the Member 5 folder is available, and returns its "may qualify" list with the claim |
| A4 | Folder rule says only Member 5 edits `Member-5/`, but Member 3 wrote ~half of `dashboard/index.html` | Rule and practice don't match | Agree: Member 3 may edit `Member-5/dashboard/` (update `.agent/rules/member5.md`), or move the dashboard to Member 3 |

### 2.3 Idea-level problems

| # | Problem | Fix |
|---|---|---|
| I1 | **Over-promising.** Every fully damaged house shows SDRF + PMAY-G = ₹2,76,750. PMAY-G needs the family to be on the Awaas+ list with no other pucca house. SDRF needs an officially notified disaster and an official assessment. | Show two separate blocks: **"Relief owed (SDRF estimate)"** and **"You may also qualify for"**, each with its conditions. Never add them into one "you will get" total. |
| I2 | README says "Official MHA rates", but the rules file is versioned `sample-…` and nothing cites the source per rate | Every rate and every state proof rule gets a `source` field (letter number, date, clause). Change wording to "based on MHA norms 2022-26" until checked. |
| I3 | Letters are English only; the victim signs something they may not be able to read | Member 1 reads each letter back in the victim's language (TTS already exists); Member 4 shows a "Listen to this letter" button |
| I4 | Network mesh needs a native Android app, while Member 4 has no screens yet | For the buildathon: spec + pitch demo only. Build after the 5 core screens. |

### 2.4 Corrections to the network-mesh proposal

The mesh plan that was circulated is mostly right. These parts need correcting:

| Topic | Keep | Change |
|---|---|---|
| Storage | Cap relay storage per phone (≈30 MB, ≈20–30 claims); 7-day expiry; delete after receipt | **Drop the 64-byte Bloom filter.** For 400 claims it gives ~50% false "already have it", so claims get skipped. Send the plain list of claim IDs (≈6 KB for 400). |
| Priority | Urgent claims first | Only a coarse `urgent / normal` flag outside the envelope. A full VPI score leaks how badly someone is hurt. |
| Encryption | One-time AES-256-GCM key, wrapped with the server's public key | **Add a sender signature (per-device key) and a per-device rate limit.** Without it anyone can flood the mesh with junk envelopes. |
| Legal | Relay phones hold only sealed data; opt-in consent | "Mere conduit" comes from IT Act Section 79, not the DPDP Act. The Post Office Act of 1898 was replaced in 2023. Call it "our position", not a "legal opinion". |
| Battery | Scan in short windows (e.g. 30 s every 15 min) or when moving; stop in battery saver; floor 20–25% | Android needs a foreground service for background Bluetooth. Say so in the spec. |
| Receipts | Signed receipt carried back through the mesh (already in the original plan) | Receipt = server's signature over `claim_id + timestamp` (the key is not part of the message), ≈100 bytes. Show **"Your claim reached the relief office"**, never "Verified by Treasury". Delivered ≠ paid. |
| Code | Spec, policy file, consent text, demo script | **Skip `engine/mesh.py` for now.** Nothing would call it. Build it only when Member 3's relay code will import it. |

---

## 3. Member 5's Implementation (All Completed)

1. [x] **Fix C1–C6 in the Member 5 engine, with a test for each:**
   - **C1:** Household-wide 2.0 ha crop cap enforced across all crop lines in `engine/entitlement.py`.
   - **C2:** Losses with missing `damage_percent` routed to `unmatched` with reason `"Damage percent needed"` (₹0 payout).
   - **C3:** PMFBY 0% damage yields ₹0 (does not default to 100%).
   - **C4:** Per-household livestock caps enforced in `rules/sdrf_rules.json` (3 large milch, 30 small milch, 3 large draught, 6 small draught) and `engine/entitlement.py`.
   - **C5:** Applied PMFBY indemnity level (`0.80` from `rules/schemes/pmfby.json`); benchmark disclaimer added.
   - **C6:** PMAY-G amounts dynamically loaded from `rules/schemes/pmay_g_disaster.json` (zero hardcoded rupees).
2. [x] **Split results into "Relief owed" and "May also qualify", with conditions (I1):**
   - Strictly separated into `relief_owed` (SDRF statutory entitlement) and `may_also_qualify` (conditional reconstruction/insurance grants) across `multi_scheme.py`, `cli.py`, and `pitch/demo_script.md`.
3. [x] **Add `source` fields to rates and state rules; fix "official" wording (I2):**
   - Full statutory citations added to `sdrf_rules.json`, `pmfby.json`, `pmay_g_disaster.json`, and all 5 state files (WB, OD, AS, MH, TN). Wording in README updated to "Based on MHA SDRF norms 2022-26 (estimate until verified)".
4. [x] **Network mesh deliverables completed:**
   - Spec: `docs/network_mesh_spec.md` (store-and-forward, AES-256-GCM wrapped, 1.5MB budget, 25-claim cap, 7-day TTL, Ed25519 signed receipts, 25% battery floor, Android foreground service requirement, IT Act s.79 mere conduit).
   - Policy: `rules/mesh_policy.json`.
   - Consent: Plain-language carrier consent text in 6 languages (`carrier_v1`) in `rules/labels.json`.
   - Pitch: 30-second two-phone offline demo integrated into `pitch/demo_script.md`.
5. [x] **Dashboard integration & ownership documented (A4):**
   - Live dashboard mock-up ready in `Member-5/dashboard/index.html`; Member 3 telemetry compatibility verified.
6. [x] **Documentation & test suite:**
   - 27/27 tests pass in 0.16s (`python -m pytest Member-5\tests -q`). All CLI subcommands verified on Windows UTF-8 console. Updated `memory.md`, `goals.md`, `README.md`.

---

## 4. Proposals for each member (with full prompts)

### 4.1 Member 1 (Speech + Claim AI)

**Asks:**
1. Read letters from Member 5's folder instead of placeholders (A1).
2. Ask for damage % when a crop loss has none (C2).
3. Read each drafted letter back in the victim's language (I3).

**Prompt to paste:**

```text
You are working in the Aapke-Liye repo, inside Member-1/ only. Do not edit any other member's folder.

Context: Member 5 owns the legal letter templates in Member-5/templates/*.txt (9 files:
rti_application, grievance, followup_letter, aadhaar_reissue, ration_card_reissue,
land_record_reissue, insurance_crop, insurance_home, insurance_vehicle; all *.en.txt).
Member-1/app/templates/*.txt still contain placeholder text starting with
"### PLACEHOLDER TEMPLATE". The placeholders ({{name}}, {{claim_id}}, {{state}}, ...) in
Member 5's files already match what Member-1/app/documents.py fills in; Member 1's tests
pass 42/42 when Member 5's files are swapped in.

Do the following:

1. Template source. In Member-1/app/documents.py, TEMPLATE_DIR is hard-coded to
   Path(__file__).parent / "templates". Make it configurable:
   - Add a setting TEMPLATES_DIR (env var, documented in .env.example).
   - Default: use ../Member-5/templates relative to the repo root if that folder exists,
     otherwise fall back to Member-1/app/templates (so Docker builds without Member-5 still work).
   - Copy Member 5's 9 templates into Member-1/app/templates/ as the fallback copy,
     replacing the placeholders.
   - Add a test that, when Member-5/templates exists, fails if any fallback file differs
     from Member 5's version (so the copy can't silently drift). Skip the test if
     Member-5 is absent.

2. Missing crop damage. When the extracted claim has a loss with category "crop" and no
   damage_percent, treat it as a missing field and ask a follow-up question in the
   user's language, e.g. "Roughly how much of this crop was destroyed: less than a third,
   about half, or almost all?" Map answers to 25 / 50 / 100. Use the existing gap/question
   flow in app/gaps.py and app/questions.py. Add tests.

3. Letter read-back. Add an option to the drafting response (or a small new endpoint) that
   returns a short plain-language summary of a drafted letter in the claimant's language,
   and its TTS audio via the existing app/tts.py, so the victim can hear what they are
   signing. Keep the letter itself in English. Add a test using mock mode.

Run all Member-1 tests at the end and report results. Update Member-1/README.md for any new
setting or endpoint.
```

---

### 4.2 Member 2 (Backend)

**Asks:**
1. Read rules from Member 5's folder (A1).
2. Apply the crop cap per household and don't pay a crop line with unknown damage % (C1, C2).
3. Return Member 5's "may also qualify" list with each claim (A3, I1).
4. Update the one test that checks old proof wording.

**Prompt to paste:**

```text
You are working in the Aapke-Liye repo, inside Member-2/ only. Do not edit any other member's folder.

Context: Member 5 owns the rules files in Member-5/rules/: sdrf_rules.json,
proof_substitution.json, labels.json (plus schemes/ and states/). Member-2/backend/rules/
holds an older copy (version "sample-2022-26"; proof list has 5 documents, Member 5's has 8:
adds voter_id, death_certificate, disability_certificate). Member 5's sdrf_rules.json passes
validate_rules() in app/services/relief.py, and Member 2's tests pass 91/92 with Member 5's
files. The one failure is tests/test_pdf.py line 43, which expects the old phrase
"Attestation by the Gram Panchayat"; Member 5's wording is "Attestation certificate issued
by Gram Panchayat Pradhan, Ward Councillor, or Village Administrative Officer (VAO)".

Do the following:

1. Rules source. In app/config.py, RULES_DIR is hard-coded to BASE_DIR / "rules".
   - Make it an env setting RULES_DIR (documented in .env.example).
   - Default: ../../Member-5/rules relative to backend/ if it exists, else backend/rules.
   - In docker-compose.yml, mount ../../Member-5/rules read-only and set RULES_DIR to it.
   - Copy Member 5's three JSON files into backend/rules/ as the fallback copy.
   - Add a test that fails if the fallback copy differs from Member-5/rules (skip if
     Member-5 is absent).
   - Update tests/test_pdf.py line 43 to Member 5's wording.

2. Calculation fixes in app/services/relief.py calculate_relief():
   a. The crop max_quantity (2 ha) is a per-household cap across ALL crop lines, not per
      line. Today two lines of 2 ha each pay 4 ha. Track hectares already used across
      crop lines; cap the remaining. Add a note on the line that gets reduced.
   b. If a category has min_damage_percent (crop: 33) and the loss has no damage_percent,
      do not pay it: put it in "unmatched" with reason "Damage percent needed" so the app
      asks for it. Today it is paid in full.
   c. Make the cap logic generic: if a category has "max_quantity_per_household", apply it
      across lines of that category (Member 5 may add this for livestock).
   Add a test for each case.

3. Other schemes. Member 5 has Member-5/engine/multi_scheme.py (pure Python, no
   dependencies) that evaluates SDRF + PMAY-G + PMFBY. When the Member 5 folder is
   available (env MEMBER5_DIR, default ../../Member-5), import MultiSchemeAggregator and add
   "may_also_qualify" to the claim response: each scheme other than SDRF with its name,
   estimated amount and eligibility conditions. Keep SDRF "relief" exactly as today.
   Never add the two into one total. If Member 5 is not available, return an empty list.
   Show "may also qualify" on the PDF as a separate section headed "You may also qualify
   for (subject to eligibility)".

Run all Member-2 tests at the end and report results. Update backend/README.md.
```

---

### 4.3 Member 3 (Verification, Offline, Dashboard data)

**Asks:**
1. Agree dashboard ownership (A4).
2. Later: mesh relay de-duplication and signed receipts on `/sync`, following Member 5's spec.

**Prompt to paste:**

```text
You are working in the Aapke-Liye repo, inside Member-3/ only, plus Member-5/dashboard/
if the team has agreed you may edit it. Do not edit other folders.

Context: Member 5 is writing a network-mesh spec (Member-5/docs/network_mesh_spec.md) and a
policy file (Member-5/rules/mesh_policy.json). Phones relay sealed claim envelopes over
Bluetooth / Wi-Fi Direct until one has signal, then upload to Member 3's POST /sync
(Member-3/app/sync.py). Wait until those two Member 5 files exist, read them, and follow
them. Where they disagree with this prompt, the files win.

Do the following:

1. Envelope intake on POST /sync. Accept relayed envelopes as well as direct uploads:
   - Envelope = claim encrypted with a one-time AES-256-GCM key; that key is wrapped
     with the server's public key (Member 2 provides the key pair); plus the sender
     device's signature and public key; plus a coarse priority flag ("urgent"/"normal").
   - Verify the sender signature; reject unsigned or bad envelopes.
   - Rate-limit per sender device (limit from mesh_policy.json).
   - De-duplicate by claim_id: a second copy returns the same result, never a new claim.

2. Receipts. For every accepted claim return a receipt: server signature (Ed25519) over
   claim_id + timestamp, about 100 bytes. Add GET /sync/receipts?ids=... so a carrier
   phone can fetch receipts for claims it delivered and carry them back into the mesh.
   The receipt means "reached the relief office", not "approved" or "paid".

3. Expiry. Drop envelopes older than the TTL in mesh_policy.json (7 days).

4. Tests for: valid envelope, bad signature, duplicate, rate limit, expired envelope,
   receipt signature verifies with the server public key.

Run all Member-3 tests and report results. Update Member-3/README.md.
```

---

### 4.4 Member 4 (Frontend + Tracking)

**Asks:**
1. Build the 5 core screens first.
2. Use Member 5's consent text and proof alternatives.
3. Show "Relief owed" and "May also qualify" separately (I1).
4. Add a "Listen to this letter" button (I3).
5. Mesh app only after the core screens.

**Prompt to paste:**

```text
You are working in the Aapke-Liye repo, inside Member-4/ only. Do not edit other folders.

Build the 5 screens from Member-4/README.md with plain HTML/CSS/JS (or React from a CDN),
mobile-first, large touch targets, works on a ₹6,000 Android phone:

1. Language picker: 6 buttons (en, hi, bn, te, mr, ta). After a language is chosen, show
   the DPDP consent notice from Member-5/rules/labels.json ("consent" section; use the key
   for the chosen language, fall back to English). The user must tap "I agree" before
   anything is recorded. Store the consent version and time with the claim.
2. Speak & snap: one big record button and a camera button. Send audio to Member 1's
   claim API and photos to Member 2 (see their READMEs for endpoints). Show Member 1's
   follow-up questions as text and play their audio.
3. Review: show the extracted fields with "Correct ✓ / Edit". If documents were lost,
   show the proof alternatives Member 2 returns (proof_suggestions). Show money in two
   separate blocks, never one total:
     - "Relief owed (SDRF estimate)": Member 2's relief.total and its lines.
     - "You may also qualify for": Member 2's may_also_qualify list, each with its
       conditions, labelled "subject to eligibility". Hide the block if the list is empty.
4. Your claim: PDF download, claim ID, and a "Listen to this letter" button for each
   drafted letter (Member 1's read-back audio).
5. Track my claim: status timeline Submitted → Verified → Approved → Paid, from
   GET /status/{claim_id}. Implement the claims_status table and GET/PUT /status/{claim_id}
   as described in Member-4/README.md.

Start with fake JSON shaped like the real responses, then switch to the real APIs.
The network mesh (Android, Google Nearby Connections) is Phase 2: do not start it until
these 5 screens work end to end.

Report what works, what is still on fake data, and how to run it.
```

---

### 4.5 Member 5 (Completed)

**Status:** ✅ **100% Implemented & Verified (27/27 tests pass; all CLI commands operational).**

Member 5 has completed all tasks in its prompt:
1. **Calculation fixes:**
   - 2 ha crop cap across household lines enforced in `engine/entitlement.py` (C1).
   - Missing damage percentage routed to `unmatched` with reason `"Damage percent needed"` (C2).
   - PMFBY 0% damage yields ₹0 (C3).
   - PMFBY 0.80 indemnity level applied; sum insured benchmark disclaimer added (C5).
   - PMAY-G amounts dynamically loaded from `rules/schemes/pmay_g_disaster.json` (C6).
   - Livestock per-household caps enforced in `rules/sdrf_rules.json` and engine (C4).
2. **Two-block architecture (I1):**
   - Output strictly separated into `relief_owed` (SDRF statutory entitlement) and `may_also_qualify` (conditional reconstruction/insurance grants) across `multi_scheme.py`, `cli.py`, and `pitch/demo_script.md`.
3. **Statutory citations (I2):**
   - Added `source` fields to every category in `sdrf_rules.json`, `pmfby.json`, `pmay_g_disaster.json`, and all 5 state rule files (WB, OD, AS, MH, TN).
   - Updated README to reflect "Based on MHA SDRF norms 2022-26 (estimate until verified)".
4. **Network Mesh Store-and-Forward:**
   - Authored specification: `Member-5/docs/network_mesh_spec.md`.
   - Created policy configuration: `Member-5/rules/mesh_policy.json`.
   - Added carrier consent notice across 6 languages in `Member-5/rules/labels.json`.
   - Integrated 30-second two-phone offline relay demo into `Member-5/pitch/demo_script.md`.
5. **Testing & CLI validation:**
   - 27 unit and integration tests passing in `Member-5/tests/`.
   - All `Member-5/cli.py` subcommands (`status`, `calculate`, `multi-scheme`, `proofs`, `rti`) verified on Windows console.

---

## 5. Order for the team

| When | Who | What | Status |
|---|---|---|---|
| **Immediate** | **Member 5** | Calculation fixes, owed vs may-qualify, sources, mesh spec, carrier consent, demo script | ✅ **DONE** (27/27 tests pass) |
| **Immediate** | **Member 2** | Read Member 5's rules, crop cap fixes, adopt `labels.json` and `sdrf_rules.json` | ⏳ Ready to run (paste Prompt 4.2) |
| **Immediate** | **Member 1** | Read Member 5's templates, adopt 9 letters from `Member-5/templates/`, ask for crop damage % | ⏳ Ready to run (paste Prompt 4.1) |
| **Immediate** | **Member 4** | Build 5 core screens, integrate Member 5's DPDP consent and proof alternatives | ⏳ Ready to run (paste Prompt 4.4) |
| **Next** | **Member 2 + Member 4** | "May also qualify" in the API and on screen | ⏳ Dependent on Member 2 & 4 adoption |
| **Next** | **Member 1 + Member 4** | Letter read-back audio via TTS | ⏳ Dependent on Member 1 & 4 |
| **Phase 2** | **Member 3, Member 2, Member 4** | Mesh relay intake, server keys, Android app | 📋 Fully specified in `Member-5/docs/network_mesh_spec.md` |
