# 📴 offline/ — Owner: 📴 M2

The part that makes sure **no claim is ever lost**. Design: [`docs/OFFLINE_SYNC.md`](../../../../docs/OFFLINE_SYNC.md)

| Planned file | Does |
|---|---|
| `db.js` | IndexedDB wrapper — `claims`, `media`, `meta` stores |
| `network.js` | 5-second network test |
| `sync.js` | Queue + retries (app open, signal back, every 30 s); upload order JSON → audio → photos |
| `estimate.js` | Relief estimate from cached SDRF rates (step 4b) — must match the server's calculation |
| `draft-pdf.js` | Draft PDF + QR on the phone when offline |
| `compress.js` | Shrink audio and photos before saving |
