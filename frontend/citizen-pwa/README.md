# 📱 Citizen PWA

**Owners:** 🎨 **M1** (screens, i18n, audio prompts) · 📴 **M2** (offline, sync, service worker)

The free, voice-first app citizens use to file a relief claim — works online and fully offline.
Planned stack: Vanilla JS + Vite, Service Worker, IndexedDB, MediaRecorder.

## Layout

| Folder | Owner | What goes here |
|---|---|---|
| `public/` | M2 | `manifest.webmanifest`, `sw.js` (service worker), icons |
| `public/audio/prompts/` | M1 | Prerecorded voice prompts for the offline flow, per language |
| `src/screens/` | M1 | One module per screen in the citizen flow |
| `src/offline/` | M2 | IndexedDB, network test, sync engine, SDRF estimator |
| `src/api/` | M2 | Client for the backend API |
| `src/i18n/` | M1 | Text for the 6 languages |

See [`docs/OFFLINE_SYNC.md`](../../docs/OFFLINE_SYNC.md) and [`docs/TEAM.md`](../../docs/TEAM.md).
