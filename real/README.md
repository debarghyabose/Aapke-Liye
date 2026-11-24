# 🤝 Aapke Liye (आपके लिए) — Standalone Real Production Architecture

> **"Speak in your language. Show what you lost. Get your relief, even if your documents are gone."**

This folder (`real`) contains the **completely standalone, production-ready implementation** of Aapke Liye. All previous demo/mock subsystems have been remade into **real, fully functional services** using **Firebase Firestore** as the database, **Google Gemini 3.5 Flash** for speech-to-text, claim extraction and damage vision, and **Cloud Run** for deployment.

---

## 🎯 Target Cloud Environment

| Property | Value |
|---|---|
| **Project Name** | `aapke liye` |
| **Project Number** | `881624105738` |
| **Project ID** | `trusty-obelisk-515402-p3` |
| **Database** | Google Cloud Firestore (Native Mode, `asia-south1` Mumbai) |
| **Primary Region** | `us-central1` / `asia-south1` |
| **Cloud Run Service** | `https://aapke-liye-881624105738.us-central1.run.app` |

---

## 🚀 Key Improvements & Real Implementations

### 1. Database: Firebase Firestore Native
- **Claims Collection (`claims`)**: Stores authentic claim records, claimant identity, normalized phone numbers, multi-category losses (house, crop, livestock, utensils, death ex-gratia), SDRF calculation breakdowns, geo-tagged photo metadata, status transition histories, and audit events.
- **Household Vault Collection (`households`)**: Stores pre-disaster document vaults, Aadhaar/ration card documents, and peace-time baseline property photos.
- **Mesh Envelopes (`mesh_envelopes`)**: Stores carried cryptographic sealed claim envelopes.
- **Mesh Receipts (`mesh_receipts`)**: Stores Ed25519 digitally signed receipts.
- **Audit Logs (`audit_logs`)**: Immutable event logs for DPDP Act compliance.

### 2. Proper ID Generation & Security
- **Official Disaster Claim ID**: `AL-2026-{STATE}-{CODE}` (e.g. `AL-2026-WB-8492`, `AL-2026-OD-3749`).
- **Household Vault ID**: `HH-2026-{CODE}`.
- **Cryptographic Tokens**: 256-bit URL-safe tokens stored as SHA-256 hashes (`X-Claim-Token`, `X-Household-Token`).
- **Staff Access Key**: set via the `STAFF_API_KEYS` env var (`name:key,name:key`) for officials access.

### 3. Real AI Voice-to-Text & Claim Intelligence (Gemini 3.5 Flash)
- **Multilingual Speech Recognition (STT)**: Direct audio note ingestion (WebM, WAV, MP3, OGG, M4A) in 6 Indian languages (**Hindi, Bengali, Marathi, Tamil, Telugu, English**).
- **Automated Field Extraction**: Extracts applicant name, phone, village, district, state, calamity date, disaster type, detailed damage schedule, and vulnerability flags.
- **Dynamic Contextual Questioning**: Intelligently identifies missing fields and formulates polite, compassionate follow-up questions in the applicant's chosen language.
- **Text-to-Speech (TTS)**: Regional language voice synthesis (MP3) for "Listen" buttons across all 6 languages.

### 4. Real Damage Vision & Before/After Comparison
- **Visual Damage Detection**: Gemini Vision inspects damage photos, assesses damage severity (`none`, `partial`, `severe`, `total`), computes a confidence score (0.0 to 1.0), and notes specific physical damage evidence (collapsed masonry, submerged fields, missing roofs).
- **EXIF Metadata Extraction**: Automatically parses camera GPS coordinates (latitude/longitude) and timestamps.
- **Duplicate Detection**: Computes SHA-256 digests and perceptual hashes to prevent identical photo re-use across claims.
- **Before / After Baseline Comparison**: Compares peace-time baseline vault photos against post-disaster damage photos using Gemini Vision.

### 5. Entitlement Engine & Statutory Proof Substitution
- **SDRF 2022-26 Norms**: Exact compensation norms for housing (plain ₹1.2L / hilly ₹1.3L; pucca partial ₹6.5K; kutcha partial ₹4K; hut ₹8K; cattle shed ₹3K), crops (rainfed ₹8.5K/ha; irrigated ₹17K/ha; perennial ₹22.5K/ha), livestock (milch large ₹37.5K; small ₹4K; draught large ₹32K; poultry ₹100), household goods (clothing ₹2.5K, utensils ₹2.5K), and loss of life (₹4L).
- **Multi-Scheme Qualification**: Matches eligibility for PMAY-G Disaster Reconstruction, PMFBY crop insurance, and PM-KISAN.
- **Section 12 DM Act Proof Substitution**: Official alternative proof recommendations for lost Aadhaar, ration cards, land records, and bank passbooks.

### 6. Image & Document Storage
- **Cloudinary CDN Support**: Directly uploads to Cloudinary when `CLOUDINARY_URL` or credentials are set.
- **Resilient Fallback**: Stores securely in server storage / Firebase Storage with public URL generation.

### 7. DigiLocker Integration (Easy Version)
- Seamless mock consent flow: claimants tap "Link DigiLocker", review consent, and instantly import verified digital Aadhaar and Ration Card documents with clear `digilocker_mock` verification badges.

### 8. Store-and-Forward Mesh Relay
- **Cryptographic Sealing**: RSA-OAEP-256 key encapsulation + AES-256-GCM authenticated encryption.
- **Relay Ingestion**: Delivers carried QR code or file envelopes directly to the relief office when online.
- **Digital Receipts**: Signs tamper-proof delivery receipts using Ed25519.

### 9. Officials & GIS Dashboard
- **Interactive Leaflet Map**: Renders submitted claims with status pills, vulnerability highlights, and village clusters.
- **Heatmap Layer**: Live density visualizer across disaster districts.
- **Satellite Flood Extent**: Displays Copernicus satellite flood extent polygons (`EMSR357 Puri / EMSR104 Andhra`).
- **Fraud Risk Flags**: Flags duplicate photos, repeated phone numbers, and anomalous claims.
- **Official Status Transitions**: Draft → Submitted → Under Review → Verified → Approved → Disbursed.

### 10. Official Relief Form PDF Generation
- Generates downloadable, authentic Government of India Disaster Relief Claim Form PDF with claimant details, damage schedule, SDRF breakdown, embedded photos, and verification stamps.

---

## 📁 Folder Structure

```
real/
├── backend/
│   ├── app/
│   │   ├── main.py              # Unified FastAPI application & SPA static server
│   │   ├── config.py            # Environment settings & credentials
│   │   ├── db.py                # Firebase Firestore Native Database client
│   │   ├── id_gen.py            # Official Claim ID & token generation
│   │   ├── ai_service.py        # Gemini 3.5 Flash Multilingual Audio STT & Extraction
│   │   ├── vision_service.py    # Gemini Vision damage analysis & Before/After comparison
│   │   ├── entitlement.py       # SDRF 2022-26 relief calculation engine
│   │   ├── proofs.py            # Section 12 DMA Statutory Proof Substitution
│   │   ├── pdf_generator.py     # Authentic Disaster Relief Claim PDF builder
│   │   ├── image_storage.py     # Cloudinary + local resilient storage
│   │   ├── mesh_crypto.py       # RSA-OAEP-256 + AES-GCM + Ed25519 engine
│   │   ├── legal_templates.py   # Auto-drafting RTI & grievance petitions
│   │   ├── tts_service.py       # Regional language text-to-speech
│   │   ├── schemas.py           # Pydantic data schemas
│   │   └── routers/             # Claims, Vault, Status, Staff, Mesh, Speech, Meta
│   ├── rules/                   # SDRF norms, labels, proof substitution JSONs
│   ├── templates/               # Legal letter templates (.txt)
│   ├── fonts/                   # NotoSans multi-script fonts
│   ├── data/copernicus/         # Satellite flood extent GeoJSON files
│   ├── requirements.txt         # Backend Python packages
│   └── .env                     # Local configuration
├── frontend/                    # Vite + React + TypeScript + Tailwind + Leaflet
├── Dockerfile                   # Multi-stage production container
├── docker-compose.yml           # Local container orchestration
├── cloudbuild.yaml              # Google Cloud Build deployment pipeline
├── start.ps1                    # One-click Windows local launch script
├── deploy.ps1                   # Deploy to Cloud Run (PowerShell)
├── deploy.sh                    # Deploy to Cloud Run (Bash)
└── README.md
```

---

## 🏃 Running Locally

### Option 1: One-click PowerShell (Windows)
```powershell
cd real
.\start.ps1
```
This automatically builds the frontend if needed, verifies Python packages, and starts the server on `http://localhost:8080`.

### Option 2: Docker Compose
```bash
cd real
docker compose up --build
```

### Option 3: Manual Execution
**Terminal 1 (Backend):**
```bash
cd real/backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
```
**Terminal 2 (Frontend Dev Server - Optional):**
```bash
cd real/frontend
npm run dev
```

---

## ☁️ Deploying to Google Cloud Run

Deploy directly to project `trusty-obelisk-515402-p3` with a single command:

**On Windows:**
```powershell
cd real
.\deploy.ps1
```

**On Linux / macOS:**
```bash
cd real
chmod +x deploy.sh
./deploy.sh
```

**Direct gcloud CLI command:**
```bash
gcloud builds submit real --config=real/cloudbuild.yaml --project=trusty-obelisk-515402-p3
```

---

## 🔑 Default Official Credentials

- **Claimant Portal**: `http://localhost:8080/`
- **Officials Dashboard**: `http://localhost:8080/official`
- **Officials Staff Key**: whatever you set in `STAFF_API_KEYS` (see `backend/.env.example`)
- **Interactive API Documentation**: `http://localhost:8080/docs`
