# 🔌 API Reference (v1)

Base URL: `/api` · Interactive docs at `/docs` when the server runs.
Owner: **M4** (claims) · **M3** (voice) · **M5** (officials)

## Health

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/health` | Used by the phone's 5-second network test. Returns `{"ok": true}` |

## Citizen — voice (online only) · M3

| Method | Path | Body | Returns |
|---|---|---|---|
| `POST` | `/api/voice/extract` | multipart: `audio`, `language`, `partial_claim` (JSON) | `{ claim, missing_fields[], follow_up: { text, audio_b64 } \| null }` |
| `POST` | `/api/voice/speak` | `{ text, language }` | `audio/ogg` (Cloud TTS) — used for read-back |
| `POST` | `/api/vision/check-proof` | multipart: `image`, `language` | `{ looks_valid, kind, reason }` |

## Citizen — claims (online + sync) · M4

| Method | Path | Body | Returns |
|---|---|---|---|
| `PUT` | `/api/claims/{claim_id}` | Claim JSON | `200 { claim_id, status }` — **upsert**, safe to repeat |
| `PUT` | `/api/claims/{claim_id}/media/{kind}?media_id=&sha256=` | raw bytes | `200 { media_id, stored: true }` — no-op if hash already stored |
| `GET` | `/api/claims/{claim_id}/status` | — | `{ status, relief_server_inr, final_pdf_url }` |

`kind` ∈ `audio`, `photo`, `proof`.

## Officials · M5

Auth: `Authorization: Bearer <token>` (dev: `OFFICIALS_DEV_TOKEN`; prod: Google Identity).

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/officials/claims?district=&block=&status=&page=` | Sorted by `filed_at_device` |
| `GET` | `/api/officials/claims/{claim_id}` | Full claim + signed media URLs + AI checks |
| `POST` | `/api/officials/claims/{claim_id}/decision` | `{ "decision": "approve" \| "field_visit" \| "reject", "note": "" }` |
| `POST` | `/api/officials/ask` | `{ "question": "How many pending claims in Danapur?" }` → `{ sql, columns, rows }` |

## Errors

```json
{ "error": { "code": "invalid_claim", "message": "losses.crops[0].hectares must be ≥ 0" } }
```
| Code | HTTP |
|---|---|
| `invalid_claim` | 422 |
| `not_found` | 404 |
| `unauthorized` | 401 |
| `ai_unavailable` | 503 — phone should fall back to guided taps |
