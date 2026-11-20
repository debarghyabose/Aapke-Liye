# 🛰️ Member 3: Verification + Offline + Channels

**Name:** Debanik Dey · **GitHub:** [DEBANIK07](https://github.com/DEBANIK07)

## Your job
Make claims trustworthy for officials, make sure no claim is lost when the network drops, and reach people without smartphones.

## Phase 1: Core demo (build first)
- [x] **Damage vision:** AI checks the damage photos (Gemini free tier, or Claude)
- [x] **Basic verification:** check that the GPS location and timestamp look right
- [x] **Basic duplicate check:** flag the same photo or claim sent twice (also catches re-saved copies)
- [x] **Offline sync:** queue uploads so nothing is lost when the network drops
  (`offline-client/queue.js`, sends to Member 2's backend; see "Offline queue" below)

## Run it

```powershell
cd Member-3
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env      # then put your GEMINI_API_KEY in .env (never in .env.example)
uvicorn app.main:app --port 8002 --reload
```

- Member 2's backend finds this service through `MEMBER3_VERIFY_URL=http://localhost:8002`.
- API docs: http://localhost:8002/docs
- Tests (never use real API quota): `python -m pytest -q`
- Try the AI on your own photo: `python scripts/try_photo.py path\to\photo.jpg`

## Dashboard data (for Member 5)

Every `/verify` result is saved in SQLite (`member3.db`). These endpoints serve it for the
government dashboard in `Member-5/docs/government_dashboard_spec.md`. Names, villages, rupee
amounts and claim status come from Member 2: **join on `claim_id`**.

| Endpoint | For | What it returns |
|---|---|---|
| `GET /dashboard/summary` | KPI bar | Claims, photos, counts by severity (`severe`/`moderate`/`minor`/`none`), damage type and flag |
| `GET /dashboard/claims.geojson` | Map pins, priority list (VPI `S_damage`) | One point per claim: `damage_score` 0–100, `severity_band`, `damage_types`, `sdrf_categories`, `flags`, `duplicate_of`. Filters: `?min_score=50`, `?flagged_only=true` |
| `GET /dashboard/heatmap.geojson` | Heatmap layer | Claims grouped into grid cells (`?cell_km=1`) with `weight`, `claims`, `severe_claims`, `max_damage_score` |
| `GET /dashboard/fraud-flags` | Anomaly review queue | `duplicate_photo` (with `other_claim_id` for the side-by-side), `gps_mismatch` (with `distance_km`), `not_genuine_photo`, `outside_disaster_area`, each with the action for the official |

- GeoJSON works directly in Leaflet (`L.geoJSON(data)`) and MapLibre (`addSource({type: "geojson", data})`).
- Claim flags: `duplicate_photo`, `gps_mismatch`, `not_genuine_photo`, `outside_disaster_area`,
  `no_location`, `no_capture_time`, `time_invalid`, `damage_not_assessed`.
- **Privacy:** these endpoints show exact victim locations. Set `DASHBOARD_API_KEY` in `.env` and
  send it as the `X-Dashboard-Key` header. The service warns at startup when the key isn't set.
  The heatmap's grid cells hide exact household locations.
- Fraud flags are for review only. None of them proves fraud: an official decides.
- **Member 5's dashboard** (`Member-5/dashboard/index.html`) connects automatically when this
  service runs on port 8002: KPIs, map, damage queue and fraud panel switch to live data, and it
  falls back to its sample data otherwise. Browsers may only read `/dashboard` from the pages listed
  in `DASHBOARD_CORS_ORIGINS` (by default, the file opened directly and a few localhost ports).
- Photo fingerprints are saved too, so a re-used photo is still caught after a restart.

## Satellite and map checks

For photos with their own GPS (EXIF), `/verify` also checks local map files:

| Check | Data (local files) | Result in `notes` / dashboard |
|---|---|---|
| **Flood map**: was this spot flooded? | Flood-extent polygons from **Copernicus EMS** or **ISRO Bhuvan/NRSC** (`.geojson` or `.shp`) in `FLOOD_MAP_FILES` | "inside the flooded area", "X km from the mapped flooding" (`outside_flood_extent`), or "No satellite flood map covers this location yet" |
| **Building map**: is there a building at a "house" photo? | **Google Open Buildings** CSV or **OpenStreetMap** GeoJSON in `BUILDING_FILES` | "a building is mapped X m away", or `no_building_at_location` |

- **Only the photo's own GPS is used.** Relief camps are usually on dry ground, so the phone's
  location at upload time would make every camp-filed claim look "outside the flood".
- **Local files only:** no victim location is sent to any outside map service.
- **Snapshots, not proof:** a flood map shows water at the moment the satellite passed (there is a
  300 m tolerance), and building maps of rural India are incomplete. Both are review notes.
- `GET /dashboard/flood-extent.geojson` serves the loaded polygons. Member 5's dashboard draws them
  as the "Satellite flood map" layer.
- **Real data included:** `data/copernicus/` has Copernicus EMS flood maps for Andhra Pradesh
  (EMSR104, 2014) and Puri (EMSR357, Cyclone Fani 2019), plus **9,777 Puri buildings graded from
  satellite images** (Destroyed / Damaged / Possibly damaged). A claim photo at a graded building
  gets the note *"Satellite damage grading (Copernicus EMS EMSR357): … graded "Destroyed""*.
  Credit Copernicus EMS whenever you show them (see `data/copernicus/README.md`).
- Shapefiles in metres (UTM) are converted automatically using their `.prj` file. Use
  `scripts/convert_cems.py` to turn a new Copernicus vector package into GeoJSON.
- Outside the flood map is **not** flagged when satellite grading shows the building damaged
  (cyclone wind damage).
- `data/demo/DEMO_synthetic_flood_extent.geojson` is **synthetic demo data**, not from a satellite.
- **Crop before/after (Sentinel-2 NDVI):** for a *crop* photo with its own GPS and capture time,
  the service compares the field's greenness (NDVI) in the clearest image **45–120 days before**
  the photo with the clearest image **after the disaster started** (up to 7 days after the photo).
  It runs **in the background** (10–30 s) after `/verify` replies, and the result appears on the
  dashboard as `crop_satellite`:

  | Result | Meaning |
  |---|---|
  | `vegetation_loss` | Greenness dropped by 0.15 or more: consistent with crop damage |
  | `water_after` | The field is under water after: consistent with flood damage |
  | `no_change` | About the same: flag `crop_unchanged_after`, check on site |
  | `little_vegetation_before` | Little green before: flag `crop_no_vegetation_before` (may be between crop seasons) |
  | `no_clear_image` | Clouds (common in the monsoon): no verdict, never a guess |

  Images come from Earth Search (AWS open data, Sentinel-2 L2A, no account). **Privacy:** only a
  ~25 km box is sent in the search, never the exact field, and no claim ID, name or phone is sent.
  Tested on real Cyclone Fani data: villages west of Puri **0.80 → 0.26** (vegetation loss), while
  a control area far inland stayed **0.63 → 0.67** (no change). Turn off with `NDVI_ENABLED=false`.
- **Not possible with free data:** checking whether one specific house was intact before the
  disaster needs ~0.5 m imagery (ISRO Cartosat through NRSC, or Maxar Open Data for major
  disasters). Free Sentinel imagery is 10 m per pixel, about one pixel per house.

## Fraud checks

Every check is a **flag for an official to review**, never an automatic rejection.

| Check | How | Flag |
|---|---|---|
| Same photo | Perceptual hash: identical, re-saved or slightly edited copies on another claim | `duplicate_photo` |
| Same house | A *different* photo whose own GPS (EXIF) is within 25 m of another claim's photo | `possible_same_house` |
| Same person | One phone number behind more than 3 other claims in 24 h (Member 5's spec) | `phone_many_claims` |
| Wrong place | Photo GPS more than 2 km from the phone's location, or outside the disaster area | `gps_mismatch`, `outside_disaster_area` |
| Fake image | The AI judges it a screenshot, stock, drawing or AI-generated image | `not_genuine_photo` |

- **Same house uses only the photo's own GPS.** The phone's location at upload time would flag
  every family an NGO worker files for from the same relief camp. Phone GPS is often only
  accurate to 5–20 m, so neighbours can be flagged too; the note says so.
- **Phone numbers are never stored.** Only a keyed fingerprint (HMAC-SHA256 of the last 10
  digits) is kept, so `+91 98765 43210` and `9876543210` match. Set `PHONE_HASH_KEY` in production.
- **Member 2:** to switch on the same-person check, also send `phone` to `/verify`. The field is
  optional; without it, everything else works as before.
- Settings: `SAME_HOUSE_RADIUS_M`, `PHONE_MAX_OTHER_CLAIMS_24H`, `PHONE_HASH_KEY` in `.env`.

## Offline queue (for Member 4's frontend)

`offline-client/queue.js` is a plain ES module with no build step. Every claim step is saved
on the phone first (IndexedDB) and sent to Member 2's backend when the connection is back:
**create claim → voice recording → photos**, in order. Nothing is lost if the signal drops.

```js
import { createOfflineQueue } from "./queue.js";
const q = createOfflineQueue({ apiBase: "http://localhost:8000" });   // Member 2's backend

const localId = await q.startClaim({ language: "hi", disaster_type: "flood",
                                     consent: true, consent_text_version: "v1" });
await q.addAudio(localId, audioBlob, "recording.webm");
await q.addPhoto(localId, photoBlob, { lat, lon, taken_at: new Date().toISOString() });

q.on("change", async () => render(await q.list()));    // progress: { jobs, pending, failed }
q.on("claim-created", ({ claimId }) => showClaimId(claimId));
q.on("failed", ({ error }) => showError(error));         // the server refused it: tell the user
const { claimId, token } = await q.getClaim(localId);   // filled once the claim reached the server
```

- **Works offline right away.** `startClaim` returns a local id at once, even with no signal.
- **Retries by itself** with growing waits (2 s, 4 s, 8 s … up to 5 min), and immediately when
  the phone comes back online. It respects `Retry-After`.
- **Safe to retry.** Member 2 ignores a photo uploaded twice. If Member 1's AI is down, the
  recording is already kept on the server, so the queue asks for `/audio/retry` instead of
  uploading again.
- **Doesn't retry forever on real errors.** A 4xx reply (for example a claim already submitted)
  is marked `failed`, with a readable message for the user.
- The claim token is stored on the device only and is never included in `list()`.

**Demo:** `cd offline-client; python -m http.server 3000`, then open
http://localhost:3000/demo.html (Member 2's backend allows browser calls from port 3000).
Stop the backend or turn off Wi-Fi, start a claim and add a photo, then reconnect: everything
uploads by itself.

## Demo day (Cyclone Fani, Puri)

1. In `.env`: the Puri demo settings from `data/copernicus/README.md`, plus `GEMINI_API_KEY` and
   `DASHBOARD_API_KEY`.
2. Start the service: `uvicorn app.main:app --port 8002`.
3. Fill the dashboard with demo claims (7 Gemini calls, so run it early):
   ```powershell
   python scripts/seed_demo.py
   ```
   It sends 7 `DEMO-` claims through `/verify`, using the real photos in `data/demo/photos/`
   (credits in `ATTRIBUTION.md`) with demo Puri GPS added in memory. They cover: a satellite-graded
   "Destroyed" house inside the flood map, a "Damaged" house outside it (wind damage, so no flood
   flag), a duplicate photo, the same house from another photo, a chat screenshot, one phone behind
   5 claims, a 54 km GPS mismatch, a crop field with a Sentinel-2 before/after loss, and a house
   outside the disaster area.
4. Open Member 5's dashboard (`Member-5/dashboard/index.html`), paste the dashboard key, and press
   **Connect live**.

The script refuses to run twice, because re-adding the same photos would flag them all as
duplicates. To start over: stop the service, delete `member3.db`, start it, and run the script again.
Photos taken live at the venue fall outside the Puri disaster area, which is correct. For a live
demo, set `DISASTER_ZONE_*` to where you are.

## Damage AI accuracy (CrisisMMD benchmark)

Tested on a **balanced, reproducible sample of 30 photos** (10 per label, random seed 42) from the
**CrisisMMD damage-severity test split** (QCRI; 7 disasters, including the 2017 Sri Lanka floods).
Labels are by human annotators. Model: Gemini free tier (`gemini-3.6-flash`, falling back to
`gemini-3.5-flash-lite` when busy). Run on 20 Nov 2026.

| Measure | Result |
|---|---|
| Exact agreement (none / mild / severe; chance = 33%) | **47%** (14/30) |
| Within one level | **100%** (30/30): never "none" for severe or "severe" for none |
| Damage vs no damage | **70%** (21/30) |

Confusion (rows = human label, columns = model):

| | none | mild | severe |
|---|---|---|---|
| **none** | 3 | 7 | 0 |
| **mild** | 2 | 5 | 3 |
| **severe** | 0 | 4 | 6 |

What the misses show:
- **Human "none" → model "mild" (7/10):** mostly damage that isn't to a home, such as snapped
  trees, downed power poles or debris. CrisisMMD calls these "little or no damage"; the relief
  prompt counts any visible damage. This is a different definition of the task more than an error.
- **Human "severe" floods → model "mild" (4):** flood water around a house is scored about 0.4 by
  the inundation rule in the prompt.

**Limits:** 30 photos is a rough estimate (about ±15%). The photos are mostly US hurricanes and
wildfires from Twitter, not Indian claim photos. Free-tier model quality varies. Every claim is
reviewed by an official anyway. To improve without overfitting, tune on CrisisMMD's **dev** split
and report on **test**, with 100+ photos.

Reproduce: download CrisisMMD (`huggingface.co/datasets/QCRI/CrisisMMD`, CC BY-NC-SA 4.0) and run
`python scripts/eval_accuracy.py labels.csv --out results.csv`. The script retries when the free AI
is busy, so busy moments are never scored as wrong answers.

## API

**`POST /verify`**, called by Member 2 for every claim photo.
Multipart `photo` (required), plus `lat`, `lon`, `taken_at` (ISO 8601), `claim_id` and, optionally, `phone`.

```json
{"damage_detected": true, "damage_score": 0.8, "gps_ok": true, "timestamp_ok": true,
 "duplicate": false, "notes": ["Roof collapsed.", "Suggested SDRF category: kutcha house fully damaged"]}
```

- `notes` explain every problem found, for example GPS far from the phone's location, a photo taken
  before the disaster, a copy of another claim's photo, or an image that is not a genuine photo.
- If the damage AI is only temporarily unavailable (free-tier limit or busy), `/verify` returns
  **503**. Member 2 then keeps the photo as `pending` and can re-check it later.
- Gemini models are tried in order (`GEMINI_MODELS`). A busy model falls through to the next one,
  and the whole check finishes within 25 seconds (Member 2 waits 30).

## Phase 2: Roadmap features (after the demo works)
| Feature | What to do |
|---|---|
| ✅ Satellite verification | Flood maps + satellite building damage grading (real Copernicus EMS data) and crop before/after from Sentinel-2 NDVI. ISRO Bhuvan layers need a login; house-level before/after needs ISRO Cartosat (roadmap) |
| ✅ Advanced fraud detection | Flag the same photo, house or person claiming twice (see "Fraud checks" below) |
| WhatsApp bot | File a claim by sending a voice note on WhatsApp |
| IVR / missed-call line | Feature-phone users call in and speak their claim |
| Voice/SMS status updates | Send each status change to the user in their own language |
| ✅ Dashboard data | Provide the map and damage data for the government dashboard that Member 5 designs (see "Dashboard data" below) |

## You work with
- **Member 2:** stores your verification results
- **Member 5:** uses your data for the dashboard
