# ⚖️ Member 5: Entitlement, Policy & Pitch

<div align="center">

### Ensuring every disaster victim receives every rupee they are statutorily owed, safeguarding citizen privacy under the DPDP Act 2023, and delivering an airtight pitch to evaluators.

**Team OPUS · Institute of Engineering and Management (IEM), Kolkata · Startup Buildathon India 2026**

</div>

---

## 🎯 Role & Domain Ownership

Member 5 leads the **Policy, Legal, Entitlement, and Pitch** architecture for Aapke Liye:
1. **SDRF / NDRF Entitlement Rules:** Financial assistance norm calculations based on MHA SDRF norms 2022-26 (estimate until verified by revenue officials; Letter No. 33-03/2020-NDM-I).
2. **Proof Substitution Framework:** Overcoming the "lost document barrier" via certified administrative and community alternatives under Section 12 of the Disaster Management Act, 2005.
3. **Data Privacy & Statutory Protection:** End-to-end compliance with India's Digital Personal Data Protection Act (DPDP Act) 2023, multi-lingual consent notices, and India sovereign data residency.
4. **Statutory Escalation & RTI Templates:** Legally vetted grievance and RTI applications invoking the **Section 7(1) Life & Liberty 48-Hour emergency proviso**.
5. **Government / SDMA Operations Dashboard:** Functional and visual specifications for State and District Disaster Management Authorities (heatmaps, vulnerability ranking, DBT batch export).
6. **Pitch Deck & Live Demonstration:** 10-slide startup investor deck and turn-by-turn 3-minute competition presentation script.

---

## 🗂️ Member 5 Directory Structure

All files owned and managed by Member 5 are contained strictly within this folder:

```
Member-5/
├── README.md                            # You are here: comprehensive guide & master reference
├── memory.md                            # Living progress tracker: completed milestones & pending tasks
├── goals.md                             # Backlog for future ideas, deferred features & policy models
├── prd.md                               # Product Requirements Document & institutional architecture
│
├── rules/                               # Authoritative entitlement & configuration JSONs
│   ├── sdrf_rules.json                  # MHA SDRF 2022-2026 normative rates (housing, crops, livestock, ex-gratia)
│   ├── proof_substitution.json          # Multi-state statutory proof substitution matrix
│   └── labels.json                      # Multilingual UI labels & consent notices (EN, HI, BN, TE, MR, TA)
│
├── templates/                           # Statutory legal & escalation templates (Jinja2 compatible)
│   ├── rti_application.en.txt           # RTI Act Sec 6(1) + 7(1) Life & Liberty 48-hour emergency format
│   ├── grievance.en.txt                 # Formal DM Act Sec 12 grievance petition to District Magistrate
│   ├── followup_letter.en.txt           # Formal reminder notice citing SDRF Citizens' Charter SLAs
│   ├── aadhaar_reissue.en.txt           # UIDAI disaster loss reprint / biometric verification application
│   ├── ration_card_reissue.en.txt       # Emergency duplicate ration card & immediate food grain relief
│   ├── land_record_reissue.en.txt       # Certified copies of RoR / Khatian / 7-12 extract request
│   ├── insurance_crop.en.txt            # PMFBY 72-hour localized disaster intimation notice
│   ├── insurance_home.en.txt            # Dwelling property disaster insurance claim intimation
│   └── insurance_vehicle.en.txt         # Motor vehicle disaster damage claim intimation
│
├── docs/                                # In-depth legal, policy & technical specifications
│   ├── sdrf_guidelines_reference.md     # Official MHA SDRF/NDRF statutory reference & calculation formulas
│   ├── proof_substitution_framework.md  # Detailed SOP & administrative pathways (WB, OD, AS, MH, TN)
│   ├── dpdp_compliance_privacy_framework.md # DPDP Act 2023 compliance, consent models, data localization
│   └── government_dashboard_spec.md     # SDMA / DDMA operations portal, heatmap & DBT export specs
│
└── pitch/                               # Competition & investor presentation assets
    ├── pitch_deck.md                    # 10-slide startup deck for Startup Buildathon India 2026
    └── demo_script.md                   # 3-minute turn-by-turn live presentation script with judge Q&A
```

---

## 📌 Deliverable Status Summary

### 🧱 Phase 1: Core Demo Deliverables
| Deliverable | Location | Status | Summary |
|---|---|---|---|
| **Living Memory Tracker** | [memory.md](memory.md) | ✅ Active | Tracks active status, completed items, and next steps |
| **Future Goals Backlog** | [goals.md](goals.md) | ✅ Active | Stores future enhancements not being built right now |
| **Product Requirements Document** | [prd.md](prd.md) | ✅ Complete | Complete system blueprint, data flows, and specifications |
| **SDRF Relief Rules** | [rules/sdrf_rules.json](rules/sdrf_rules.json) | ✅ Complete | Based on MHA SDRF norms 2022-26 (estimate until verified) across 5 categories, tested & validated |
| **Proof Substitution Matrix** | [rules/proof_substitution.json](rules/proof_substitution.json) | ✅ Complete | Complete statutory substitutes for 8 lost document types |
| **Multi-Lingual Consent & Labels** | [rules/labels.json](rules/labels.json) | ✅ Complete | Plain-language consent across 6 official Indian languages |
| **Pitch Deck** | [pitch/pitch_deck.md](pitch/pitch_deck.md) | ✅ Complete | 10-slide startup narrative, unit economics, market size |
| **3-Minute Demo Script** | [pitch/demo_script.md](pitch/demo_script.md) | ✅ Complete | Time-coded presentation with device cues and judge Q&A |

### 🚀 Phase 2: Roadmap Deliverables
| Deliverable | Location | Status | Summary |
|---|---|---|---|
| **Statutory Escalation Templates** | [templates/](templates/) | ✅ Ready | Legally reviewed templates for RTI, grievances, and reissues |
| **SDRF Reference Guide** | [docs/sdrf_guidelines_reference.md](docs/sdrf_guidelines_reference.md) | ✅ Documented | Full legal analysis of MHA Order 33-03/2020-NDM-I |
| **Proof Substitution Framework** | [docs/proof_substitution_framework.md](docs/proof_substitution_framework.md) | ✅ Documented | State-by-state administrative SOPs (WB, OD, AS, MH, TN) |
| **DPDP Privacy Framework** | [docs/dpdp_compliance_privacy_framework.md](docs/dpdp_compliance_privacy_framework.md) | ✅ Documented | 6 privacy pillars, encryption, retention, and GRO details |
| **Government Operations Dashboard** | [docs/government_dashboard_spec.md](docs/government_dashboard_spec.md) | ✅ Documented | Damage heatmap, Vulnerability Priority Index, DBT export |
| **Network Mesh (phone-to-phone relay)** | [docs/network_mesh_spec.md](docs/network_mesh_spec.md) | ✅ Complete | End-to-end spec, DPDP carrier consent (6 langs), policy JSON, and 30-sec pitch demo |

---

## 🤝 Inter-Member Collaboration & Contracts

Member 5 maintains explicit contracts with every member of Team OPUS:

- **With Member 1 (AI/ML):**
  - Member 1's automated drafting engine (`POST /v1/documents/draft`) uses Jinja2 template filling.
  - Member 5 provides the authoritative, legally vetted text in `templates/` retaining all `{{placeholder}}` keys (`{{name}}`, `{{phone}}`, `{{claim_id}}`, `{{losses_table}}`, etc.).
- **With Member 2 (Core Backend / CTO):**
  - Member 2's `relief.py` service dynamically loads `sdrf_rules.json`, `proof_substitution.json`, and `labels.json` without hardcoding rupee values in Python.
  - Member 5 maintains the validated schema and ensures test compatibility (`version`, `categories`, `unit`, `items`).
- **With Member 3 (Verification & Vision):**
  - Member 3 supplies damage scores, EXIF coordinates, and duplicate flags.
  - Member 5 documents how this telemetry feeds the Government Dashboard's Vulnerability Priority Index (VPI) and anti-fraud alerts.
- **With Member 4 (Frontend & Tracking):**
  - Member 4's 5-screen user journey uses Member 5's multi-lingual consent notices and proof substitution recommendations on the Review screen.

---

## ⚖️ Indian Statutory Alignment

Aapke Liye is engineered on solid constitutional and statutory footings:
1. **Disaster Management Act, 2005 (Act No. 53 of 2005):**
   - Section 12: Minimum standards of relief (food, shelter, sanitation, ex-gratia).
   - Section 38: State executive measures to ensure non-discrimination in disaster relief.
2. **Digital Personal Data Protection Act, 2023 (Act No. 22 of 2023):**
   - Section 5 & 6: Notice and explicit multi-lingual consent prior to processing.
   - Section 8: Sovereign data localization and robust security safeguards.
   - Section 12: Right of Data Principals to review and correct inaccurate records.
3. **Right to Information Act, 2005 (Act No. 22 of 2005):**
   - Section 6(1): Right to request information from public authorities.
   - **Section 7(1) Proviso:** Mandatory **48-hour** statutory response time when information concerns the life or liberty of a person.

---

## 🛠️ How to Validate Member 5 Rules

To inspect and validate Member 5's rule files independently:
```powershell
# Validate that sdrf_rules.json has valid JSON formatting and correct structure
Get-Content Member-5\rules\sdrf_rules.json | ConvertFrom-Json | Select-Object -ExpandProperty categories

# Verify that proof_substitution.json covers all necessary documents
Get-Content Member-5\rules\proof_substitution.json | ConvertFrom-Json

# Check multi-lingual consent strings
(Get-Content Member-5\rules\labels.json | ConvertFrom-Json).consent
```

---

## 📡 Network mesh (phone-to-phone relay)

**Problem:** after a flood or cyclone, whole villages can lose mobile network for days.
The offline queue (Member 3) only helps when *the same phone* gets signal back.

**Idea:** phones pass the claim along to each other over Bluetooth / Wi-Fi Direct until one
of them reaches signal, which then uploads it.

```
Ramesh's phone (no signal) ──Bluetooth/Wi-Fi Direct──► neighbour's phone ──► … ──► volunteer phone with signal ──► server
```

How it works (store and forward):
1. The claim is saved on the phone and **encrypted with the server's public key**, so phones in between can carry it but never read it.
2. Nearby phones running the app discover each other and copy claims they don't have yet.
3. The first phone with internet uploads everything it is carrying to `POST /sync` (Member 3).
4. The server ignores duplicates (same `claim_id`) and sends a receipt back through the mesh, so the original phone shows "Delivered".

### Your tasks (Member 5)
- [x] **Spec:** one page covering the flow above, what a relay phone stores, how long it keeps a claim (7 days TTL), and the size limit per claim (1.5 MB envelope, 30 MB / 25 claims relay cap) — see [docs/network_mesh_spec.md](docs/network_mesh_spec.md) and [rules/mesh_policy.json](rules/mesh_policy.json)
- [x] **Privacy and legal:** consent wording for "let my phone carry others' sealed claims" across 6 languages in [rules/labels.json](rules/labels.json); IT Act Section 79 mere conduit and DPDP Act 2023 compliance documented in [docs/network_mesh_spec.md](docs/network_mesh_spec.md)
- [x] **Battery and trust rules:** relaying is opt-in, halts below 25% battery floor, duty-cycled BLE scanning, and trusted volunteer carriers documented in [rules/mesh_policy.json](rules/mesh_policy.json)
- [x] **Pitch:** 30-second live two-phone airplane-mode relay demonstration script and evaluator Q&A integrated into [pitch/demo_script.md](pitch/demo_script.md)

### Who builds it
| Member | Part |
|---|---|
| **Member 5** | Spec, privacy, consent text, pitch mock-up (above) |
| **Member 3** | The relay logic and `/sync` de-duplication + receipts |
| **Member 4** | A native Android app (browsers can't form a phone-to-phone mesh); Google Nearby Connections API |
| **Member 2** | Server key pair for encrypting claims; accepts relayed claims |
| **Member 1** | Nothing changes: speech + claim AI run on the server once the claim arrives |

**Phase:** roadmap (Phase 2). For the buildathon, the two-phone demo is enough.
