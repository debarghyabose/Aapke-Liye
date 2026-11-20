<div align="center">

# 🤝 Aapke Liye — *For You*

### Speak once. Get your relief form. Even with no network.

**A voice-first, offline-capable disaster relief claim app for India — in 6 languages.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![PWA](https://img.shields.io/badge/Citizen%20App-PWA-5A0FC8?logo=pwa&logoColor=white)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)
![Cloud Run](https://img.shields.io/badge/Deploy-Cloud%20Run%20(Mumbai)-4285F4?logo=googlecloud&logoColor=white)
![Gemini](https://img.shields.io/badge/AI-Gemini-8E75B2?logo=googlegemini&logoColor=white)
![AlloyDB](https://img.shields.io/badge/DB-AlloyDB-4285F4?logo=postgresql&logoColor=white)
![Status](https://img.shields.io/badge/status-planning-orange)

[The Problem](#-the-problem) · [How it works](#-how-it-works) · [Architecture](#-architecture) · [Repo Structure](#-repository-structure) · [Team](#-team--ownership) · [Work Plan](#-work-plan) · [Getting Started](#-getting-started)

</div>

---

## 🌊 The Problem

When a flood, cyclone, landslide or fire hits, the people who need relief the most face a wall:

- 📄 **Paper forms** they can't read, in a language that isn't theirs.
- 🪪 **Documents lost** in the very disaster they are claiming for.
- 📵 **No network** for days — exactly when claims must be filed.
- ⏳ **Long queues** at block offices, and claims that silently go missing.

Officials, on the other side, drown in handwritten forms with no way to search, verify or prioritise them.

## 💡 Our Solution

**Aapke Liye** lets any citizen **speak** their loss in their own language. AI turns that into a complete, official relief claim — and if the network is down, the app **finishes the claim on the phone** and sends it automatically when signal returns.

| For citizens (free) | For officials (paid) |
|---|---|
| 🗣️ Speak in 1 of 6 languages — no typing, no reading needed | 📊 Dashboard filtered by block & status |
| 📸 Photograph damage — GPS + time saved as proof | 🕐 Sees the **original** filing time, even for offline claims |
| 🤖 AI asks follow-up questions out loud | 💬 Ask questions in plain language → read-only SQL |
| 📴 Works fully offline, syncs later | ✅ Approve, or 🚩 flag for field visit |
| 🧾 Gets a PDF with claim ID + QR, instantly | 🔍 AI-rechecked relief amounts per SDRF norms |

---

## 🔄 How it works

![Aapke Liye app workflow](assets/workflow.jpg)

<details>
<summary><b>📝 Step-by-step (click to expand)</b></summary>

1. **Open app** — PWA, cached on the phone. Pick 1 of 6 languages.
2. **Consent**, then **speak** or **photograph** the damage (GPS + time saved).
3. **Network check (5 s)**
   - **Online →** Gemini turns voice into claim JSON → asks follow-ups (spoken by Cloud TTS) until nothing is missing.
   - **Offline →** guided taps + prerecorded voice prompts → *the same* claim JSON → relief **estimated** from cached SDRF rates.
4. **Read-back** — the claim is read aloud; the citizen confirms.
5. **Documents lost?** — upload substitute proof; Gemini vision checks it (queued if offline).
6. **Fill relief form** — PDF + claim ID + QR (offline: draft + QR).
7. **Save on phone first** — always, in IndexedDB.
8. **Send** when network is available — JSON first, then audio, then photos. Retries on app open, on signal return, and every 30 s.
9. **Server** saves to AlloyDB + Cloud Storage (upsert by claim ID), Gemini re-checks audio/photos and relief, produces the final PDF + status.
10. **Officials** review on the dashboard → **Approve** (relief released) or **Flag for field visit**.

</details>

---

## 🏗️ Architecture

```mermaid
flowchart LR
    subgraph Phone["📱 Citizen phone (PWA)"]
        UI[UI · 6 languages]
        SW[Service worker<br/>app cache]
        IDB[(IndexedDB<br/>claims + media)]
        SYNC[Sync engine<br/>JSON → audio → photos]
        EST[SDRF estimator<br/>cached rates]
        UI --> IDB
        UI --> EST
        IDB --> SYNC
    end

    subgraph GCP["☁️ Google Cloud · asia-south1 (Mumbai)"]
        API[FastAPI on Cloud Run<br/>one service]
        DB[(AlloyDB<br/>claims)]
        GCS[(Cloud Storage<br/>audio · photos · PDFs)]
        API --> DB
        API --> GCS
    end

    subgraph AI["🤖 Google AI"]
        GEM[Gemini<br/>voice → JSON · vision · NL→SQL]
        TTS[Cloud TTS]
    end

    SYNC -- HTTPS, idempotent upsert --> API
    UI -- online only --> API
    API --> GEM
    API --> TTS

    DASH[🖥️ Officials dashboard] --> API
```

**Key design rules**

| # | Rule | Why |
|---|---|---|
| 1 | **One claim JSON format** for online *and* offline | Everything downstream is a single pipeline |
| 2 | **Save on phone first, always** | A claim is never lost — even if the phone dies mid-upload |
| 3 | **Upload order: JSON → audio → photos** | The important, tiny part gets through on 2G |
| 4 | **Upsert by claim ID** (UUID made on the phone) | Retries are always safe; no duplicates |
| 5 | **Server re-verifies everything** | Offline estimates are never final |
| 6 | **Original filing time is kept** | Offline filers are never penalised |
| 7 | **NL→SQL runs as a read-only DB role** | The AI can never change data |

### 🧰 Tech stack

| Layer | Technology |
|---|---|
| Citizen app | PWA · Vanilla JS + Vite · Service Worker · IndexedDB · MediaRecorder |
| Officials dashboard | Static HTML/JS served by the same FastAPI service |
| Backend | Python 3.12 · FastAPI · SQLAlchemy · ReportLab (PDF) · qrcode |
| AI | Gemini (audio understanding, vision, NL→SQL) · Google Cloud Text-to-Speech |
| Data | AlloyDB (PostgreSQL-compatible) · Cloud Storage |
| Hosting | Cloud Run, `asia-south1` (Mumbai) — data stays in India |
| CI | GitHub Actions |

### 🌐 Languages

Hindi · Bengali · Marathi · Tamil · Telugu · English

---

## 📁 Repository structure

```
Aapke-Liye/
├── Member-1/README.md    🎨 Citizen App & Experience
├── Member-2/README.md    📴 Offline & Sync Engineer
├── Member-3/README.md    🤖 AI Engineer
├── Member-4/README.md    🗄️ Backend & Data Engineer
├── Member-5/README.md    🖥️ Officials Dashboard & DevOps
├── assets/workflow.jpg   app workflow diagram
├── README.md
└── LICENSE
```

---

## 👥 Team & ownership

| Member | Role | Key deliverables |
|---|---|---|
| [**Member 1**](Member-1/README.md) | 🎨 Citizen App & Experience | All citizen screens, 6 languages, offline guided-tap flow (3b), voice read-back, accessibility |
| [**Member 2**](Member-2/README.md) | 📴 Offline & Sync Engineer | Service worker, IndexedDB, 5 s network test, sync queue & retries, SDRF estimate (4b), draft PDF + QR on the phone |
| [**Member 3**](Member-3/README.md) | 🤖 AI Engineer | Voice → claim JSON, follow-up questions, Cloud TTS, substitute-proof vision check, server recheck of offline claims |
| [**Member 4**](Member-4/README.md) | 🗄️ Backend & Data Engineer | FastAPI, AlloyDB, safe-to-repeat uploads, Cloud Storage, final PDF + QR, relief calculation, claim format |
| [**Member 5**](Member-5/README.md) | 🖥️ Officials Dashboard & DevOps | Dashboard, "Ask your claims" (read-only SQL), Cloud Run deploy, CI, monitoring |

👉 Each member's folder has their full task list, week-by-week timeline and "done when" goal.

---

## 🎯 Final goal

> **A citizen in a flood-hit village, with no network and no documents, can file a complete relief claim by voice in under 5 minutes — and an official in the block office sees it, verified, the moment signal returns.**

**Definition of done (v1.0)**

- [ ] Full claim filed **by voice** in all **6 languages**, online
- [ ] Full claim filed **with zero network**, synced automatically later
- [ ] **No claim ever lost** — kill the app / phone mid-upload and it still arrives
- [ ] **No duplicate** claims from retries
- [ ] Relief estimate on phone matches server re-check for standard cases
- [ ] Citizen receives PDF + claim ID + QR
- [ ] Officials can filter, ask questions in plain language, approve or flag
- [ ] Runs on a ₹7,000 Android phone on a 2G connection
- [ ] Deployed on Cloud Run (Mumbai) with CI green

---

## 🗓️ Work plan

6 weeks, 3 phases, starting Mon 23 Nov 2026. Per-member weekly tasks are in each `Member-N` folder.

```mermaid
gantt
    title Aapke Liye — 6-week plan
    dateFormat  YYYY-MM-DD
    axisFormat  W%W
    section Phase 1 · Foundation
    Claim schema + API contract (all)      :p1a, 2026-11-23, 4d
    Repo, CI, Cloud Run skeleton (M5)      :p1b, 2026-11-23, 5d
    PWA shell + language/consent (M1)      :p1c, 2026-11-25, 6d
    IndexedDB + service worker (M2)        :p1d, 2026-11-25, 6d
    DB schema + upsert API (M4)            :p1e, 2026-11-25, 6d
    Gemini voice → JSON prototype (M3)     :p1f, 2026-11-25, 6d
    section Phase 2 · Core flows
    Online voice loop + TTS (M1, M3)       :p2a, 2026-12-07, 7d
    Offline guided flow + estimator (M1,M2):p2b, 2026-12-07, 7d
    Sync engine + retries (M2, M4)         :p2c, 2026-12-10, 7d
    PDF + QR, storage (M4)                 :p2d, 2026-12-10, 7d
    Dashboard + filters (M5)               :p2e, 2026-12-07, 10d
    section Phase 3 · Polish & ship
    Vision proof check + server recheck(M3):p3a, 2026-12-21, 6d
    NL → SQL (M5)                          :p3b, 2026-12-21, 6d
    Field test, 2G test, bug bash (all)    :p3c, 2026-12-28, 5d
    Demo + v1.0 release (all)              :milestone, 2027-01-02, 0d
```

| Phase | Weeks | Milestone |
|---|---|---|
| 🧱 **1. Foundation** | 1–2 | Contract frozen; an empty claim can travel phone → IndexedDB → API → AlloyDB |
| ⚙️ **2. Core flows** | 3–4 | Full claim works online **and** offline end-to-end; officials can see it |
| 🚀 **3. Polish & ship** | 5–6 | AI re-check, NL→SQL, real-device testing, v1.0 demo |

---

## 🚀 Getting started

> 🚧 **The repo is at the planning stage.** Code arrives phase by phase, following the work plan above.

1. Clone the repo:
   ```bash
   git clone https://github.com/debarghyabose/Aapke-Liye.git
   ```
2. Open your `Member-N` folder and add your name and GitHub username to its README.
3. **Week 1:** agree on the claim JSON format together. Everything else builds on it.

### Prerequisites (for when building starts)
- Node.js 20+ · Python 3.12+ · PostgreSQL 15+ (local stand-in for AlloyDB)
- A Google Cloud project with the Gemini API and Cloud TTS enabled

---

## 🤝 Contributing

Branch from `main` as `m<N>/<short-topic>` (e.g. `m2/sync-retry`), open a pull request, and get one review from a teammate.

## 🔐 Privacy

Consent is taken before any data is collected. We store only the **last 4 digits** of any ID number, keep all data in India (`asia-south1`), and officials' AI queries run on a **read-only** database role.

## 📄 License

Released under the [MIT License](LICENSE).

<div align="center">

**Made with ❤️ for the people who need it most — *aapke liye*.**

</div>
