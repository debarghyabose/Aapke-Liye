# Contributing to Aapke Liye

## Workflow

1. **Pick an issue** from the project board (or open one with the templates).
2. **Branch** from `main`: `m<member-number>/<short-topic>` — e.g. `m3/followup-questions`.
3. **Commit** small, clear commits: `feat(sync): retry every 30s while app is open`.
   Prefixes: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`.
4. **Open a PR** into `main` using the PR template. CI must be green.
5. **One approval** from a teammate is required. CODEOWNERS adds the right reviewer automatically.
6. **Squash-merge** and delete the branch.

## Golden rules

- 🔗 **Never change `shared/schemas/claim.schema.json` alone.** Open a PR tagged `contract` and get M1, M2, M3 and M4 to approve — every part of the app depends on it.
- 📴 **Offline is not an edge case.** Every citizen-side feature must say what happens with no network.
- 💾 **Phone saves first.** Nothing is sent before it is in IndexedDB.
- 🔁 **Every write is idempotent** (upsert by `claim_id`).
- 🔐 **No secrets in git.** Use `.env` (copied from `.env.example`).
- 🪪 **No full ID numbers.** Store last 4 digits only.

## Code style

| Area | Tool |
|---|---|
| Python | `ruff` (lint + format), type hints, `pytest` |
| JS | Prettier defaults, ES modules, no framework in the PWA |
| Docs | Markdown, keep `docs/` in sync with behaviour changes |

## Weekly rhythm

- **Mon** — 20-min planning: each member picks the week's issues.
- **Wed** — integration check: run the full phone → server → dashboard flow.
- **Fri** — demo + update `docs/WORK_PLAN.md` progress.
