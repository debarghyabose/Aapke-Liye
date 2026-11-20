# 📖 SDRF & NDRF Assistance Norms Reference Guide
## Ministry of Home Affairs (MHA) Guidelines & Statutory Foundations

> **Compiled & Maintained By:** Member 5 (Entitlement, Policy & Pitch)  
> **Statutory Authority:** Government of India, Ministry of Home Affairs (Disaster Management Division)  
> **Primary Citation:** MHA Order No. 33-03/2020-NDM-I dated 10th October 2022  
> **Constitutional & Legal Basis:** Disaster Management Act, 2005 (Sections 12, 46, and 48)  
> **Current Cycle:** 15th Finance Commission Award Period (2021-22 to 2025-26 / 2026-31 transitional)

---

## 1. Statutory Context & Principles

Under Section 12 of the **Disaster Management Act, 2005**, the National Disaster Management Authority (NDMA) and State Disaster Management Authorities (SDMAs) have an affirmative legal mandate to recommend and enforce **minimum standards of relief** to be provided to persons affected by disaster.

### Key Principles of Relief:
1. **Relief is Assistance, Not Compensation:** Under Indian administrative law, SDRF/NDRF grants are ex-gratia relief to assist in immediate recovery and restoration, not civil compensation for total tortious loss.
2. **First Charge on State Funds:** SDRF is the primary fund available to State Governments for responding to notified disasters (cyclone, drought, earthquake, fire, flood, tsunami, hailstorm, landslide, avalanche, cloudburst, pest attack, frost/cold wave).
3. **Transparent Scale & Direct Benefit Transfer (DBT):** All financial assistance must be calculated according to published norms and transferred directly to Aadhaar-seeded bank accounts without cash intermediaries.

---

## 2. Comprehensive SDRF Rate Schedule & Calculation Rules

### 2.1 Housing Assistance
Assistance is admissible for damage caused to residential houses:

| Item Code | Description | Normative Rate | Mandatory Conditions & Thresholds |
|---|---|---|---|
| `house.fully_damaged_plain` | Fully Destroyed / Severely Damaged Pucca/Kutcha House in Plains | **₹1,20,000** | Damage > 50% or structure rendered structurally unsafe and uninhabitable. |
| `house.fully_damaged_hilly` | Fully Destroyed / Severely Damaged in Hilly / Difficult / Inaccessible Areas | **₹1,30,000** | Applied in notified hill districts (e.g. Himalayas, Western Ghats, island territories). |
| `house.partially_damaged_pucca` | Partially Damaged Pucca House | **₹6,500** | Minimum damage of 15% required. Pucca = permanent walls & roof. |
| `house.partially_damaged_kutcha` | Partially Damaged Kutcha House | **₹4,000** | Minimum damage of 15% required. Kutcha = mud, unbaked bricks, thatch, bamboo. |
| `house.hut_damaged` | Hut Fully Destroyed or Damaged | **₹8,000** | Temporary dwelling/shanty of thatch/tarpaulin/reeds. |
| `house.cattle_shed` | Cattle Shed Attached to House | **₹3,000** | Free-standing or attached shed for domestic cattle/livestock. |

### 2.2 Agricultural Crop Loss (Input Subsidy)
Admissible where damage to crops/horticulture is **33% or higher**:

| Item Code | Category | Rate per Hectare | Floor (Minimum) | Ceiling (Maximum) |
|---|---|---|---|---|
| `crop.rainfed` | Rainfed Agriculture / Single Crop | **₹8,500 / ha** | ₹1,000 | Capped at 2 hectares per farmer |
| `crop.irrigated` | Assured Irrigation Agriculture | **₹17,000 / ha** | ₹2,000 | Capped at 2 hectares per farmer |
| `crop.perennial` | Perennial Horticulture Crops | **₹22,500 / ha** | ₹2,500 | Capped at 2 hectares per farmer |

> **Calculation Formula in Aapke Liye Engine:**  
> `Eligible_Amount = min(area_hectares, 2.0) * rate`  
> *Subject to:* `damage_percent >= 33%` and `amount >= min_amount`

### 2.3 Animal Husbandry & Livestock
Assistance for loss of domestic animals essential to livelihood:

| Item Code | Livestock Type | Rate per Animal | Household Upper Cap |
|---|---|---|---|
| `livestock.milch_large` | Large Milch Animal (Cow, Buffalo, Camel) | **₹37,500** | Maximum 3 animals per family |
| `livestock.milch_small` | Small Milch Animal (Sheep, Goat) | **₹4,000** | Maximum 30 animals per family |
| `livestock.draught_large` | Large Draught Animal (Bullock, Ox, Horse) | **₹32,000** | Maximum 3 animals per family |
| `livestock.draught_small` | Small Draught Animal (Donkey, Mule, Calf) | **₹20,000** | Maximum 6 animals per family |
| `livestock.poultry` | Domestic Poultry Birds | **₹100 / bird** | Maximum ₹10,000 per family |

### 2.4 Immediate Sustenance & Household Goods
Assistance for families whose houses have been washed away or submerged:

| Item Code | Purpose | Amount | Eligibility Criteria |
|---|---|---|---|
| `household.clothing` | Emergency Clothing Assistance | **₹2,500** | Per eligible family whose clothing was lost in flood/fire/cyclone. |
| `household.utensils` | Kitchen Utensils & Household Items | **₹2,500** | Per eligible family whose kitchen equipment/provisions were submerged/lost. |

### 2.5 Ex-Gratia Relief for Life & Disability
Admissible from SDRF to victims or legal heirs:

| Item Code | Event | Amount | Recipient & Process |
|---|---|---|---|
| `ex_gratia.death` | Loss of Life caused by Disaster | **₹4,00,000** | Direct transfer to Next of Kin (NOK) based on police inquest/FIR. |
| `ex_gratia.disability_40_60` | Permanent Disability (40% to 60%) | **₹74,000** | Direct transfer based on CMO / Medical Board certificate. |
| `ex_gratia.disability_above_60` | Severe Disability (> 60%) | **₹2,50,000** | Direct transfer based on CMO / Medical Board certificate. |

---

## 3. Practical Example: Claim Calculation Walkthrough

### Scenario:
A farmer (Smt. Rina Das, Gosaba, Sundarbans, West Bengal) suffers cyclone damage:
1. Kutcha house completely destroyed in coastal plain.
2. 1.2 hectares of rainfed paddy submerged (100% loss).
3. 2 small milch goats drowned.
4. Household items and clothing washed away.

### Algorithmic Evaluation by Aapke Liye:
1. `house.fully_damaged_plain`: $1 \times ₹1,20,000 = ₹1,20,000$
2. `crop.rainfed`: $1.2 \times ₹8,500 = ₹10,200$ (well within 2.0 ha cap; > ₹1,000 minimum)
3. `livestock.milch_small`: $2 \times ₹4,000 = ₹8,000$ (well within 30 animal cap)
4. `household.clothing`: $1 \times ₹2,500 = ₹2,500$
5. `household.utensils`: $1 \times ₹2,500 = ₹2,500$

$$\text{Total Sanctioned Relief} = ₹1,20,000 + ₹10,200 + ₹8,000 + ₹2,500 + ₹2,500 = \mathbf{₹1,43,200}$$

*Verification Note:* The PDF generated by Member 2 shows itemized line items with exact MHA rate annotations.
