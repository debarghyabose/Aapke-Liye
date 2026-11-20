# 🔐 DPDP Act 2023 Compliance & Data Privacy Architecture
## Protecting Disaster Victims' Rights under India's Digital Personal Data Protection Act

> **Author:** Member 5 (Entitlement, Policy & Pitch)  
> **Statutory Basis:** Digital Personal Data Protection Act, 2023 (Act No. 22 of 2023)  
> **Enforcement Body:** Data Protection Board of India (DPBI) & Ministry of Electronics & IT (MeitY)  
> **Classification:** Aapke Liye Core Privacy Standard

---

## 1. Statutory Context

Disaster victims in emergency conditions are uniquely vulnerable to predatory data harvesting, identity theft, and unauthorized commercial exploitation. Under the **Digital Personal Data Protection Act, 2023 (DPDP Act)**, Aapke Liye operates as a **Data Fiduciary** committed to the highest standards of data stewardship and citizen empowerment.

Disaster relief processing falls under:
- **Section 6 (Consent):** Explicit, informed, unconditional consent collected in the Data Principal's native tongue.
- **Section 7 (Certain Legitimate Uses):** Medical emergency, disaster response, and state service delivery; however, Aapke Liye goes beyond by obtaining affirmative multi-lingual consent for all operations.

---

## 2. The Six Pillars of Privacy in Aapke Liye

### 2.1 Pillar 1: Multi-Lingual, Plain-Language Consent (Section 5 & 6)
Consent is collected before any voice note or photograph is recorded. The notice is rendered both as plain, uncompressed text and as a synthesized spoken audio readout in the user's selected language:

#### Official Consent Declaration Across 6 Languages:
- **English:**  
  *"I agree that the information, voice recordings and photographs I provide may be collected and processed by disaster relief authorities solely for evaluating and disbursing my official relief claim under the Disaster Management Act 2005 and DPDP Act 2023. I understand that I retain the right to review and request correction of my data."*
- **Hindi (हिन्दी):**  
  *"मैं सहमति देता/देती हूँ कि मेरे द्वारा प्रदान की गई जानकारी, आवाज़ की रिकॉर्डिंग और तस्वीरें आपदा प्रबंधन अधिनियम 2005 और डीपीडीपी अधिनियम 2023 के तहत केवल मेरे आधिकारिक राहत दावे के प्रसंस्करण के लिए एकत्र और उपयोग की जा सकती हैं। मुझे अपने डेटा की समीक्षा और सुधार का अधिकार है।"*
- **Bengali (বাংলা):**  
  *"আমি সম্মত হচ্ছি যে আমার দেওয়া তথ্য, ভয়েস রেকর্ডিং এবং ছবিগুলি দুর্যোগ ব্যবস্থাপনা আইন ২০০৫ এবং ডিপিডিপি আইন ২০২৩-এর অধীনে কেবল আমার ত্রাণের দাবি প্রক্রিয়া করার জন্য ব্যবহার করা হবে। আমার তথ্য পর্যালোচনা ও সংশোধন করার অধিকার রয়েছে।"*
- **Telugu (తెలుగు):**  
  *"విపత్తు నిర్వహణ చట్టం 2005 మరియు DPDP చట్టం 2023 ప్రకారం నా అధికారిక సహాయ దావాను ప్రాసెస్ చేయడానికి మాత్రమే నేను అందించిన సమాచారం, వాయిస్ రికార్డింగ్‌లు మరియు ఫోటోలను సేకరించి ఉపయోగించడానికి నేను అంగీకరిస్తున్నాను. నా డేటాను సమీక్షించే మరియు సరిదిద్దే హక్కు నాకు ఉంది."*
- **Marathi (मराठी):**  
  *"आपत्ती व्यवस्थापन कायदा 2005 आणि DPDP कायदा 2023 अंतर्गत केवळ माझ्या अधिकृत मदत अर्जावर प्रक्रिया करण्यासाठी मी दिलेली माहिती, आवाज रेकॉर्डिंग आणि फोटो संकलित करण्यास मी संमती देतो/देते. मला माझ्या माहितीचे पुनरावलोकन आणि दुरुस्ती करण्याचा अधिकार आहे।"*
- **Tamil (தமிழ்):**  
  *"பேரிடர் மேலாண்மைச் சட்டம் 2005 மற்றும் DPDP சட்டம் 2023 ஆகியவற்றின் கீழ் எனது அதிகாரப்பூர்வ நிவாரணக் கோரிக்கையைச் செயல்படுத்த மட்டுமே நான் வழங்கும் தகவல்கள், குரல் பதிவுகள் மற்றும் புகைப்படங்களைச் சேகரிக்க நான் ஒப்புக்கொள்கிறேன். எனது தரவை மதிப்பாய்வு செய்து திருத்துவதற்கான உரிமை எனக்கு உள்ளது."*

---

### 2.2 Pillar 2: Strict Purpose Limitation (Section 4)
- Personal data is processed **exclusively** for determining disaster eligibility, generating official government forms, and enabling direct bank disbursement.
- Personal data is **never shared, sold, rented, or utilized for commercial ad targeting, political canvassing, or credit profiling**.

### 2.3 Pillar 3: Data Minimization (Section 6)
- The system extracts only what is required by MHA SDRF relief forms: Name, Phone, Village, District, Incident Date, Loss Item, and Bank Account Availability.
- Photos are collected strictly for structural damage, crop loss, or animal casualties. No facial recognition or biometric indexing is performed on claimant faces.

### 2.4 Pillar 4: Right to Correction & Erasure (Section 12)
- Member 4's **Review Screen** provides a mandatory verification step before submission: the user inspects every extracted field and can tap "Edit" to modify, update, or delete any incorrectly transcribed entry.
- Claims remaining in un-submitted "Draft" state are automatically purged after 30 days unless extended by user action.

### 2.5 Pillar 5: Sovereign Data Localization & Encryption (Section 8)
- **Geographic Residency:** 100% of servers, databases, and media storage are hosted physically within the Republic of India (e.g. Mumbai, Pune, or Hyderabad data center availability zones).
- **Encryption at Rest:** All audio recordings and damage photographs are stored encrypted using **AES-256 (Fernet symmetric encryption)** with UUID-based anonymized storage paths.
- **Encryption in Transit:** All client-server communications require TLS 1.3.

### 2.6 Pillar 6: Grievance Redressal Officer (GRO) Mechanism (Section 13)
Every claimant has statutory recourse to a designated Grievance Redressal Officer:
- **Title:** Chief Data Protection & Grievance Officer, Aapke Liye Project
- **Email:** `grievance-dpdp@aapke-liye.gov.in` (Institutional deployment) / `dpdp@aapke-liye.org`
- **Statutory Resolution Window:** Grievance inquiries must be acknowledged within 24 hours and determined within 7 working days.

---

## 3. Developer & Agent Implementation Checklist
- [x] In `Member-2/backend/rules/labels.json`, maintain multi-lingual consent notices under `"consent"`.
- [x] In `Member-2/backend/app/logs.py`, sanitize names, phone numbers, and raw transcripts from console logs.
- [x] In `Member-2/backend/app/storage.py`, enforce Fernet encryption for all uploaded media files.
- [x] In `Member-4`, ensure the consent modal is presented on first launch before activating the microphone or camera.
