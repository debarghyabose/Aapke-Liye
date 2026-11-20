# 🖥️ Officials Dashboard — Owner: 🖥️ M5

The paid side: officials review, query and decide on claims. Served as static files by the same FastAPI service at `/officials`.

| Planned file | Does |
|---|---|
| `index.html` | Claim list with filters (district, block, status), sorted by original filing time |
| `claim.html` | Claim detail — form, photos, audio, AI checks, map pin, Approve / Flag for field visit |
| `ask.js` | "Ask your claims" — plain-language question → read-only SQL → table |
| `styles.css` | Dashboard styles |
