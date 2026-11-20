# 🧠 services/ — business logic

| Planned file | Owner | Does |
|---|---|---|
| `gemini.py` | 🤖 M3 | Voice → claim JSON, follow-up questions, server recheck of offline claims |
| `tts.py` | 🤖 M3 | Cloud Text-to-Speech in 6 languages |
| `vision.py` | 🤖 M3 | Check substitute proof and damage photos |
| `relief.py` | 🗄️ M4 | Relief amount from SDRF rates — must match the phone's `estimate.js` |
| `pdf.py` | 🗄️ M4 | Final relief form PDF + claim ID + QR (all 6 scripts) |
| `storage.py` | 🗄️ M4 | Cloud Storage uploads, signed URLs |
| `nl_sql.py` | 🖥️ M5 | "Ask your claims" — question → SELECT-only SQL on the read-only role |
