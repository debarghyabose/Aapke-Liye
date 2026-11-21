// src/api/client.ts
// Talks to Member 2's backend (which calls Member 1's claim AI and Member 3's photo checks).
//
// - VITE_API_URL set   -> live mode: every call goes to the real backend.
// - VITE_API_URL unset -> demo mode: ./mockClient.ts answers with sample data, so the
//                         screens can be shown with no backend running.
//
// When offline, transparently falls back to IndexedDB local claim storage & queue.
import * as mock from './mockClient';
// Member 3's sealing helper (WebCrypto), used as-is so both sides share one format.
import * as mesh from '../../../../Member-3/offline-client/mesh.js';
import {
  ClaimCreate,
  ClaimCreated,
  ClaimFields,
  ClaimOut,
  Household,
  PhotoOut,
  PhotoVerification,
  ReliefScheme,
  ReliefSummary,
  SealedClaimEnvelope,
  StaffClaimOut,
  StatusOut,
  VaultDocument,
} from '../types/api';
import {
  queueOfflineItem,
  saveOfflineClaim,
  getOfflineClaim,
  saveLocalHousehold,
  getLocalHousehold,
  getAllLocalHouseholds,
  saveMeshEnvelope,
  getMeshEnvelopes as getStoredMeshEnvelopes,
  removeMeshEnvelope,
} from '../utils/indexedDB';

const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
export const DEMO_MODE = !API_URL;

// ---------- error type the pages can show ----------

export class ApiError extends Error {
  status: number;
  detail: any;
  constructor(status: number, message: string, detail?: any) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

/** A user-safe sentence for any error thrown by this client. */
export function errorText(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 422 && e.detail?.missing_fields) {
      const missing = [...(e.detail.missing_fields || []), ...Object.keys(e.detail.invalid_fields || {})];
      return `${e.detail.message || 'Some details are missing'}: ${missing.join(', ')}`;
    }
    return e.message;
  }
  if (e instanceof TypeError) return 'Cannot reach the Aapke Liye server. Check your connection or offline mode.';
  return 'Something went wrong. Please try again.';
}

// ---------- claim tokens (kept on this device only) ----------

const TOKENS_KEY = 'aapke_liye_claim_tokens';

function readTokens(): Record<string, string> {
  try {
    return JSON.parse(localStorage.getItem(TOKENS_KEY) || '{}');
  } catch {
    return {};
  }
}

export function saveToken(claimId: string, token: string) {
  try {
    localStorage.setItem(TOKENS_KEY, JSON.stringify({ ...readTokens(), [claimId]: token }));
  } catch {
    // private mode: the token lives only in memory for this visit
  }
  memoryTokens[claimId] = token;
}

const memoryTokens: Record<string, string> = {};

function tokenFor(claimId: string): string {
  const t = memoryTokens[claimId] || readTokens()[claimId];
  if (!t) {
    // If it's an offline draft, synthesize a local token
    if (claimId.startsWith('offline-')) return `local-token-${claimId}`;
    throw new ApiError(404, 'This claim was filed on another device. Open it on the phone that filed it.');
  }
  return t;
}

/** Claim IDs filed from this device, newest last. */
export function claimsOnThisDevice(): string[] {
  return Object.keys({ ...readTokens(), ...memoryTokens });
}

// ---------- staff key (officials' screen) ----------

const STAFF_KEY = 'aapke_liye_staff_key';

export function getStaffKey(): string {
  try {
    return sessionStorage.getItem(STAFF_KEY) || '';
  } catch {
    return '';
  }
}

export function setStaffKey(key: string) {
  try {
    sessionStorage.setItem(STAFF_KEY, key.trim());
  } catch {
    // ignore
  }
}

// ---------- HTTP ----------

async function request<T>(
  path: string,
  init: RequestInit & {
    claimId?: string;
    staff?: boolean;
    householdId?: string;
    householdToken?: string;
  } = {}
): Promise<T> {
  const headers: Record<string, string> = { ...(init.headers as Record<string, string>) };
  if (init.claimId) headers['X-Claim-Token'] = tokenFor(init.claimId);
  if (init.householdToken) {
    headers['X-Household-Token'] = init.householdToken;
  } else if (init.householdId) {
    const hhTok = householdTokenFor(init.householdId);
    if (hhTok) headers['X-Household-Token'] = hhTok;
  }
  if (init.staff) headers['X-Staff-Key'] = getStaffKey();
  if (init.body && typeof init.body === 'string') headers['Content-Type'] = 'application/json';

  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail: any = null;
    try {
      detail = (await res.json()).detail;
    } catch {
      // not JSON
    }
    const message =
      typeof detail === 'string'
        ? detail
        : detail?.message ||
          (res.status === 401 ? 'Staff key missing or wrong.' : `Request failed (HTTP ${res.status}).`);
    throw new ApiError(res.status, message, detail);
  }
  const type = res.headers.get('content-type') || '';
  return (type.includes('application/json') ? res.json() : res.blob()) as Promise<T>;
}

// ---------- shape translation: Member 2 -> screens ----------

const photoPreviews: Record<string, string> = {};

async function sha256Hex(file: Blob): Promise<string | null> {
  try {
    const buf = await crypto.subtle.digest('SHA-256', await file.arrayBuffer());
    return Array.from(new Uint8Array(buf))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('');
  } catch {
    return null;
  }
}

function damageLevel(score: number | undefined, detected: boolean | undefined): PhotoVerification['damage_level'] {
  if (score == null) return detected ? 'partial' : 'none';
  if (score >= 0.85) return 'total';
  if (score >= 0.6) return 'severe';
  if (score >= 0.25) return 'partial';
  return 'none';
}

function toPhoto(p: any): PhotoOut {
  const v = p.verification || {};
  const notes: string[] = v.notes || [];
  return {
    id: p.id,
    sha256: p.sha256,
    lat: p.lat,
    lon: p.lon,
    taken_at: p.taken_at,
    url: photoPreviews[p.sha256] || p.url,
    duplicate_of_claim_id: p.duplicate_of_claim_id,
    verification: {
      ...v,
      status: v.status === 'complete' ? 'complete' : 'pending',
      damage_level: v.status === 'complete' ? damageLevel(v.damage_score, v.damage_detected) : undefined,
      gemini_reason:
        v.status === 'complete'
          ? notes.join(' ') || (v.damage_detected ? 'Damage detected in the photo.' : 'No damage detected.')
          : 'Photo saved. Checking is not available right now; it will be checked again.',
      gps_valid: v.gps_ok ?? v.gps_valid,
      time_valid: v.timestamp_ok ?? v.time_valid,
      exif_valid: (v.gps_ok && v.timestamp_ok) ?? v.exif_valid,
      duplicate: v.duplicate,
      before_after: v.before_after,
      comparison: v.comparison,
    },
  } as PhotoOut;
}

const LABELS: Record<string, string> = {
  'house.fully_damaged_plain': 'House fully destroyed',
  'house.fully_damaged_hilly': 'House fully destroyed (hilly area)',
  'house.partially_damaged_pucca': 'Pucca house partly damaged',
  'house.partially_damaged_kutcha': 'Kutcha house partly damaged',
  'house.hut_damaged': 'Hut destroyed',
  'house.cattle_shed': 'Cattle shed',
  'crop.rainfed': 'Rainfed crop',
  'crop.irrigated': 'Irrigated crop',
  'crop.perennial': 'Perennial / orchard crop',
  'livestock.milch_large': 'Cow / buffalo',
  'livestock.milch_small': 'Goat / sheep',
  'livestock.draught_large': 'Bullock / ox',
  'livestock.draught_small': 'Calf / donkey',
  'livestock.poultry': 'Poultry',
  'household.clothing': 'Clothing',
  'household.utensils': 'Household utensils',
  'ex_gratia.death': 'Ex-gratia for loss of life',
};

function label(category: string, item: string): string {
  return LABELS[`${category}.${item}`] || `${category} · ${String(item).replace(/_/g, ' ')}`;
}

function toRelief(r: any): ReliefSummary | null {
  if (!r) return null;
  const breakdown: ReliefScheme[] = [
    ...(r.lines || []).map((l: any) => ({
      scheme_name: 'SDRF',
      category: l.category,
      item: label(l.category, l.item),
      quantity: l.quantity,
      rate: l.rate,
      amount: l.amount,
      description:
        [l.claimed_amount ? `You reported ₹${Math.round(l.claimed_amount).toLocaleString('en-IN')}` : null, l.note]
          .filter(Boolean)
          .join(' · ') || undefined,
    })),
    ...(r.unmatched || []).map((u: any) => ({
      scheme_name: 'Not covered',
      category: u.category,
      item: label(u.category, u.item),
      quantity: u.quantity ?? 1,
      rate: 0,
      amount: 0,
      description: u.reason,
    })),
  ];
  const others: any[] = r.may_also_qualify || [];
  return {
    total: r.total || 0,
    currency: 'INR',
    breakdown,
    matched_schemes: ['SDRF', ...others.map((s) => (s.scheme_code === 'PMAY_G_DISASTER' ? 'PMAY-G' : s.scheme_code))],
    estimate_only: r.estimate_only,
    claimed_total: r.claimed_total ?? null,
    may_also_qualify: others,
  } as ReliefSummary;
}

function toClaim(c: any): ClaimOut {
  const questions: any[] = c.follow_up_questions || [];
  const missing: string[] = c.missing_fields || [];
  return {
    ...c,
    household_id: c.household_id ?? c.fields?.household_id ?? null,
    documents_in_vault: c.documents_in_vault || [],
    fields: {
      ...c.fields,
      is_hilly: c.fields?.is_hilly ?? false,
    },
    follow_up_questions: questions.map((q, i) =>
      typeof q === 'string' ? { field: missing[i] || `question_${i}`, question: q } : q
    ),
    relief: toRelief(c.relief),
    proof_suggestions: (c.proof_suggestions || []).map((p: any) => ({
      document: String(p.document).replace(/_/g, ' '),
      suggestions: p.alternatives || p.suggestions || [],
    })),
    photos: (c.photos || []).map(toPhoto),
    pdf_url: c.pdf_url ? `${API_URL}${c.pdf_url}` : null,
  } as ClaimOut;
}

// ---------- API with full offline-first resilience ----------

/** True when the request never reached the server (no network, server down): only then
 *  is work saved on the phone for later. A server answer (4xx/5xx) is shown to the person. */
function isNetworkError(e: unknown): boolean {
  return !navigator.onLine || e instanceof TypeError;
}

/** Creates the claim on the server only (used by the offline sync, which must not start a
 *  second offline draft if the network drops again). */
export async function createClaimOnServer(payload: ClaimCreate): Promise<ClaimCreated> {
  const c = await request<any>('/claims', { method: 'POST', body: JSON.stringify(payload) });
  saveToken(c.id, c.claim_token);
  const converted = { ...toClaim(c), claim_token: c.claim_token };
  await saveOfflineClaim(converted);
  return converted;
}

export async function createClaim(payload: ClaimCreate): Promise<ClaimCreated> {
  if (DEMO_MODE) return mock.createClaim(payload);

  try {
    const c = await request<any>('/claims', { method: 'POST', body: JSON.stringify(payload) });
    saveToken(c.id, c.claim_token);
    const converted = { ...toClaim(c), claim_token: c.claim_token };
    await saveOfflineClaim(converted);
    return converted;
  } catch (err) {
    if (!isNetworkError(err)) throw err;
    // No network: start the claim on the phone. It is EMPTY until the person speaks or types;
    // nothing is filled in for them. It is created on the server when the signal returns.
    const localId = `offline-${Date.now()}`;
    const now = new Date().toISOString();
    const offlineDraft: ClaimCreated = {
      id: localId,
      claim_token: '',
      language: payload.language,
      disaster_type: payload.disaster_type || null,
      transcript: null,
      fields: {},
      missing_fields: [],
      follow_up_questions: [],
      relief: null,
      proof_suggestions: [],
      status: 'Draft',
      photos: [],
      recordings: [],
      history: [{ status: 'Draft', note: 'Started on this phone with no network', at: now }],
      consent_text_version: payload.consent_text_version,
      consent_given_at: now,
      submitted_at: null,
      created_at: now,
      updated_at: now,
      is_offline_draft: true,
    } as ClaimCreated;
    await saveOfflineClaim(offlineDraft);
    await queueOfflineItem({ type: 'claim_create', claimId: localId, payload });
    return offlineDraft;
  }
}

export async function getClaim(claimId: string): Promise<ClaimOut> {
  if (DEMO_MODE) return mock.getClaim(claimId);

  // Check offline store first if offline ID
  if (claimId.startsWith('offline-')) {
    const local = await getOfflineClaim(claimId);
    if (local) return local;
  }

  try {
    const claim = toClaim(await request<any>(`/claims/${claimId}`, { claimId }));
    await saveOfflineClaim(claim);
    return claim;
  } catch (err) {
    const local = await getOfflineClaim(claimId);
    if (local) return local;
    throw err;
  }
}

export async function uploadAudio(claimId: string, audioBlob: Blob, onProgressMsg?: (m: string) => void): Promise<ClaimOut> {
  if (DEMO_MODE) return mock.uploadAudio(claimId, audioBlob, onProgressMsg);

  if (claimId.startsWith('offline-') || !navigator.onLine) {
    onProgressMsg?.('Saving recording securely on phone storage…');
    await queueOfflineItem({
      type: 'audio',
      claimId,
      blob: audioBlob,
    });
    const local = await getOfflineClaim(claimId);
    if (local) {
      local.transcript = 'Voice note recorded locally on device. Will be processed by Gemini when signal returns.';
      local.recordings = [{ id: Date.now(), status: 'pending' }];
      await saveOfflineClaim(local);
      return local;
    }
  }

  onProgressMsg?.('Understanding what you said…');
  const form = new FormData();
  const ext = (audioBlob.type.split('/')[1] || 'webm').split(';')[0];
  form.append('audio', new File([audioBlob], `recording.${ext}`, { type: audioBlob.type.split(';')[0] || 'audio/webm' }));

  try {
    return toClaim(await request<any>(`/claims/${claimId}/audio`, { method: 'POST', body: form, claimId }));
  } catch (err) {
    if (!isNetworkError(err)) throw err; // e.g. 503 (kept on the server, use Retry) or 415
    await queueOfflineItem({
      type: 'audio',
      claimId,
      blob: audioBlob,
    });
    const local = (await getOfflineClaim(claimId)) || (await getClaim(claimId));
    return local;
  }
}

/** A typed answer, a tapped suggestion, or speech the phone turned into text. */
export async function sendText(claimId: string, text: string): Promise<ClaimOut> {
  if (DEMO_MODE) return mock.getClaim(claimId);

  if (claimId.startsWith('offline-') || !navigator.onLine) {
    await queueOfflineItem({
      type: 'text',
      claimId,
      text,
    });
    const local = await getOfflineClaim(claimId);
    if (local) {
      local.transcript = (local.transcript ? local.transcript + '\n' : '') + text;
      await saveOfflineClaim(local);
      return local;
    }
  }

  try {
    return toClaim(
      await request<any>(`/claims/${claimId}/text`, { method: 'POST', body: JSON.stringify({ text }), claimId })
    );
  } catch (err) {
    if (!isNetworkError(err)) throw err;
    await queueOfflineItem({
      type: 'text',
      claimId,
      text,
    });
    return (await getOfflineClaim(claimId)) || (await getClaim(claimId));
  }
}

export async function retryAudio(claimId: string): Promise<ClaimOut> {
  if (DEMO_MODE) return mock.retryAudio(claimId);
  return toClaim(await request<any>(`/claims/${claimId}/audio/retry`, { method: 'POST', claimId }));
}

export async function uploadPhoto(claimId: string, file: File, lat?: number, lon?: number, takenAt?: string): Promise<ClaimOut> {
  if (DEMO_MODE) return mock.uploadPhoto(claimId, file, lat, lon, takenAt);

  const digest = await sha256Hex(file);
  const localUrl = URL.createObjectURL(file);
  if (digest) photoPreviews[digest] = localUrl;

  if (claimId.startsWith('offline-') || !navigator.onLine) {
    await queueOfflineItem({
      type: 'photo',
      claimId,
      blob: file,
      metadata: { name: file.name, lat, lon, taken_at: takenAt || new Date().toISOString() },
    });
    const local = await getOfflineClaim(claimId);
    if (local) {
      const offlinePhoto: PhotoOut = {
        id: Date.now(),
        sha256: digest || `offline_${Date.now()}`,
        lat: lat ?? null,
        lon: lon ?? null,
        taken_at: takenAt || new Date().toISOString(),
        url: localUrl,
        verification: {
          status: 'pending',
          gemini_reason: 'Saved on this phone. It will be checked when the signal returns.',
        },
      };
      local.photos = [offlinePhoto, ...local.photos];
      await saveOfflineClaim(local);
      return local;
    }
  }

  const form = new FormData();
  form.append('photo', file);
  if (lat != null) form.append('lat', String(lat));
  if (lon != null) form.append('lon', String(lon));
  form.append('taken_at', takenAt || new Date(file.lastModified || Date.now()).toISOString());

  try {
    const claim = toClaim(await request<any>(`/claims/${claimId}/photos`, { method: 'POST', body: form, claimId }));
    await saveOfflineClaim(claim);
    return claim;
  } catch (err) {
    if (!isNetworkError(err)) throw err; // e.g. too large, wrong type, 10-photo limit
    await queueOfflineItem({
      type: 'photo',
      claimId,
      blob: file,
      metadata: { name: file.name, lat, lon, taken_at: takenAt },
    });
    return (await getOfflineClaim(claimId)) || (await getClaim(claimId));
  }
}

export async function reverifyPhoto(claimId: string, photoId: number): Promise<ClaimOut> {
  if (DEMO_MODE) return mock.reverifyPhoto(claimId, photoId);
  return toClaim(await request<any>(`/claims/${claimId}/photos/${photoId}/reverify`, { method: 'POST', claimId }));
}

export async function updateFields(claimId: string, fields: Partial<ClaimFields>): Promise<ClaimOut> {
  if (DEMO_MODE) return mock.updateFields(claimId, fields);

  if (claimId.startsWith('offline-') || !navigator.onLine) {
    const local = await getOfflineClaim(claimId);
    if (local) {
      local.fields = { ...local.fields, ...fields };
      await saveOfflineClaim(local);
      // sent to the server, in order, when the signal returns (relief is calculated there)
      await queueOfflineItem({ type: 'fields', claimId, payload: fields });
      return local;
    }
  }

  const updated = toClaim(
    await request<any>(`/claims/${claimId}`, { method: 'PATCH', body: JSON.stringify({ fields }), claimId })
  );
  await saveOfflineClaim(updated);
  return updated;
}

export async function submitClaim(claimId: string): Promise<ClaimOut> {
  if (DEMO_MODE) return mock.submitClaim(claimId);

  if (claimId.startsWith('offline-') || !navigator.onLine) {
    const local = await getOfflineClaim(claimId);
    if (local) {
      local.history = [
        ...local.history,
        { status: 'Draft', note: 'Waiting for signal: it will be submitted automatically', at: new Date().toISOString() },
      ];
      (local as any).submit_pending = true;
      await saveOfflineClaim(local);
      await queueOfflineItem({ type: 'submit', claimId });
      return local;
    }
  }

  const claim = toClaim(await request<any>(`/claims/${claimId}/submit`, { method: 'POST', claimId }));
  await saveOfflineClaim(claim);
  return claim;
}

/** Downloads the relief form PDF and opens the browser's save dialog. */
export async function getClaimPdf(claimId: string): Promise<Blob> {
  if (!DEMO_MODE && claimId.startsWith('offline-')) {
    throw new Error('The relief form PDF is made when your claim reaches the server. Try again when you have signal.');
  }
  const blob = DEMO_MODE ? await mock.getClaimPdf(claimId) : await request<Blob>(`/claims/${claimId}/pdf`, { claimId });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `relief-claim-${claimId}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
  return blob;
}

export async function getStatus(claimId: string): Promise<StatusOut> {
  if (DEMO_MODE || claimId.startsWith('offline-')) return mock.getStatus(claimId);
  return request<StatusOut>(`/status/${claimId}`, { claimId });
}

// ---------- ready-to-sign letters (Member 1 fills Member 5's legal templates) ----------

export interface DraftLetter {
  doc_type: string;
  title: string;
  text: string;
  missing_fields: string[];
}

export async function draftDocument(claimId: string, docType: string): Promise<DraftLetter> {
  if (claimId.startsWith('offline-') || DEMO_MODE) {
    return {
      doc_type: docType,
      title: `${docType.replace(/_/g, ' ').toUpperCase()} Intimation Form`,
      text: `TO THE COMPETENT DISASTER RELIEF OFFICER\nRef: Claim ${claimId}\nApplicant has suffered severe disaster loss. Generated from offline vault.\nDate: ${new Date().toLocaleDateString()}`,
      missing_fields: [],
    };
  }
  return request<DraftLetter>(`/claims/${claimId}/documents/${docType}`, { method: 'POST', claimId });
}

/** Saves text as a .txt file (opens the browser's save dialog). */
export function saveTextFile(text: string, filename: string) {
  const url = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}

// ---------- officials ----------

export async function getStaffClaim(claimId: string): Promise<StaffClaimOut> {
  if (DEMO_MODE) return mock.getStaffClaim(claimId);
  return toClaim(await request<any>(`/staff/claims/${claimId}`, { staff: true })) as StaffClaimOut;
}

export async function getStaffClaimsList(): Promise<StaffClaimOut[]> {
  if (DEMO_MODE) return mock.getStaffClaimsList();
  const list = await request<any[]>('/staff/claims', { staff: true });
  return list.map((c) => toClaim(c) as StaffClaimOut);
}

export interface Escalation {
  days_pending: number;
  next_step: 'followup_letter' | 'grievance' | 'rti_application' | null;
  reason: string;
  steps_done?: string[];
}

export async function getEscalation(claimId: string): Promise<Escalation> {
  if (DEMO_MODE || claimId.startsWith('offline-')) {
    return {
      days_pending: 1,
      next_step: 'followup_letter',
      reason: 'Claim pending official verification.',
      steps_done: [],
    };
  }
  return request<Escalation>(`/claims/${claimId}/escalation`, { claimId });
}

export async function getDashboard(view: string): Promise<any> {
  if (DEMO_MODE) return mock.getStaffClaimsList();
  return request<any>(`/staff/dashboard/${view}`, { staff: true });
}

export async function updateStaffStatus(claimId: string, status: string, note?: string): Promise<StatusOut | null> {
  if (DEMO_MODE) return null;
  return request<StatusOut>(`/status/${claimId}`, {
    method: 'PUT',
    body: JSON.stringify({ status, note: note || null }),
    staff: true,
  });
}

// ============================================================================
// PRE-DISASTER DOCUMENT VAULT & HOUSEHOLD APIS (MEMBER 2 CONTRACT)
// ============================================================================

const HOUSEHOLD_KEY = 'aapke_liye_current_household';
const HOUSEHOLD_TOKEN_KEY = 'aapke_liye_household_tokens';

function allHouseholdTokens(): Record<string, string> {
  try {
    return JSON.parse(localStorage.getItem(HOUSEHOLD_TOKEN_KEY) || '{}');
  } catch {
    return {};
  }
}

export function householdTokenFor(householdId: string): string {
  return allHouseholdTokens()[householdId] || '';
}

export function saveHouseholdToken(householdId: string, token: string) {
  try {
    const all = allHouseholdTokens();
    all[householdId] = token;
    localStorage.setItem(HOUSEHOLD_TOKEN_KEY, JSON.stringify(all));
  } catch {
    // ignore
  }
}

export function getSavedHouseholdId(): string | null {
  try {
    return localStorage.getItem(HOUSEHOLD_KEY);
  } catch {
    return null;
  }
}

export function saveHouseholdId(id: string) {
  try {
    localStorage.setItem(HOUSEHOLD_KEY, id);
  } catch {
    // ignore
  }
}

// Live mode: the vault lives on Member 2's server. Nothing is reported as saved, deleted or
// linked unless the server confirmed it. Demo mode (no VITE_API_URL) keeps everything on
// this phone with sample data.

function vaultOnline(action: string) {
  if (!navigator.onLine) throw new Error(`Connect to the internet to ${action}.`);
}

export async function registerHousehold(data: {
  head_name: string;
  phone: string;
  village: string;
  district: string;
  state: string;
  ration_card_no?: string;
}): Promise<Household> {
  let id = `HH-DEMO-${Date.now().toString(36).toUpperCase()}`;
  let token = '';
  if (!DEMO_MODE) {
    vaultOnline('set up your family vault');
    // Member 2 POST /households takes no body and returns { household_id, household_token }
    const res = await request<any>('/households', { method: 'POST' });
    id = res.household_id;
    token = res.household_token;
  }
  saveHouseholdId(id);
  if (token) saveHouseholdToken(id, token);
  // Name, phone and village stay on this phone (the server vault stores only documents);
  // they pre-fill claims made with "Use my household".
  const newHousehold: Household = {
    id,
    token,
    head_name: data.head_name,
    phone: data.phone,
    village: data.village,
    district: data.district,
    state: data.state,
    ration_card_no: data.ration_card_no,
    documents: [],
    created_at: new Date().toISOString(),
  };
  await saveLocalHousehold(newHousehold);
  return newHousehold;
}

// Vault files need the X-Household-Token header, so an <img src> cannot load them directly:
// fetch once and keep an object URL for this visit.
const vaultFileCache: Record<string, string> = {};

export async function vaultFileUrl(householdId: string, docId: string | number): Promise<string | undefined> {
  const key = `${householdId}/${docId}`;
  if (vaultFileCache[key]) return vaultFileCache[key];
  const token = householdTokenFor(householdId);
  if (DEMO_MODE || !token || !navigator.onLine) return undefined;
  try {
    const blob = await request<Blob>(`/households/${householdId}/documents/${docId}/file`, { householdToken: token });
    vaultFileCache[key] = URL.createObjectURL(blob);
    return vaultFileCache[key];
  } catch (e) {
    console.warn('Could not load the vault file', e);
    return undefined;
  }
}

/** A fresh object URL for one vault file (the caller may revoke it). Used by /prepare. */
export async function fetchVaultFileBlobUrl(householdId: string, docId: string | number): Promise<string | null> {
  const token = householdTokenFor(householdId);
  if (DEMO_MODE || !token || !navigator.onLine) return null;
  try {
    const blob = await request<Blob>(`/households/${householdId}/documents/${docId}/file`, { householdToken: token });
    return URL.createObjectURL(blob);
  } catch (e) {
    console.warn('Could not load the vault file', e);
    return null;
  }
}

export async function getHousehold(id: string): Promise<Household | null> {
  const local = await getLocalHousehold(id);
  const token = householdTokenFor(id) || local?.token;

  if (!DEMO_MODE && navigator.onLine && token) {
    try {
      const docs = await request<any[]>(`/households/${id}/documents`, { householdToken: token });
      const mappedDocs: VaultDocument[] = docs.map((d) => ({
        id: String(d.id),
        household_id: id,
        doc_type: d.doc_type,
        filename: `${d.doc_type}.${(d.content_type || 'application/pdf').split('/')[1] || 'bin'}`,
        file_url: `${API_URL}${d.file_url}`,
        source: d.source || 'upload', // 'upload' | 'digilocker_mock' (show as "DigiLocker (demo)")
        uploaded_at: d.created_at || new Date().toISOString(),
        verified: false, // nothing in the vault is checked by an official yet
      }));
      // newest baseline photo (the server keeps every upload)
      const baseline = [...mappedDocs].reverse().find((d) => d.doc_type === 'baseline_photo');
      const merged: Household = {
        ...(local || {
          id,
          token,
          head_name: '',
          phone: '',
          village: '',
          district: '',
          state: '',
          created_at: new Date().toISOString(),
        }),
        token,
        documents: mappedDocs,
        baseline_photo_url: baseline ? await vaultFileUrl(id, baseline.id) : undefined,
      };
      await saveLocalHousehold(merged);
      return merged;
    } catch (e) {
      console.warn('Could not load household documents from the server vault:', e);
    }
  }
  return local;
}

export async function uploadVaultDocument(householdId: string, file: File, docType: string): Promise<VaultDocument> {
  if (DEMO_MODE) {
    const doc: VaultDocument = {
      id: `doc_${Date.now()}`,
      household_id: householdId,
      doc_type: docType,
      filename: file.name,
      file_url: URL.createObjectURL(file),
      source: 'upload',
      uploaded_at: new Date().toISOString(),
      verified: false,
    };
    const hh = await getLocalHousehold(householdId);
    if (hh) {
      if (docType === 'baseline_photo') hh.baseline_photo_url = doc.file_url;
      hh.documents = [doc, ...(hh.documents || []).filter((d) => d.doc_type !== docType)];
      await saveLocalHousehold(hh);
    }
    return doc;
  }
  vaultOnline('save documents in your vault');
  const token = householdTokenFor(householdId);
  if (!token) throw new Error('This vault was set up on another phone.');
  const form = new FormData();
  form.append('file', file);
  form.append('doc_type', docType);
  const created = await request<any>(`/households/${householdId}/documents`, {
    method: 'POST',
    body: form,
    householdToken: token,
  });
  vaultFileCache[`${householdId}/${created.id}`] = URL.createObjectURL(file);
  await getHousehold(householdId); // refresh the local copy from the server
  return {
    id: String(created.id),
    household_id: householdId,
    doc_type: docType,
    filename: file.name,
    file_url: `${API_URL}${created.file_url}`,
    source: created.source || 'upload',
    uploaded_at: created.created_at || new Date().toISOString(),
    verified: false,
  };
}

export async function deleteVaultDocument(householdId: string, docId: string): Promise<void> {
  if (!DEMO_MODE) {
    vaultOnline('delete documents from your vault');
    await request<void>(`/households/${householdId}/documents/${docId}`, {
      method: 'DELETE',
      householdToken: householdTokenFor(householdId),
    });
    delete vaultFileCache[`${householdId}/${docId}`];
    await getHousehold(householdId);
    return;
  }
  const hh = await getLocalHousehold(householdId);
  if (hh) {
    hh.documents = (hh.documents || []).filter((d) => String(d.id) !== String(docId));
    if (!hh.documents.find((d) => d.doc_type === 'baseline_photo')) hh.baseline_photo_url = undefined;
    await saveLocalHousehold(hh);
  }
}

/** DigiLocker (demo): Member 2 returns a consent page URL (clearly labelled "Demo"). */
export async function startDigiLockerFlow(householdId: string): Promise<{ consent_url: string; banner: string } | null> {
  if (DEMO_MODE) return null;
  vaultOnline('connect DigiLocker');
  const returnTo = `${window.location.origin}/prepare`;
  const res = await request<{ mode: string; demo: boolean; banner: string; consent_url: string }>(
    `/households/${householdId}/digilocker/start?return_to=${encodeURIComponent(returnTo)}`,
    { householdToken: householdTokenFor(householdId) }
  );
  return { consent_url: `${API_URL}${res.consent_url}`, banner: res.banner };
}

/** Demo mode only (no backend): sample documents, labelled DigiLocker (demo). */
export async function startDigiLockerMock(householdId: string): Promise<VaultDocument[]> {
  if (!DEMO_MODE) throw new Error('DigiLocker (demo) needs the Aapke Liye server. Try again when online.');
  const hh = await getLocalHousehold(householdId);
  const mockDocs: VaultDocument[] = ['aadhaar', 'ration_card'].map((t) => ({
    id: `dl_${t}_${Date.now()}`,
    household_id: householdId,
    doc_type: t,
    filename: `${t}-sample-digilocker-demo.pdf`,
    source: 'digilocker_mock',
    uploaded_at: new Date().toISOString(),
    verified: false,
  }));
  if (hh) {
    hh.documents = [...mockDocs, ...(hh.documents || [])];
    await saveLocalHousehold(hh);
  }
  return mockDocs;
}

/** "Use my household": the server links the vault to the claim (vault papers then count as
 *  available, and the PDF lists them), and the household's details fill empty claim fields. */
export async function linkHouseholdToClaim(claimId: string, householdId: string): Promise<ClaimOut> {
  const hh = await getLocalHousehold(householdId);
  if (DEMO_MODE) {
    const claim = await getClaim(claimId);
    return { ...claim, household_id: householdId };
  }
  vaultOnline('use your family vault');
  const hhToken = householdTokenFor(householdId);
  if (!hhToken) throw new Error('This vault was set up on another phone.');
  let updated = toClaim(
    await request<any>(`/claims/${claimId}/household`, {
      method: 'POST',
      claimId,
      householdToken: hhToken,
      body: JSON.stringify({ household_id: householdId }),
    })
  );
  const prefill: Record<string, string> = {};
  if (hh) {
    const pairs: [string, string | undefined][] = [
      ['name', hh.head_name], ['phone', hh.phone], ['village', hh.village],
      ['district', hh.district], ['state', hh.state],
    ];
    for (const [k, v] of pairs) if (v && !(updated.fields as any)[k]) prefill[k] = v;
  }
  if (Object.keys(prefill).length) updated = await updateFields(claimId, prefill);
  await saveOfflineClaim(updated);
  return updated;
}

// ============================================================================
// MESH RELAY (Member 3's protocol: Member-3/app/mesh.py + offline-client/mesh.js)
// ============================================================================
// Phone A (no network) seals the claim with Member 3's public key (RSA-OAEP + AES-256-GCM):
// only Member 3's server can open it, and any change on the way makes delivery fail.
// Phone B carries the sealed text (QR code / copy) and, once online, delivers it to Member 3,
// which files it through Member 2 and returns a receipt signed with Ed25519.

export const MESH_URL = (import.meta.env.VITE_MESH_URL || 'http://localhost:8002').replace(/\/$/, '');
const MESH_KEY_STORE = 'aapke_liye_mesh_key';
const MESH_IDS_STORE = 'aapke_liye_mesh_ids';

/** Member 3's public key and limits. Fetched while online and kept, so a phone with no
 *  network can still seal. Throws if it was never fetched. */
export async function getMeshKey(): Promise<any> {
  if (navigator.onLine) {
    try {
      const key = await mesh.fetchMeshKey(MESH_URL);
      try {
        localStorage.setItem(MESH_KEY_STORE, JSON.stringify(key));
      } catch {
        // private mode: keep it for this visit only
      }
      return key;
    } catch (e) {
      console.warn('Could not fetch the mesh key; using the saved one', e);
    }
  }
  try {
    const saved = localStorage.getItem(MESH_KEY_STORE);
    if (saved) return JSON.parse(saved);
  } catch {
    // ignore
  }
  throw new Error('Open the app once with internet so it can get the relief office key.');
}

/** The same envelope id every time one claim is sealed, so carrying it twice files it once. */
function meshIdFor(claim: ClaimOut): { id: string; createdAt: string } {
  let ids: Record<string, { id: string; createdAt: string }> = {};
  try {
    ids = JSON.parse(localStorage.getItem(MESH_IDS_STORE) || '{}');
  } catch {
    ids = {};
  }
  if (!ids[claim.id]) {
    ids[claim.id] = {
      id: crypto.randomUUID(),
      createdAt: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'),
    };
    try {
      localStorage.setItem(MESH_IDS_STORE, JSON.stringify(ids));
    } catch {
      // ignore
    }
  }
  return ids[claim.id];
}

// Only Member 2's claim fields travel (unknown keys would be refused there).
const MESH_FIELDS = ['name', 'phone', 'village', 'district', 'state', 'disaster_type', 'date_of_incident',
  'losses', 'documents_lost', 'bank_account_available', 'vulnerability', 'crop_insured', 'is_hilly'];

/** Seals a claim for phone-to-phone relay. The QR code holds only the sealed text: a
 *  carrier cannot read the name, village or losses. `summary` stays on this phone. */
export async function sealClaimEnvelope(claim: ClaimOut): Promise<SealedClaimEnvelope> {
  const key = await getMeshKey();
  const fields: Record<string, any> = {};
  for (const k of MESH_FIELDS) {
    const v = (claim.fields as any)[k];
    if (v !== undefined && v !== null && v !== '') fields[k] = v;
  }
  const priority: 'urgent' | 'normal' = (claim.fields.vulnerability || []).length > 0 ? 'urgent' : 'normal';
  const { id, createdAt } = meshIdFor(claim);
  const sealed = await mesh.sealClaim(
    {
      consent: true,
      consent_text_version: claim.consent_text_version || 'v1',
      language: claim.language,
      fields,
      submit: true,
    },
    key,
    { priority, claimId: id, createdAt } as any
  );
  const { text, fitsInQr } = mesh.envelopeText(sealed);
  const envelope: SealedClaimEnvelope = {
    claim_id: sealed.claim_id,
    local_claim_id: claim.id,
    created_at: sealed.created_at,
    sender_device_id: 'this-phone',
    priority,
    summary: {
      name: claim.fields.name || '—',
      village: claim.fields.village || '—',
      disaster_type: claim.fields.disaster_type || claim.disaster_type || 'disaster',
      losses_count: (claim.fields.losses || []).length,
      has_photos: (claim.photos || []).length > 0,
    },
    sealed_text: text,
    fits_in_qr: fitsInQr,
    own: true,
  };
  const before = (await getStoredMeshEnvelopes()).find((e) => e.claim_id === envelope.claim_id);
  if (before?.receipt) {
    envelope.receipt = before.receipt;
    envelope.receipt_verified = before.receipt_verified;
  }
  await saveMeshEnvelope(envelope);
  return envelope;
}

/** Phone B: read a scanned / pasted sealed claim. The contents stay private. */
export async function importMeshEnvelope(text: string): Promise<SealedClaimEnvelope> {
  const sealed = mesh.parseEnvelope(text.trim());
  const envelope: SealedClaimEnvelope = {
    claim_id: sealed.claim_id,
    created_at: sealed.created_at,
    sender_device_id: 'carried',
    priority: sealed.priority === 'urgent' ? 'urgent' : 'normal',
    summary: { name: 'Sealed claim (private)', village: '—', disaster_type: '—', losses_count: 0, has_photos: false },
    sealed_text: JSON.stringify(sealed),
    fits_in_qr: true,
    own: false,
  };
  await saveMeshEnvelope(envelope);
  return envelope;
}

function receiptText(r: any): string {
  return `${r.message || 'Your claim reached the relief office'}${r.reference ? ` · ${r.reference}` : ''}`;
}

/** Deliver a carried envelope to Member 3 (only when online). A receipt is stored only
 *  when Member 3 really returned one; otherwise the envelope stays waiting. */
export async function submitMeshEnvelope(
  envelope: SealedClaimEnvelope
): Promise<{ delivered: boolean; receipt?: string; error?: string }> {
  if (DEMO_MODE) return { delivered: false, error: 'Mesh delivery needs the live servers.' };
  if (!navigator.onLine) return { delivered: false, error: 'No network yet: the claim stays on this phone.' };
  try {
    const res = await mesh.deliverEnvelope(MESH_URL, mesh.parseEnvelope(envelope.sealed_text));
    const key = await getMeshKey().catch(() => null);
    envelope.receipt = receiptText(res.receipt);
    envelope.receipt_verified = key ? await mesh.verifyReceipt(res.receipt, key) : false;
    envelope.delivery_status = res.status;
    await saveMeshEnvelope(envelope);
    return { delivered: true, receipt: envelope.receipt };
  } catch (e: any) {
    return { delivered: false, error: e?.message || 'Delivery failed; try again later.' };
  }
}

/** Phone A: has my sealed claim reached the relief office? (signed receipt from Member 3) */
export async function checkMeshReceipt(envelope: SealedClaimEnvelope): Promise<SealedClaimEnvelope> {
  if (DEMO_MODE || !navigator.onLine || envelope.receipt) return envelope;
  try {
    const r = await mesh.fetchReceipt(MESH_URL, envelope.claim_id);
    if (r) {
      const key = await getMeshKey().catch(() => null);
      envelope.receipt = receiptText(r);
      envelope.receipt_verified = key ? await mesh.verifyReceipt(r, key) : false;
      await saveMeshEnvelope(envelope);
    }
  } catch (e) {
    console.warn('Could not check the mesh receipt', e);
  }
  return envelope;
}

export { getStoredMeshEnvelopes, removeMeshEnvelope };
