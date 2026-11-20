# 📴 Offline & Sync Design

Owner: **M2** · Reviewers: M1, M4

## Principles

1. **Phone saves first, always.** Every claim and every media file is written to IndexedDB *before* any network call.
2. **Same claim JSON** whether filed online or offline (`source: "online_ai" | "offline_guided"`).
3. **Idempotent everything.** `claim_id` is a UUIDv4 made on the phone. Sending twice = no harm.
4. **Most important bytes first.** JSON → audio → photos.

## IndexedDB layout (`aapke-liye` DB, version 1)

| Store | Key | Value |
|---|---|---|
| `claims` | `claim_id` | Claim JSON + `sync_state` |
| `media` | `media_id` | `{ claim_id, kind: "audio"\|"photo"\|"proof", blob, sha256, uploaded: bool }` |
| `meta` | `key` | `sdrf_rates`, `rates_version`, `language`, `last_sync_at` |

`sync_state`: `draft` → `queued` → `json_sent` → `media_sent` → `done` (or `error` with `last_error`).

## Network test (5 s)

```
GET /api/health  with AbortController timeout 5000 ms
  200 within 5 s → online
  anything else  → offline
```
`navigator.onLine` is used only as a *hint* (false ⇒ offline immediately; true ⇒ still run the test).

## Sync triggers

| Trigger | How |
|---|---|
| App opened | `sync()` on startup |
| Signal returns | `window.addEventListener("online", sync)` |
| Timer | `setInterval(sync, 30_000)` while the app is visible |
| Background (Android/Chrome) | Background Sync tag `claims-sync` when supported |

Only one sync runs at a time (in-memory lock). Back-off on server errors: 30 s → 60 s → 120 s (max 5 min).

## Sync algorithm

```
for claim in claims where sync_state in (queued, json_sent, media_sent, error):
    if not json sent:   PUT /api/claims/{id}            → json_sent
    for media in claim.media where not uploaded, order by kind (audio, photo, proof):
        PUT /api/claims/{id}/media/{kind}?sha256=...     → uploaded = true
    GET /api/claims/{id}/status                          → done, store final PDF URL + status
```

## What the citizen sees

| State | Badge |
|---|---|
| Saved, no network | 🟣 *Waiting for network* · offline ref `AL-XXXX-XXXX` |
| Sending | 🔵 *Sending… (2 of 3)* |
| Done | 🟢 *Submitted* · claim ID · final PDF |

The offline ref number is the first 8 hex characters of `claim_id`, which is also printed in the QR, so an official can match a paper draft to the server record.

## Relief estimate (step 4b)

`src/offline/estimate.js` mirrors `backend/app/services/relief.py` and reads the same `shared/sdrf/sdrf_rates.json`. **Both must give the same answer for the same claim** — there is a shared test vector set in `shared/sdrf/test_vectors.json`.

## Testing checklist

- [ ] DevTools offline → file claim → reload → claim still there
- [ ] Go online → claim syncs without user action
- [ ] Kill tab mid-photo-upload → reopen → upload resumes, no duplicate on server
- [ ] Throttle to "Slow 3G" / 2G profile → JSON arrives in < 5 s
- [ ] Storage quota: 20 claims with 3 photos each fit (≈ 15 MB)
