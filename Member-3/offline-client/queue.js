// Aapke Liye offline queue (Member 3).
//
// Saves every claim step on the phone first (IndexedDB), then sends it to Member 2's
// backend when the network is back. Nothing is lost if the signal drops mid-claim.
//
// Usage for Member 4 (plain ES module, no build step):
//
//   import { createOfflineQueue } from "./queue.js";
//   const q = createOfflineQueue({ apiBase: "http://localhost:8000" });
//   const localId = await q.startClaim({ language: "hi", disaster_type: "flood",
//                                        consent: true, consent_text_version: "v1" });
//   await q.addAudio(localId, audioBlob, "recording.webm");
//   await q.addPhoto(localId, photoBlob, { lat, lon, taken_at: new Date().toISOString() });
//   q.on("change", async () => render(await q.list())); // any job or claim changed
//   q.on("claim-created", ({ localId, claimId }) => ...); // server id now known
//   q.on("failed", ({ job, error }) => ...);              // needs the user's attention
//   const claim = await q.getClaim(localId);              // { claimId, token, ... } once online
//
// Steps run in order per claim: create claim -> audio -> photos. Uploads wait until the
// claim exists on the server. Retries are safe: Member 2 ignores a photo uploaded twice.

const DB_NAME = "aapke-liye-offline";
const DB_VERSION = 1;
const MAX_BACKOFF_MS = 5 * 60 * 1000;

// ---------------------------------------------------------------- IndexedDB helpers

function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      db.createObjectStore("claims", { keyPath: "localId" });
      const jobs = db.createObjectStore("jobs", { keyPath: "id", autoIncrement: true });
      jobs.createIndex("localId", "localId");
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function tx(db, stores, mode, fn) {
  return new Promise((resolve, reject) => {
    const t = db.transaction(stores, mode);
    let result;
    Promise.resolve(fn(t)).then((r) => (result = r));
    t.oncomplete = () => resolve(result);
    t.onerror = () => reject(t.error);
    t.onabort = () => reject(t.error);
  });
}

const req2promise = (r) => new Promise((res, rej) => { r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); });

// ---------------------------------------------------------------- errors

class RetryLater extends Error {
  constructor(message, retryAfterMs) { super(message); this.retryAfterMs = retryAfterMs; }
}
class Permanent extends Error {}

function retryAfterMs(res) {
  const s = Number(res.headers.get("Retry-After"));
  return Number.isFinite(s) && s > 0 ? s * 1000 : undefined;
}

async function detail(res) {
  try {
    const d = (await res.json()).detail;
    if (typeof d === "string") return d;
    // FastAPI validation errors: [{loc: [..., "lat"], msg: "..."}]
    if (Array.isArray(d)) return d.map((e) => `${(e.loc || []).slice(-1)[0] || "input"}: ${e.msg}`).join("; ");
    return `HTTP ${res.status}`;
  } catch { return `HTTP ${res.status}`; }
}

// ---------------------------------------------------------------- the queue

export function createOfflineQueue({ apiBase, fetchImpl = (...a) => fetch(...a) } = {}) {
  if (!apiBase) throw new Error("createOfflineQueue: apiBase is required");
  apiBase = apiBase.replace(/\/+$/, "");
  const dbPromise = openDb();
  const listeners = {};
  let flushing = false;
  let timer = null;

  const emit = (event, data) => (listeners[event] || []).forEach((cb) => { try { cb(data); } catch (e) { console.error(e); } });
  const changed = () => emit("change");

  async function call(path, { method = "POST", token, json, form } = {}) {
    const headers = {};
    if (token) headers["X-Claim-Token"] = token;
    let body;
    if (json) { headers["Content-Type"] = "application/json"; body = JSON.stringify(json); }
    if (form) body = form;
    let res;
    try {
      res = await fetchImpl(apiBase + path, { method, headers, body });
    } catch (e) {
      throw new RetryLater("No connection to the server");
    }
    if (res.ok) return res.json();
    if (res.status === 408 || res.status === 429 || res.status >= 500) {
      throw Object.assign(new RetryLater(await detail(res), retryAfterMs(res)), { status: res.status });
    }
    throw Object.assign(new Permanent(await detail(res)), { status: res.status });
  }

  // One job = one request. Returns extra jobs to add after it, if any.
  async function runJob(job, claim) {
    if (job.kind === "create") {
      const c = await call("/claims", { json: job.payload });
      claim.claimId = c.id;
      claim.token = c.claim_token;   // kept on this device only; needed for every later call
      claim.state = "created";
      emit("claim-created", { localId: claim.localId, claimId: c.id });
      return [];
    }
    if (job.kind === "audio") {
      const form = new FormData();
      form.append("audio", job.blob, job.payload.filename || "recording.webm");
      try {
        await call(`/claims/${claim.claimId}/audio`, { token: claim.token, form });
        return [];
      } catch (e) {
        // 503 = Member 2 kept the recording but Member 1's AI is down: ask it to retry later.
        if (e instanceof RetryLater && e.status === 503) {
          return [{ kind: "audio-retry", payload: {}, delayMs: e.retryAfterMs ?? 60000 }];
        }
        throw e;
      }
    }
    if (job.kind === "audio-retry") {
      try { await call(`/claims/${claim.claimId}/audio/retry`, { token: claim.token }); }
      catch (e) { if (!(e instanceof Permanent && e.status === 409)) throw e; } // 409 = nothing pending
      return [];
    }
    if (job.kind === "photo") {
      const form = new FormData();
      form.append("photo", job.blob, "photo.jpg");
      for (const k of ["lat", "lon", "taken_at"]) {
        if (job.payload[k] !== undefined && job.payload[k] !== null) form.append(k, String(job.payload[k]));
      }
      await call(`/claims/${claim.claimId}/photos`, { token: claim.token, form });
      return [];
    }
    throw new Permanent(`Unknown job kind ${job.kind}`);
  }

  async function addJob(localId, kind, payload, blob) {
    const db = await dbPromise;
    await tx(db, ["jobs"], "readwrite", (t) => t.objectStore("jobs").add({
      localId, kind, payload, blob: blob || null, state: "queued",
      attempts: 0, nextAttemptAt: 0, error: null, createdAt: Date.now(),
    }));
    changed();
    flush();
  }

  async function flush({ force = false } = {}) {
    if (flushing) return;
    flushing = true;
    clearTimeout(timer);
    try {
      const db = await dbPromise;
      const [claims, jobs] = await tx(db, ["claims", "jobs"], "readonly", async (t) => [
        await req2promise(t.objectStore("claims").getAll()),
        await req2promise(t.objectStore("jobs").getAll()),
      ]);
      const byId = Object.fromEntries(claims.map((c) => [c.localId, c]));
      const blocked = new Set(); // claims with an earlier step still waiting
      let soonest = Infinity;

      for (const job of jobs.sort((a, b) => a.id - b.id)) {
        if (job.state !== "queued" || blocked.has(job.localId)) continue;
        const claim = byId[job.localId];
        if (!claim) continue;
        if (job.kind !== "create" && !claim.claimId) { blocked.add(job.localId); continue; }
        if (!force && job.nextAttemptAt > Date.now()) {
          blocked.add(job.localId); soonest = Math.min(soonest, job.nextAttemptAt); continue;
        }

        let extra = [];
        try {
          extra = await runJob(job, claim);
          job.state = "done"; job.error = null; job.blob = null; // free the space once sent
        } catch (e) {
          job.attempts += 1;
          job.error = e.message;
          if (e instanceof Permanent) {
            job.state = "failed";
            emit("failed", { job: { ...job, blob: undefined }, error: e.message });
          } else {
            const backoff = Math.min(MAX_BACKOFF_MS, 2000 * 2 ** (job.attempts - 1));
            job.nextAttemptAt = Date.now() + (e.retryAfterMs ?? backoff * (0.8 + Math.random() * 0.4));
            soonest = Math.min(soonest, job.nextAttemptAt);
          }
          blocked.add(job.localId);
        }
        await tx(db, ["claims", "jobs"], "readwrite", (t) => {
          t.objectStore("jobs").put(job);
          t.objectStore("claims").put(claim);
          for (const x of extra) {
            t.objectStore("jobs").add({ localId: job.localId, kind: x.kind, payload: x.payload, blob: null,
              state: "queued", attempts: 0, nextAttemptAt: Date.now() + (x.delayMs || 0),
              error: null, createdAt: Date.now() });
            soonest = Math.min(soonest, Date.now() + (x.delayMs || 0));
          }
        });
        changed();
      }
      if (soonest < Infinity) timer = setTimeout(flush, Math.max(500, soonest - Date.now()));
    } finally {
      flushing = false;
    }
  }

  window.addEventListener("online", () => flush({ force: true }));

  return {
    /** Start a claim offline. Returns a local id usable right away. */
    async startClaim({ language, disaster_type, consent, consent_text_version }) {
      if (consent !== true) throw new Error("Consent is required before starting a claim");
      const localId = crypto.randomUUID();
      const db = await dbPromise;
      await tx(db, ["claims"], "readwrite", (t) => t.objectStore("claims").add({
        localId, claimId: null, token: null, state: "local", createdAt: Date.now(),
      }));
      await addJob(localId, "create", { language, disaster_type, consent, consent_text_version });
      return localId;
    },
    /** Queue a voice recording (Blob) for this claim. */
    addAudio: (localId, blob, filename) => addJob(localId, "audio", { filename }, blob),
    /** Queue a photo (Blob) with optional { lat, lon, taken_at (ISO 8601) }. */
    addPhoto: (localId, blob, meta = {}) => addJob(localId, "photo", meta, blob),
    /** Local claim record: claimId and token are filled once the server has it. */
    async getClaim(localId) {
      const db = await dbPromise;
      return tx(db, ["claims"], "readonly", (t) => req2promise(t.objectStore("claims").get(localId)));
    },
    /** Everything in the queue, for showing progress. Photo/audio bytes are left out. */
    async list() {
      const db = await dbPromise;
      const [claims, jobs] = await tx(db, ["claims", "jobs"], "readonly", async (t) => [
        await req2promise(t.objectStore("claims").getAll()),
        await req2promise(t.objectStore("jobs").getAll()),
      ]);
      return {
        claims: claims.map(({ token, ...c }) => c), // never expose the token to the UI list
        jobs: jobs.map(({ blob, ...j }) => j),
        pending: jobs.filter((j) => j.state === "queued").length,
        failed: jobs.filter((j) => j.state === "failed").length,
      };
    },
    /** Send now, ignoring backoff timers (e.g. a "Retry now" button). */
    flush: (opts) => flush(opts),
    on(event, cb) { (listeners[event] ||= []).push(cb); return () => { listeners[event] = listeners[event].filter((x) => x !== cb); }; },
  };
}
