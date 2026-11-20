/**
 * Mesh "lite" helper for Member 4's app: seal a claim on a phone with no network, so a
 * neighbour's phone can carry it (QR code or file) and deliver it when it has signal.
 * Only Member 3's server can open it; any change on the way makes delivery fail.
 *
 *   // while online, once: keep the server's key for offline use
 *   const key = await fetchMeshKey("http://localhost:8002");   // store it (IndexedDB/localStorage)
 *
 *   // phone A, offline
 *   const envelope = await sealClaim({ consent: true, consent_text_version: "v1", language: "bn",
 *                                      fields: { name: "...", village: "..." }, submit: true }, key);
 *   const { text, fitsInQr } = envelopeText(envelope);  // QR code if it fits, else share as a file
 *
 *   // phone B, back online
 *   const { receipt } = await deliverEnvelope("http://localhost:8002", envelope);
 *   // carry receipt back to phone A (or phone A asks later): await fetchReceipt(base, envelope.claim_id)
 *   await verifyReceipt(receipt, key)   // true -> show "Your claim reached the relief office"
 *
 * Payload fields: consent (required, true), consent_text_version, language, fields (Member 2's
 * claim fields), audio {data: base64, content_type}, photos [{data: base64, content_type, lat,
 * lon, taken_at}], submit. Works in browsers and Node 18+ (WebCrypto).
 */

const ALG = "RSA-OAEP-256+A256GCM";
// A QR code holds at most ~2,950 bytes; keep a margin. Photos and voice notes need the file route.
export const QR_MAX_CHARS = 2800;

const subtle = globalThis.crypto.subtle;
const enc = new TextEncoder();

function toB64(bytes) {
  let s = "";
  const b = new Uint8Array(bytes);
  for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode(...b.subarray(i, i + 0x8000));
  return btoa(s);
}

function fromB64(text) {
  return Uint8Array.from(atob(text), (c) => c.charCodeAt(0));
}

/** The header is bound to the ciphertext (AES-GCM additional data): it cannot be altered. */
export function headerBytes(env) {
  return enc.encode(`${env.v}|${env.claim_id}|${env.created_at}|${env.priority}`);
}

/** Server key and limits. Fetch while online and keep it: phone A needs it with no network. */
export async function fetchMeshKey(base, fetchImpl = fetch) {
  const r = await fetchImpl(`${base}/mesh/public-key`);
  if (!r.ok) throw new Error(`mesh key: HTTP ${r.status}`);
  return r.json();
}

/** Seal a claim payload with the server's public key. Returns the envelope (plain JSON). */
export async function sealClaim(payload, key, { priority = "normal", claimId, createdAt } = {}) {
  if (payload?.consent !== true) throw new Error("payload.consent must be true (the claimant agreed)");
  if (!(key.priorities || ["urgent", "normal"]).includes(priority)) throw new Error(`bad priority ${priority}`);
  const env = {
    v: 1,
    claim_id: claimId || globalThis.crypto.randomUUID(),
    created_at: createdAt || new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
    priority,
    alg: ALG,
  };
  const plain = enc.encode(JSON.stringify(payload));
  if (key.max_payload_bytes && plain.length > key.max_payload_bytes) {
    throw new Error(`claim is ${plain.length} bytes; the limit is ${key.max_payload_bytes}. Use a smaller photo.`);
  }
  const rsa = await subtle.importKey("spki", fromB64(key.public_key_spki), { name: "RSA-OAEP", hash: "SHA-256" },
                                     false, ["encrypt"]);
  const aes = await subtle.generateKey({ name: "AES-GCM", length: 256 }, true, ["encrypt"]);
  const iv = globalThis.crypto.getRandomValues(new Uint8Array(12));
  const ct = await subtle.encrypt({ name: "AES-GCM", iv, additionalData: headerBytes(env) }, aes, plain);
  const wrapped = await subtle.encrypt({ name: "RSA-OAEP" }, rsa, await subtle.exportKey("raw", aes));
  return { ...env, key: toB64(wrapped), iv: toB64(iv), ct: toB64(ct) };
}

/** Text to put in a QR code or a .claim.json file, and whether it fits in one QR code. */
export function envelopeText(envelope) {
  const text = JSON.stringify(envelope);
  return { text, fitsInQr: text.length <= QR_MAX_CHARS };
}

/** Phone B: read an envelope from a scanned QR code or an opened file. */
export function parseEnvelope(text) {
  const env = JSON.parse(text);
  if (env?.v !== 1 || env?.alg !== ALG || !env.claim_id || !env.ct) throw new Error("not an Aapke Liye claim envelope");
  return env;
}

/** Phone B, online: deliver. 503 = keep the envelope and retry later. */
export async function deliverEnvelope(base, envelope, fetchImpl = fetch) {
  const r = await fetchImpl(`${base}/mesh/envelopes`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(envelope),
  });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) {
    const err = new Error(body.detail || `HTTP ${r.status}`);
    err.status = r.status;
    err.retry = r.status === 503 || r.status === 409;   // try again later; others will never work
    throw err;
  }
  return body;            // {status, receipt}
}

/** Anyone online: has this claim arrived? null if not yet. */
export async function fetchReceipt(base, claimId, fetchImpl = fetch) {
  const r = await fetchImpl(`${base}/mesh/receipts/${encodeURIComponent(claimId)}`);
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`receipt: HTTP ${r.status}`);
  return r.json();
}

/** Check the receipt really came from the server. Needs Ed25519 in WebCrypto (current browsers). */
export async function verifyReceipt(receipt, key) {
  try {
    const pub = await subtle.importKey("raw", fromB64(key.receipt_public_key), { name: "Ed25519" }, false, ["verify"]);
    return await subtle.verify({ name: "Ed25519" }, pub, fromB64(receipt.signature),
                               enc.encode(`${receipt.claim_id}|${receipt.received_at}`));
  } catch {
    return false;          // browser without Ed25519: treat as not verified
  }
}
