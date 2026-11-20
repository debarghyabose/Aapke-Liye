// Offline upload queue for the Aapke Liye app (browser / PWA).
// Claims are saved in IndexedDB first, then sent to POST /sync when the network returns.
// Each claim keeps the same client_uuid across retries, so the server never creates duplicates.

const DB_NAME = "aapke-liye";
const STORE = "outbox";
const API_BASE = "http://localhost:8000";

function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE, { keyPath: "client_uuid" });
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function withStore(mode, fn) {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, mode);
    const out = fn(tx.objectStore(STORE));
    tx.oncomplete = () => resolve(out && out.result !== undefined ? out.result : out);
    tx.onerror = () => reject(tx.error);
  });
}

// Save a claim locally. photos: array of Blob/File.
export async function enqueueClaim({ phone, lat, lon, photos }) {
  const claim = {
    client_uuid: crypto.randomUUID(),
    phone,
    lat,
    lon,
    photos,
    attempts: 0,
    created_at: Date.now(),
  };
  await withStore("readwrite", (s) => s.put(claim));
  flushQueue();
  return claim.client_uuid;
}

async function sendClaim(claim) {
  const form = new FormData();
  form.append("client_uuid", claim.client_uuid);
  form.append("phone", claim.phone);
  if (claim.lat != null) form.append("device_lat", claim.lat);
  if (claim.lon != null) form.append("device_lon", claim.lon);
  claim.photos.forEach((p, i) => form.append("photos", p, `photo-${i}.jpg`));
  const res = await fetch(`${API_BASE}/sync`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`sync failed: ${res.status}`);
  return res.json();
}

let flushing = false;

// Try to send everything in the outbox; failed claims stay queued and retry with backoff.
export async function flushQueue() {
  if (flushing || !navigator.onLine) return;
  flushing = true;
  try {
    const claims = await withStore("readonly", (s) => s.getAll());
    for (const claim of claims) {
      try {
        const result = await sendClaim(claim);
        await withStore("readwrite", (s) => s.delete(claim.client_uuid));
        window.dispatchEvent(new CustomEvent("claim-synced", { detail: result }));
      } catch (err) {
        claim.attempts += 1;
        await withStore("readwrite", (s) => s.put(claim));
        const delay = Math.min(60000, 1000 * 2 ** claim.attempts); // 2s, 4s, 8s ... max 60s
        setTimeout(flushQueue, delay);
        break;
      }
    }
  } finally {
    flushing = false;
  }
}

window.addEventListener("online", flushQueue);
