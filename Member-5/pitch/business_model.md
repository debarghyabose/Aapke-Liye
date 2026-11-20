# 💼 Aapke Liye: Business & Revenue Model (v1.0, final for review)

> **Team OPUS · IEM Kolkata · Startup Buildathon India 2026**
> Purpose: the complete business and revenue model, written so reviewers ("sharks") can attack it.
> Every number is either sourced from the repo, a public norm, or marked **[ASSUMPTION]**. Section 10 lists the weak points we already know about.

---

## 1. One-line summary

**Victims file disaster relief claims free, by voice, in their own language. Governments, insurers and funders pay because they get clean, verified, de-duplicated claims faster and with less fraud.**

Model type: **B2G SaaS (core) + B2B per-claim verification (insurers) + grant/CSR-funded deployments (entry wedge).**
Citizens never pay. That rule is never broken.

---

## 2. The problem, in money terms

| Fact | Figure | Source / status |
|---|---|---|
| Annual SDRF + NDRF fund flow | ₹30,000+ Cr | Pitch deck; verify against latest MHA/FC allocation |
| SDRF split (15th FC, 2021–26) | 40% Response & Relief · 30% Recovery & Reconstruction · 10% Preparedness & Capacity Building · 20% to SDMF | 15th Finance Commission; **16th FC (2026–31) shares to be confirmed** |
| People affected by disasters per year | 30M+ | Pitch deck |
| Relief claims processed on paper today | Majority, district-dependent | **[ASSUMPTION]**, needs field validation |
| Leakage (duplicate, inflated, ineligible claims) | 3–8% of relief disbursed | **[ASSUMPTION]**; CAG audits report irregularities, but this % must be sourced |

**Value hypothesis:** for a state disbursing ₹1,000 Cr of relief a year, cutting leakage by even 2 percentage points saves ₹20 Cr. Our state licence is priced at ₹1.5–3 Cr, so roughly **7–15% of the savings it creates.**

---

## 3. Customer segments: who uses it vs. who pays

| Segment | Uses it | Pays | What they get | Budget line they pay from |
|---|---|---|---|---|
| **Disaster victims** | ✅ | ❌ never | Voice claim, proof substitution, entitlement estimate, tracking, escalation letters | — |
| **SDMAs / Relief Commissioners / District Collectors** | ✅ | ✅ **main payer** | Verified claims, duplicate & fraud flags, village heatmap, Vulnerability Priority Index, PFMS/DBT export, audit trail | SDRF Preparedness & Capacity Building (10%); state IT/e-governance budget |
| **Insurers (PMFBY crop, home, motor)** | ✅ | ✅ | Geo-tagged, timestamped, fraud-checked claim packets; fewer surveyor visits | Claims-handling / loss-assessment cost |
| **NGOs, CSR foundations, multilaterals** (Red Cross, UNDP, corporate CSR) | ✅ | ✅ | Funded rollouts in high-risk districts with measurable impact reports | CSR (Companies Act Sch. VII covers disaster management); program grants |
| **CSC operators (VLEs) / volunteers** | ✅ | ❌ (they earn) | Assisted-filing tools; per-claim commission paid by the state | — |

---

## 4. Revenue streams and pricing

### Stream A: B2G platform licence (core, ~50–60% of revenue by Year 3)

| Tier | Scope | Price / year | Included volume | Overage |
|---|---|---|---|---|
| **District pilot** | 1 district, 6–12 months | ₹15 L | 25,000 claims | ₹20 / claim |
| **District licence** | 1 district, full year | ₹20–25 L | 50,000 claims | ₹20 / claim |
| **State licence** | All districts in a state | ₹1.5–3 Cr (by district count and disaster exposure) | 5,00,000 claims | ₹15 / claim |
| **One-time implementation** | State portal integration, PFMS export, state top-up rules (`rules/states/*.json`), training | ₹30–60 L per state | — | — |

**Why base fee + overage:** disasters are seasonal and spiky. The base fee gives us predictable revenue; the overage only kicks in during big events, when the state's relief budget is also unlocked.

**Procurement route:** GeM listing, DPIIT startup relaxation (no prior turnover or experience criteria), and state innovation-procurement or nomination routes for pilots under ₹25 L. **[ASSUMPTION]**: some states will need a full tender for a state licence, which is a 6–12 month cycle.

### Stream B: Insurer verification fee (B2B, ~30–35% by Year 3)

| Product | Price per verified claim packet | What's in the packet |
|---|---|---|
| PMFBY localized calamity / post-harvest loss | ₹150–250 | GPS + timestamp check, satellite flood overlay, crop-damage score, duplicate check, farmer statement |
| Home / property catastrophe claim | ₹300–500 | Photo damage score, before/after (if baseline exists), location match, duplicate check |
| Motor (flood-damaged vehicle) | ₹250–400 | Location-in-flood-zone check, photo duplicate check |

**Benchmark:** a physical surveyor visit in a catastrophe event costs insurers far more than ₹250 **[ASSUMPTION: get real surveyor fee data from 1–2 insurers]**. We don't replace surveyors; we triage, so they only visit the flagged 20–30%.

**Note:** most PMFBY payouts are area-based (crop-cutting experiments / YES-TECH), not individual. Our insurer market is the **individual-assessment slice only** (localized calamity, post-harvest, non-crop lines). That slice is smaller than the headline PMFBY number.

### Stream C: CSR / multilateral sponsored deployments (entry wedge, ~15% by Year 3)

| Package | Price | Includes |
|---|---|---|
| **Sponsored district deployment** | ₹25–40 L per district-year | Platform, pre-monsoon household pre-registration drive, baseline-photo vault campaign, volunteer training, impact report |

This is how we get **in before the government signs**: a funder pays for 1–2 districts, and we produce the evidence (turnaround time, fraud catch rate, claims filed by people without documents) that gets the state to buy.

### Stream D: Later options (not in projections)

| Option | Status | Risk |
|---|---|---|
| Aggregated, anonymized damage intelligence for reinsurers and parametric products | Year 3+ | DPDP Act limits, so aggregated data only, never individual data |
| Licensing to other countries (Bangladesh, Philippines, Indonesia) | Year 3+ | Needs local rules engines and languages |
| Parametric micro-advance gateway (₹5–10k within 24 h) | Research | Needs a state or insurer partner willing to fund it |

**We will never:** charge victims, take a % of relief money, sell individual data, or show ads.

---

## 5. Unit economics (per claim)

| Cost item | Per claim | Basis |
|---|---|---|
| Speech-to-text (Whisper, self-hosted GPU) | ₹0.5–1.0 | ~2–3 min audio per claim **[ASSUMPTION]** |
| Claim AI extraction (Gemini, 2–4 turns) | ₹0.5–2.0 | Token-based **[ASSUMPTION]** |
| Damage vision + duplicate check | ₹0.5–1.5 | 3–5 photos |
| Encrypted storage (India region, 1 yr) | ₹0.5 | ~10 MB per claim |
| Status updates (WhatsApp utility messages / SMS, ~5 per claim) | ₹3–5 | Utility message pricing in India |
| IVR (feature-phone users only, ~30% of claims) | ₹2–4 average | ₹1–2 per minute |
| **Total variable cost** | **₹8–14 per claim** | |

| Revenue per claim | Value |
|---|---|
| State licence at ₹2 Cr ÷ 5 L claims | ₹40 |
| Overage | ₹15–20 |
| Insurer packet | ₹150–500 |

**Gross margin target:** 65–75% after field-support staff (the real cost is people on the ground during an event, not compute).

---

## 6. Three-year projection

Fiscal years start April. Year 1 = FY 2027–28.

### Revenue

| Line | Year 1 | Year 2 | Year 3 |
|---|---|---|---|
| CSR / grant sponsored districts | 2 × ₹30 L = **₹0.60 Cr** | 4 × ₹30 L = **₹1.20 Cr** | 6 × ₹30 L = **₹1.80 Cr** |
| Paid district pilots / licences | 1 × ₹15 L = **₹0.15 Cr** | 4 × ₹20 L = **₹0.80 Cr** | 4 × ₹20 L = **₹0.80 Cr** |
| State licences | 0 | 1 × ₹1.5 Cr = **₹1.50 Cr** | 3 × ₹2 Cr = **₹6.00 Cr** |
| Implementation fees | 0 | 1 × ₹40 L = **₹0.40 Cr** | 2 × ₹40 L = **₹0.80 Cr** |
| Overage (event surge) | 0 | 2 L × ₹20 = **₹0.40 Cr** | 8 L × ₹20 = **₹1.60 Cr** |
| Insurer packets | 20k × ₹200 = **₹0.40 Cr** | 75k × ₹200 = **₹1.50 Cr** | 3 L × ₹200 = **₹6.00 Cr** |
| **Total revenue** | **₹1.15 Cr** | **₹5.80 Cr** | **₹17.00 Cr** |

### Costs

| Line | Year 1 | Year 2 | Year 3 |
|---|---|---|---|
| Team (8 → 18 → 35 people) | ₹0.80 Cr | ₹2.20 Cr | ₹4.50 Cr |
| Infra + AI + messaging | ₹0.15 Cr | ₹0.50 Cr | ₹1.50 Cr |
| Field ops (training, pre-registration drives, event surge staff) | ₹0.30 Cr | ₹1.00 Cr | ₹2.50 Cr |
| Sales, tenders, legal, compliance (DPDP audits, CERT-In, STQC) | ₹0.10 Cr | ₹0.60 Cr | ₹1.50 Cr |
| **Total cost** | **₹1.35 Cr** | **₹4.30 Cr** | **₹10.00 Cr** |
| **EBITDA** | **–₹0.20 Cr** | **+₹1.50 Cr** | **+₹7.00 Cr** |

**Cash is not EBITDA.** Government payments typically arrive 6–12 months after invoicing **[ASSUMPTION, common in B2G]**. Year 2 is cash-negative even if EBITDA-positive. Working capital need: about ₹2–3 Cr in Year 2.

### Volume behind the numbers

| | Year 1 | Year 2 | Year 3 |
|---|---|---|---|
| Districts live | 3 | ~38 (1 state of ~30 districts + 8) | ~100 (3 states + 10) |
| Claims processed | 50,000 | 9,00,000 (state 7 L incl. 2 L overage; districts 2 L) | 26,00,000 (states 23 L incl. 8 L overage; districts 3 L) |

The pitch deck's 24-month SOM (2.5M claims in Odisha, West Bengal, Assam) matches the end of Year 3 here, not Year 2. **We've corrected that timeline.**

---

## 7. Go-to-market

| Step | When | Goal | Proof we need to move on |
|---|---|---|---|
| 1. Funded pilot | Months 0–12 | 2 coastal districts (WB + Odisha), sponsored by CSR / grant | 10,000+ claims filed; median filing-to-verification time < 7 days; fraud/duplicate catch rate measured against manual review |
| 2. First paid district | Months 6–12 | 1 DDMA pays ₹15 L directly | Signed work order |
| 3. First insurer | Months 6–12 | 1 PMFBY or general insurer pays per packet | 20,000 packets; surveyor visits cut by ≥ 50% |
| 4. First state | Months 12–24 | State licence via GeM / tender | Pilot evidence + DM / Relief Commissioner sponsor |
| 5. Replicate | Months 24–36 | 3 states, same rules engine with state plug-ins | `rules/states/*.json` already built for Assam, Maharashtra, Odisha, Tamil Nadu, West Bengal |

**Distribution partners:** CSC SPV (300k+ village entrepreneurs as assisted-filing points), Bhashini (language stack), state IT departments, district NGOs for pre-registration.

---

## 8. Competition and why we win

| Alternative | What it does | Our edge |
|---|---|---|
| Paper forms at camps / taluk offices | Status quo | Voice, any language, works without documents, trackable |
| State relief portals (built by NIC or state IT) | Online form entry, usually by officials | Victim-side voice filing, proof substitution, AI verification, offline-first |
| PMFBY / Crop Insurance app | Localized loss intimation for farmers | Multi-scheme (SDRF + PMFBY + PMAY-G), lost-document path, fraud signals |
| Haqdarshak-style scheme-access platforms | Agent-assisted welfare enrolment | Disaster-specific: damage verification, SDRF rules, event-surge operations |
| Generic GovTech vendors (large SIs) | Build custom portals on tender | Ready product, cheaper, faster, domain rules already encoded |

**Defensibility (honest version):** the code can be copied. What's hard to copy is (1) encoded state-by-state relief rules and proof-substitution norms, (2) pre-registered households and baseline photos collected before disasters, (3) trust and track record with one SDMA, and (4) labelled damage and fraud data from real events.

---

## 9. The ask

**₹50 L seed / grant** for 12 months:

| Use | Amount |
|---|---|
| Field pilot in 2 districts (staff, training, pre-registration drive) | ₹20 L |
| Engineering (production hardening, security audit, WhatsApp + IVR channels) | ₹18 L |
| Cloud, AI, messaging (India region) | ₹5 L |
| Compliance & legal (DPDP, CERT-In empanelled audit) | ₹4 L |
| Buffer | ₹3 L |

**12-month milestones:** 1 SDMA/DDMA partnership · 50,000 claims · median turnaround < 7 days · first insurer paying per packet.

---

## 10. Known weak points (please attack these)

1. **Government sales cycle.** A state licence can take 12–24 months, and an election or a new Relief Commissioner can reset it. Our Year 2 state deal is the single biggest assumption in the model.
2. **Government pays late.** 6–12 month receivables could kill us even with signed contracts.
3. **NIC or the state builds it themselves.** If our pilot proves the idea, the state may ask NIC to copy it for free.
4. **Two masters.** We help victims claim everything they're owed *and* sell fraud detection to the government that pays out. Plus our RTI/grievance escalation targets the officials who buy the product. Is that a contradiction or a feature?
5. **Insurer market may be smaller than it looks.** Most PMFBY payouts are area-based, so individual verification is a slice. ₹6 Cr of Year 3 insurer revenue rests on 3 L packets.
6. **Seasonality.** Revenue and workload spike in monsoon and cyclone season; field staff sit idle the rest of the year.
7. **Leakage figure is unsourced.** The ROI argument (Section 2) depends on 3–8% leakage. We need a CAG report or state audit number.
8. **AI errors have real victims.** A wrong extraction or a false fraud flag could deny someone relief. Who carries the liability, and does a human always review a rejection?
9. **Sensitive data at scale.** Aadhaar-linked identity, bank, land and location data for millions of vulnerable people. One breach ends the company.
10. **CSR dependence early.** Year 1 is 52% grant/CSR money. If that doesn't come, Year 1 revenue is ~₹0.55 Cr.
11. **Pricing benchmarks are guesses.** ₹1.5–3 Cr per state, ₹20 per overage claim and ₹200 per insurer packet have not been tested with a real buyer.
12. **Team.** Five students building a B2G company that needs government relations, field ops and compliance staff.

---

## 11. What would kill the plan (stop/pivot signals)

| Signal | By when | Pivot |
|---|---|---|
| No district will run even a sponsored pilot | Month 6 | Go NGO-only (sell to Red Cross / large NGOs as a field tool) |
| Pilot shows no measurable turnaround or fraud improvement | Month 12 | Narrow to the insurer verification product |
| No state licence after 2 strong pilots | Month 24 | Sell as a module to the large system integrators that win state tenders |
| Insurers won't pay ≥ ₹100 per packet | Month 12 | Drop Stream B; focus on B2G |
