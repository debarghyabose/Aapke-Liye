# Aapke Liye (Frontend) — "After the Water, Hope"

Disaster relief claim assistance web application built with **React**, **Vite**, and **TypeScript**. Designed for flood-affected families in India to speak in their native tongue, submit geo-tagged damage evidence, calculate SDRF relief compensations, and track government DBT disbursements.

---

## 🎨 Visual Direction & Philosophy

- **Concept**: *"After the water, hope"* — calm illustrated aesthetic rooted in rural Bengal and India, avoiding generic AI-startup cliches.
- **Palette**:
  - River-silt cream `#F4EFE6` (background)
  - Deep indigo `#1F3A5F` (primary headings & navigation)
  - Terracotta `#C0582F` (call-to-action buttons)
  - Turmeric `#E3A72F` (highlights)
  - Banana-leaf green `#3E6B48` (verification & success badges)
  - Ink `#1B1B1B` (body text)
- **Typography**: Fraunces & Noto Sans serif/sans supporting Indic scripts (`Noto Sans Bengali`, `Noto Sans Devanagari`, `Noto Sans Tamil`, `Noto Sans Telugu`).
- **Hero Art**: Hand-painted watercolor depiction of a Bengal village after a flood — still waters reflecting morning light, mud house, banyan tree on dry land, and a mother and child holding a phone.

---

## 🚀 Getting Started

### 1. Install Dependencies
```bash
cd Aapke-Liye/Member-4/frontend
npm install
```

### 2. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default `VITE_API_URL` is `http://localhost:8000`.

### 3. Run Development Server
```bash
npm run dev
```
The server will start on **http://localhost:5173** (or the next available port).

### 4. Build for Production
```bash
npm run build
```
Generates production artifacts in `dist/`.

---

## 📱 Features

1. **Full 6-Step Claim Application (`/claim`)**:
   - **Step 1 (Language)**: 6 native script tiles (English, বাংলা, हिंदी, मराठी, తెలుగు, தமிழ்) with Web Speech TTS pronunciation.
   - **Step 2 (Speech)**: Large round record button with `MediaRecorder`, live timer, animated waveform visualizer, and instructions TTS.
   - **Step 3 (Follow-up Questions)**: Gemini missing-field questions with audio playback and one-tap voice responses.
   - **Step 4 (Photos)**: Camera input (`capture="environment"`), auto GPS geocoding + timestamp, Gemini structural damage scoring, EXIF and duplicate detection.
   - **Step 5 (Review & Relief)**: Editable cards, SDRF/NDRF financial computation (letters 33-03/2020-NDM-I), matched government schemes (SDRF, PMFBY, PMAY-G), and legal proof substitution advice for lost documents.
   - **Step 6 (Submitted & Reissuance Drafts)**: Claim ID, WhatsApp sharing, PDF download, and one-click draft letters for Aadhaar, ration card, land record re-issuance, and crop insurance.

2. **Claim Tracking (`/track`)**:
   - Search by Claim ID.
   - Step-by-step verification history: *Submitted → Verified → Approved → Paid*.
   - Multi-lingual audio playback.
   - Automatic RTI & grievance follow-up generator if claim exceeds 14 days without resolution.

3. **Administration & Official Portal (`/official`)**:
   - District damage heatmap OpenStreetMap simulation.
   - Vulnerability priority list auto-sorting elderly, disabled, and single-mother households.
   - Verification inspector with cross-claim duplicate photo detection alerts and status action controls.

4. **Universal Accessibility & Resilience**:
   - WCAG AA compliant contrast and touch targets $\ge 56\text{px}$.
   - High Contrast and Large Text modes.
   - IndexedDB offline queueing for zero-connectivity rural zones with automatic reconnection sync.
   - Transparent Demo Mode when backend is offline or connecting.

