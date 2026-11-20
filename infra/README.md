# ☁️ infra/ — Owner: 🖥️ M5 (migrations: 🗄️ M4)

| Folder | Owner | What goes here |
|---|---|---|
| `migrations/` | M4 | SQL migrations for AlloyDB (`001_init.sql`, …) |
| `sql/` | M5 | `readonly_role.sql` — the read-only role and `claims_view` used by "Ask your claims" |
| `cloudrun/` | M5 | Deploy script / service config for Cloud Run in `asia-south1` (Mumbai) |

Deployment design: [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md#9-deployment)
