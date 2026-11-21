// src/utils/mesh.ts
// Member 3 Mesh "lite" client implementation using WebCrypto
// Seals claims on phones with no network so neighbour devices can carry and deliver them.

export const QR_MAX_CHARS = 2800;
const ALG = 'RSA-OAEP-256+A256GCM';
const MESH_KEY_STORAGE = 'aapke_liye_mesh_public_key';

export interface MeshPublicKey {
  public_key_spki: string;
  receipt_public_key: string;
  max_payload_bytes?: number;
  priorities?: string[];
}

export interface MeshEnvelope {
  v: number;
  claim_id: string;
  created_at: string;
  priority: 'urgent' | 'normal';
  alg: string;
  key: string; // RSA-wrapped AES key (base64)
  iv: string;  // AES-GCM IV (base64)
  ct: string;  // Ciphertext (base64)
}

export interface MeshReceipt {
  claim_id: string;
  received_at: string;
  signature: string;
}

const subtle = globalThis.crypto?.subtle;
const enc = new TextEncoder();

function toB64(bytes: ArrayBuffer | Uint8Array): string {
  let s = '';
  const b = new Uint8Array(bytes);
  for (let i = 0; i < b.length; i += 0x8000) {
    s += String.fromCharCode(...b.subarray(i, i + 0x8000));
  }
  return btoa(s);
}

function fromB64(text: string): Uint8Array {
  return Uint8Array.from(atob(text), (c) => c.charCodeAt(0));
}

/** The header is bound to the ciphertext (AES-GCM additional data): it cannot be altered. */
export function headerBytes(env: { v: number; claim_id: string; created_at: string; priority: string }): Uint8Array {
  return enc.encode(`${env.v}|${env.claim_id}|${env.created_at}|${env.priority}`);
}

/** Get cached server public key for offline sealing */
export function getCachedMeshKey(): MeshPublicKey | null {
  try {
    const raw = localStorage.getItem(MESH_KEY_STORAGE);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

/** Fetch server key and limits while online, and cache for offline use */
export async function fetchMeshKey(base: string = 'http://localhost:8002'): Promise<MeshPublicKey> {
  const r = await fetch(`${base}/mesh/public-key`);
  if (!r.ok) throw new Error(`mesh key: HTTP ${r.status}`);
  const key: MeshPublicKey = await r.json();
  try {
    localStorage.setItem(MESH_KEY_STORAGE, JSON.stringify(key));
  } catch {
    // ignore
  }
  return key;
}

/** Seal a claim payload with the server's public key. Returns the envelope (plain JSON). */
export async function sealClaim(
  payload: any,
  key: MeshPublicKey,
  { priority = 'normal', claimId, createdAt }: { priority?: 'urgent' | 'normal'; claimId?: string; createdAt?: string } = {}
): Promise<MeshEnvelope> {
  if (payload?.consent !== true) throw new Error('payload.consent must be true (the claimant agreed)');
  if (!(key.priorities || ['urgent', 'normal']).includes(priority)) throw new Error(`bad priority ${priority}`);

  const cid = (claimId && /^[0-9a-fA-F-]{16,64}$/.test(claimId)) ? claimId : globalThis.crypto.randomUUID();
  const env = {
    v: 1,
    claim_id: cid,
    created_at: createdAt || new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'),
    priority,
    alg: ALG,
  };

  const plain = enc.encode(JSON.stringify(payload));
  if (key.max_payload_bytes && plain.length > key.max_payload_bytes) {
    throw new Error(`claim is ${plain.length} bytes; limit is ${key.max_payload_bytes}. Use a smaller photo.`);
  }

  const rsa = await subtle.importKey(
    'spki',
    fromB64(key.public_key_spki),
    { name: 'RSA-OAEP', hash: 'SHA-256' },
    false,
    ['encrypt']
  );
  const aes = await subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, ['encrypt']);
  const iv = globalThis.crypto.getRandomValues(new Uint8Array(12));
  const ct = await subtle.encrypt({ name: 'AES-GCM', iv, additionalData: headerBytes(env) }, aes, plain);
  const wrapped = await subtle.encrypt({ name: 'RSA-OAEP' }, rsa, await subtle.exportKey('raw', aes));

  return { ...env, key: toB64(wrapped), iv: toB64(iv), ct: toB64(ct) };
}

/** Text to put in a QR code or a .claim.json file, and whether it fits in one QR code. */
export function envelopeText(envelope: MeshEnvelope): { text: string; fitsInQr: boolean } {
  const text = JSON.stringify(envelope);
  return { text, fitsInQr: text.length <= QR_MAX_CHARS };
}

/** Phone B: read an envelope from a scanned QR code or an opened file. */
export function parseEnvelope(text: string): MeshEnvelope {
  const env = JSON.parse(text);
  if (env?.v !== 1 || env?.alg !== ALG || !env.claim_id || !env.ct) {
    throw new Error('Not an Aapke Liye sealed claim envelope');
  }
  return env as MeshEnvelope;
}

/** Phone B, online: deliver to Member 3. 503 = keep the envelope and retry later. */
export async function deliverEnvelope(
  base: string = 'http://localhost:8002',
  envelope: MeshEnvelope
): Promise<{ status: string; receipt: MeshReceipt }> {
  const r = await fetch(`${base}/mesh/envelopes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(envelope),
  });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) {
    const err: any = new Error(body.detail || `HTTP ${r.status}`);
    err.status = r.status;
    err.retry = r.status === 503 || r.status === 409;
    throw err;
  }
  return body;
}

/** Anyone online: has this claim arrived? null if not yet. */
export async function fetchReceipt(
  base: string = 'http://localhost:8002',
  claimId: string
): Promise<MeshReceipt | null> {
  const r = await fetch(`${base}/mesh/receipts/${encodeURIComponent(claimId)}`);
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`receipt: HTTP ${r.status}`);
  return r.json();
}

/** Check the receipt really came from the server. Needs Ed25519 in WebCrypto. */
export async function verifyReceipt(receipt: MeshReceipt, key: MeshPublicKey): Promise<boolean> {
  try {
    const pub = await subtle.importKey(
      'raw',
      fromB64(key.receipt_public_key),
      { name: 'Ed25519' },
      false,
      ['verify']
    );
    return await subtle.verify(
      { name: 'Ed25519' },
      pub,
      fromB64(receipt.signature),
      enc.encode(`${receipt.claim_id}|${receipt.received_at}`)
    );
  } catch {
    return false;
  }
}
