# Member 5 Report: Entitlement, Policy & Pitch

**Status:** Complete. All 20 tests pass, every CLI command runs, and Member 1's and Member 2's test suites pass when given Member 5's files (one Member 2 test checks old proof wording; see section 6).
**Date:** 2026-11-20

---

## 1. What Member 5 does

Member 5 is the **rules and policy layer** of Aapke Liye. It answers three questions for every disaster victim:

1. **How much money are they owed?** (SDRF relief, plus PMAY-G housing and PMFBY crop insurance)
2. **What can they show instead of documents that were destroyed?** (proof substitutes, by state)
3. **What can they file if the claim is stuck?** (RTI, grievance, reminder and document reissue templates)

It also holds the privacy consent text (DPDP Act 2023), the government dashboard mock-up, and the pitch material.

Member 5 does **not** run a server. It provides **data files** (JSON rules and text templates) that Member 1 and Member 2 read, plus a Python engine and a CLI that show and test those rules.

---

## 2. What's inside

```
Member-5/
├── rules/                  Data the other members read
│   ├── sdrf_rules.json         Relief rates: house, crop, livestock, household, ex-gratia
│   ├── proof_substitution.json Substitutes for 8 lost document types
│   ├── labels.json             Display names + consent text in 6 languages
│   ├── schemes/                pmfby.json, pmay_g_disaster.json
│   └── states/                 west_bengal, odisha, assam, maharashtra, tamil_nadu
├── templates/              9 letters with {{placeholders}} (for Member 1's drafting)
├── engine/                 Python logic
│   ├── entitlement.py          SDRF calculator
│   ├── multi_scheme.py         SDRF + PMAY-G + PMFBY combined
│   ├── proofs.py               Lost-document → substitutes (with state overrides)
│   ├── dpdp.py                 Consent text and labels by language
│   ├── templates_validator.py  Finds placeholders, renders test letters
│   └── connector.py            Checks if Members 1–4 use Member 5's files
├── cli.py                  Command-line tool for all of the above
├── dashboard/index.html    SDMA dashboard mock-up (open in a browser)
├── tests/                  20 tests
├── docs/                   4 policy references (SDRF, proofs, DPDP, dashboard spec)
├── pitch/                  10-slide deck + 3-minute demo script
└── prd.md, memory.md, goals.md, README.md
```

---

## 3. How each part works

### 3.1 SDRF relief calculator (`engine/entitlement.py` + `rules/sdrf_rules.json`)

Input is a list of losses, for example:
```json
[{"category": "house", "item": "fully_damaged_plain", "quantity": 1},
 {"category": "crop", "item": "rainfed", "quantity": 1.2, "damage_percent": 100}]
```

For each loss it:
1. Looks up the rate for `category.item` in `sdrf_rules.json`.
2. Multiplies by quantity.
3. Applies the category's limits:
   - **Crop:** no payment if damage is below **33%**; area capped at **2 hectares**; minimum payment ₹1,000 / ₹2,000 / ₹2,500 (rainfed / irrigated / perennial).
   - **Poultry:** capped at ₹10,000.
4. Puts anything it can't match into `unmatched`, with a reason, so nothing is silently dropped.

Rates in the file:

| Category | Unit | Items (₹) |
|---|---|---|
| House | per house | fully damaged plains 1,20,000 · hilly 1,30,000 · partly pucca 6,500 · partly kutcha 4,000 · hut 8,000 · cattle shed 3,000 |
| Crop | per hectare | rainfed 8,500 · irrigated 17,000 · perennial 22,500 |
| Livestock | per animal | milch large 37,500 · milch small 4,000 · draught large 32,000 · draught small 20,000 · poultry 100 |
| Household | per family | clothing 2,500 · utensils 2,500 |
| Ex-gratia | per person | death 4,00,000 · disability 40–60% 74,000 · above 60% 2,50,000 |

The file's version is `sample-mha-sdrf-2022-26-v1.1`. Member 2's backend treats any version starting with "sample" as an **estimate** and marks the amounts that way on the claim.

Example (`python cli.py calculate`): a fully damaged house, 1.2 ha of rainfed crop, 2 small milch animals, clothing and utensils come to **₹1,43,200**.

### 3.2 Multi-scheme package (`engine/multi_scheme.py`)

It takes the whole claim and checks three schemes:

- **SDRF:** always, using the calculator above.
- **PMAY-G housing:** if any house is *fully damaged*. ₹1,56,750 in plains, ₹1,66,750 in hilly areas (house grant + 90 days of MGNREGA wages + toilet grant).
- **PMFBY crop insurance:** only if the claim says the farmer is insured. Pays area × sum insured per hectare × damage %.

It returns every scheme that applies and a grand total. In the CLI example the total is **₹3,79,750**.

### 3.3 Proof substitution (`engine/proofs.py`)

Input: the lost documents (e.g. `aadhaar, land_record`) and, optionally, the state.

1. It takes the national substitutes from `proof_substitution.json`. Documents not in the file get the `_default` list.
2. If the state has a file in `rules/states/`, those state-specific substitutes go first.
3. For land records it also adds the state's land authority and online portal.

Covered documents: Aadhaar, ration card, land record, bank passbook, house ownership, voter ID, death certificate, disability certificate.
Covered states: West Bengal, Odisha, Assam, Maharashtra, Tamil Nadu (short names like `WB` or `OD` also work).

### 3.4 Consent and labels (`engine/dpdp.py` + `rules/labels.json`)

- Gives the DPDP consent notice in the user's language (English, Hindi, Bengali, Telugu, Marathi, Tamil). Falls back to English.
- Turns codes into readable names, e.g. `house.fully_damaged_plain` → "House – fully damaged (plains)". Member 2's PDF uses these names.

### 3.5 Legal templates (`templates/` + `engine/templates_validator.py`)

There are 9 letters: RTI application (with the 48-hour life-and-liberty clause), grievance to the District Magistrate, follow-up reminder, Aadhaar / ration card / land record reissue, and crop / home / vehicle insurance notices.
They use `{{name}}`, `{{claim_id}}`, `{{state}}` and similar placeholders. Member 1's drafting service fills them in. The validator lists each template's placeholders and renders test copies.

### 3.6 Connection check (`engine/connector.py`)

It compares Member 5's files with the copies inside the other members' folders:
- **Member 1:** are all 9 templates identical to Member 5's?
- **Member 2:** do the rules version and the proof file match?
- **Member 3:** are the vision and duplicate-detection modules present?
- **Member 4:** have the screens been built?

It reports **In sync**, **Out of sync** or **Pending** for each one, so the status shows what is actually in use.

### 3.7 CLI (`cli.py`)

```powershell
python Member-5\cli.py status
python Member-5\cli.py calculate
python Member-5\cli.py multi-scheme
python Member-5\cli.py proofs --docs aadhaar,land_record --state "West Bengal"
python Member-5\cli.py rti --name "Ramesh Mondal" --claim-id "CLM-8921"
```
It works in a normal Windows console (it switches the output to UTF-8 itself).

### 3.8 Dashboard (`dashboard/index.html`)

This is a single-page mock-up for the state or district disaster office. It shows a village damage heatmap, a priority list of the most vulnerable households, a fraud alert built from Member 3's duplicate and EXIF checks, and a PFMS bank-transfer batch export. Open the file in a browser; no server is needed.

### 3.9 Docs and pitch

- `docs/`: SDRF reference, state-by-state proof procedures, DPDP privacy framework, dashboard spec.
- `pitch/`: 10-slide deck and a timed 3-minute demo script with judge Q&A.
- `prd.md`: whole-product requirements. `goals.md`: ideas for later.

---

## 4. How it connects to the other members

```
Member 5 rules/*.json  ──►  Member 2 backend (relief.py reads sdrf_rules, proof_substitution, labels)
                               └─► relief amount, proof suggestions, labels on the claim PDF
Member 5 templates/*.txt ──►  Member 1 drafting (documents.py fills {{placeholders}})
Member 3 vision/duplicates ─►  Member 5 dashboard (priority list, fraud alert)
Member 5 labels.json consent ─► Member 4 screens (consent, proof alternatives on Review)
```

Members 1 and 2 load these files from their own folders (`Member-1/app/templates/`, `Member-2/backend/rules/`). To switch them to Member 5's versions, they copy the files in or point those paths at `Member-5/`. No code change is needed on either side.

---

## 5. Test results (2026-11-20)

| Check | Result |
|---|---|
| Member 5 tests (`python -m pytest` in `Member-5/`) | **20 / 20 pass** |
| All 5 CLI commands | Run without errors |
| Member 1 tests, using Member 5's templates (temporary copy) | **42 / 42 pass** |
| Member 2 tests, using Member 5's rules (temporary copy) | **91 / 92 pass** (see section 6) |
| Member 5 `sdrf_rules.json` against Member 2's own validator | Passes |

---

## 6. Note for Member 2 when switching to Member 5's files

Member 2's `tests/test_pdf.py` checks for the text "Attestation by the Gram Panchayat". Member 5's proof file says "Attestation certificate issued by Gram Panchayat Pradhan, Ward Councillor, or Village Administrative Officer (VAO)". When Member 2 adopts the file, they should update that one expected string in the test. Nothing else changes.
