# 🔌 api/ — HTTP routes

| Planned file | Owner | Routes |
|---|---|---|
| `claims.py` | 🗄️ M4 | `PUT /claims/{id}` (upsert), `PUT /claims/{id}/media/{kind}`, `GET /claims/{id}/status`, `GET /health` |
| `voice.py` | 🤖 M3 | `POST /voice/extract`, `POST /voice/speak`, `POST /vision/check-proof` |
| `officials.py` | 🖥️ M5 | `GET /officials/claims`, `POST /officials/claims/{id}/decision`, `POST /officials/ask` |
