# 🖼️ screens/ — Owner: 🎨 M1

One module per step of the citizen flow (step numbers match the workflow diagram).

| Planned file | Step | Does |
|---|---|---|
| `language.js` | 1 | Pick 1 of 6 languages |
| `consent.js` | 2 | Spoken consent before any data is collected |
| `capture.js` | 2 | Record voice, take photos, save GPS + time |
| `followup.js` | 4 | Play Gemini's follow-up question, record the answer |
| `guided.js` | 3b | Offline guided taps + prerecorded prompts → claim JSON |
| `readback.js` | 5 | Read the claim back (TTS online / clips offline), user confirms |
| `documents.js` | 6 | Documents lost? → photograph substitute proof |
| `done.js` | 7 | Claim ID, QR, PDF, sync badge |
