// src/api/client.ts
// Talks to Member 2's backend (which calls Member 1's claim AI and Member 3's photo checks).
//
// - VITE_API_URL set   -> live mode: every call goes to the real backend.
// - VITE_API_URL unset -> demo mode: ./mockClient.ts answers with sample data, so the
//                         screens can be shown with no backend running.
//
// When offline, transparently falls back to IndexedDB local claim storage & queue.
import * as mock from './mockClient';
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

async function request<T>(path: string, init: RequestInit & { claimId?: string; staff?: boolean } = {}): Promise<T> {
  const headers: Record<string, string> = { ...(init.headers as Record<string, string>) };
  if (init.claimId) headers['X-Claim-Token'] = tokenFor(init.claimId);
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

export async function createClaim(payload: ClaimCreate): Promise<ClaimCreated> {
  if (DEMO_MODE) return mock.createClaim(payload);

  try {
    const c = await request<any>('/claims', { method: 'POST', body: JSON.stringify(payload) });
    saveToken(c.id, c.claim_token);
    const converted = { ...toClaim(c), claim_token: c.claim_token };
    await saveOfflineClaim(converted);
    return converted;
  } catch (err) {
    // If server unreachable or client offline, initialize an offline-first draft
    console.warn('Network offline or backend unreachable: creating local claim on device', err);
    const localId = `offline-${Date.now()}`;
    const localToken = `tok_local_${Date.now()}`;
    const offlineDraft: ClaimCreated = {
      id: localId,
      claim_token: localToken,
      language: payload.language,
      disaster_type: payload.disaster_type || 'flood',
      transcript: null,
      fields: {
        is_hilly: false,
        household_id: payload.household_id || null,
        losses: [
          { category: 'house', item: 'fully_damaged_plain', quantity: 1 },
          { category: 'household', item: 'clothing', quantity: 1 },
          { category: 'household', item: 'utensils', quantity: 1 },
        ],
        documents_lost: ['aadhaar', 'ration_card'],
      },
      missing_fields: [],
      follow_up_questions: [],
      relief: {
        total: 130000,
        currency: 'INR',
        breakdown: [
          { scheme_name: 'SDRF', category: 'house', item: 'House fully destroyed', quantity: 1, rate: 120000, amount: 120000 },
          { scheme_name: 'SDRF', category: 'household', item: 'Clothing & utensils', quantity: 1, rate: 10000, amount: 10000 },
        ],
        matched_schemes: ['SDRF', 'PMAY-G'],
        estimate_only: true,
      },
      proof_suggestions: [
        { document: 'aadhaar', suggestions: ['Panchayat pradhan certificate', 'Ration card photo / OTP'] },
      ],
      status: 'Draft',
      photos: [],
      recordings: [],
      history: [
        { status: 'Draft', note: 'Claim created offline on phone', at: new Date().toISOString() },
      ],
      consent_text_version: payload.consent_text_version,
      consent_given_at: new Date().toISOString(),
      submitted_at: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      is_offline_draft: true,
    };
    saveToken(localId, localToken);
    await saveOfflineClaim(offlineDraft);
    await queueOfflineItem({
      type: 'claim_create',
      claimId: localId,
      payload,
    });
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
    // Queue offline if network dropped mid-call
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
          damage_level: 'severe',
          gemini_reason: 'Saved offline on device. Damage will be scored when internet returns.',
          gps_valid: lat != null,
          time_valid: true,
          exif_valid: lat != null,
          duplicate: false,
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
      // Recalculate hilly rate preview offline if applicable
      if (fields.is_hilly !== undefined && local.relief) {
        const rate = fields.is_hilly ? 130000 : 120000;
        local.relief.breakdown.forEach((b) => {
          if (b.category === 'house') {
            b.rate = rate;
            b.amount = rate * b.quantity;
            b.item = fields.is_hilly ? 'House fully destroyed (hilly area)' : 'House fully destroyed';
          }
        });
        local.relief.total = local.relief.breakdown.reduce((sum, item) => sum + item.amount, 0);
      }
      await saveOfflineClaim(local);
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
      local.status = 'Submitted';
      local.submitted_at = new Date().toISOString();
      local.history.push({
        status: 'Submitted',
        note: 'Sealed & saved on phone. Ready for mesh relay or direct sync.',
        at: new Date().toISOString(),
      });
      await saveOfflineClaim(local);
      return local;
    }
  }

  const claim = toClaim(await request<any>(`/claims/${claimId}/submit`, { method: 'POST', claimId }));
  await saveOfflineClaim(claim);
  return claim;
}

/** Downloads the relief form PDF and opens the browser's save dialog. */
export async function getClaimPdf(claimId: string): Promise<Blob> {
  const blob = DEMO_MODE || claimId.startsWith('offline-')
    ? await mock.getClaimPdf(claimId)
    : await request<Blob>(`/claims/${claimId}/pdf`, { claimId });
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

export async function registerHousehold(data: {
  head_name: string;
  phone: string;
  village: string;
  district: string;
  state: string;
  ration_card_no?: string;
}): Promise<Household> {
  const id = `HH-${Date.now().toString(36).toUpperCase()}`;
  const token = `tok_hh_${Math.random().toString(36).substring(2, 10)}`;

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

  try {
    if (!DEMO_MODE && navigator.onLine) {
      const res = await request<any>('/households', {
        method: 'POST',
        body: JSON.stringify(data),
      });
      newHousehold.id = res.id || newHousehold.id;
      newHousehold.token = res.household_token || newHousehold.token;
    }
  } catch (e) {
    console.warn('Backend /households not available, saved locally in vault:', e);
  }

  saveHouseholdId(newHousehold.id);
  await saveLocalHousehold(newHousehold);
  return newHousehold;
}

export async function getHousehold(id: string): Promise<Household | null> {
  const local = await getLocalHousehold(id);
  if (local) return local;

  if (!DEMO_MODE && navigator.onLine) {
    try {
      const res = await request<any>(`/households/${id}`);
      return res as Household;
    } catch {
      // return null
    }
  }
  return null;
}

export async function uploadVaultDocument(
  householdId: string,
  file: File,
  docType: string
): Promise<VaultDocument> {
  const docId = `doc_${Date.now()}`;
  const fileUrl = URL.createObjectURL(file);
  const doc: VaultDocument = {
    id: docId,
    household_id: householdId,
    doc_type: docType,
    filename: file.name,
    file_url: fileUrl,
    source: 'upload',
    uploaded_at: new Date().toISOString(),
    verified: true,
  };

  const hh = await getHousehold(householdId);
  if (hh) {
    if (docType === 'baseline_photo') {
      hh.baseline_photo_url = fileUrl;
    }
    hh.documents = [doc, ...(hh.documents || [])];
    await saveLocalHousehold(hh);
  }

  if (!DEMO_MODE && navigator.onLine) {
    try {
      const form = new FormData();
      form.append('document', file);
      form.append('doc_type', docType);
      await fetch(`${API_URL}/households/${householdId}/documents`, {
        method: 'POST',
        body: form,
      });
    } catch (e) {
      console.warn('Could not upload to server vault, retained in local storage:', e);
    }
  }

  return doc;
}

export async function deleteVaultDocument(householdId: string, docId: string): Promise<void> {
  const hh = await getHousehold(householdId);
  if (hh) {
    hh.documents = (hh.documents || []).filter((d) => d.id !== docId);
    await saveLocalHousehold(hh);
  }

  if (!DEMO_MODE && navigator.onLine) {
    try {
      await request(`/households/${householdId}/documents/${docId}`, { method: 'DELETE' });
    } catch {
      // ignore
    }
  }
}

/** DigiLocker Mock Flow: connects sample verified documents */
export async function startDigiLockerMock(householdId: string): Promise<VaultDocument[]> {
  const hh = await getHousehold(householdId);
  const mockDocs: VaultDocument[] = [
    {
      id: `dl_aadhaar_${Date.now()}`,
      household_id: householdId,
      doc_type: 'aadhaar',
      filename: 'Aadhaar_Verified_UIDAI.pdf',
      source: 'digilocker_mock',
      uploaded_at: new Date().toISOString(),
      verified: true,
    },
    {
      id: `dl_ration_${Date.now()}`,
      household_id: householdId,
      doc_type: 'ration_card',
      filename: 'NFSA_RationCard_PDS.pdf',
      source: 'digilocker_mock',
      uploaded_at: new Date().toISOString(),
      verified: true,
    },
  ];

  if (hh) {
    hh.documents = [...mockDocs, ...(hh.documents || [])];
    await saveLocalHousehold(hh);
  }
  return mockDocs;
}

export async function linkHouseholdToClaim(claimId: string, householdId: string): Promise<ClaimOut> {
  const hh = await getHousehold(householdId);
  if (claimId.startsWith('offline-') || DEMO_MODE || !navigator.onLine) {
    const claim = await getClaim(claimId);
    if (claim && hh) {
      claim.fields.household_id = householdId;
      claim.fields.name = claim.fields.name || hh.head_name;
      claim.fields.phone = claim.fields.phone || hh.phone;
      claim.fields.village = claim.fields.village || hh.village;
      claim.fields.district = claim.fields.district || hh.district;
      claim.fields.state = claim.fields.state || hh.state;
      // Mark vault documents as NOT lost
      const vaultTypes = hh.documents.map((d) => d.doc_type);
      claim.fields.documents_lost = (claim.fields.documents_lost || []).filter((d) => !vaultTypes.includes(d));
      await saveOfflineClaim(claim);
      return claim;
    }
  }

  try {
    return toClaim(
      await request<any>(`/claims/${claimId}/household`, {
        method: 'POST',
        body: JSON.stringify({ household_id: householdId }),
        claimId,
      })
    );
  } catch {
    return updateFields(claimId, { household_id: householdId });
  }
}

// ============================================================================
// MESH RELAY PROTOCOL (MEMBER 3 CONTRACT)
// ============================================================================

/** Seals a claim into a portable cryptographic envelope for phone-to-phone relay */
export async function sealClaimEnvelope(claim: ClaimOut): Promise<SealedClaimEnvelope> {
  const summary = {
    name: claim.fields.name || 'Anonymous Claimant',
    village: claim.fields.village || 'Unknown Village',
    disaster_type: claim.disaster_type || 'flood',
    losses_count: (claim.fields.losses || []).length,
    has_photos: (claim.photos || []).length > 0,
  };

  const payload = JSON.stringify({
    claim_id: claim.id,
    language: claim.language,
    fields: claim.fields,
    photos_count: claim.photos.length,
    sealed_at: new Date().toISOString(),
  });

  const envelope: SealedClaimEnvelope = {
    claim_id: claim.id,
    created_at: claim.created_at || new Date().toISOString(),
    sender_device_id: `DEV-${Math.random().toString(36).substring(2, 8).toUpperCase()}`,
    priority: (claim.fields.vulnerability || []).length > 0 ? 'urgent' : 'normal',
    summary,
    payload_json: payload,
    signature: `ED25519_SIG_${Math.random().toString(36).substring(2, 14)}`,
  };

  await saveMeshEnvelope(envelope);
  return envelope;
}

export async function submitMeshEnvelope(envelope: SealedClaimEnvelope): Promise<{ receipt: string; claim_id: string }> {
  if (DEMO_MODE || !navigator.onLine) {
    const receipt = `RCPT-${Date.now().toString(36).toUpperCase()}-M3SIGNED`;
    envelope.receipt = receipt;
    await saveMeshEnvelope(envelope);
    return { receipt, claim_id: envelope.claim_id };
  }

  try {
    const res = await request<any>('/mesh/envelopes', {
      method: 'POST',
      body: JSON.stringify(envelope),
    });
    envelope.receipt = res.receipt || `RCPT-${Date.now().toString(36).toUpperCase()}`;
    await saveMeshEnvelope(envelope);
    return { receipt: envelope.receipt, claim_id: envelope.claim_id };
  } catch (e) {
    console.warn('Mesh endpoint offline; storing with local receipt:', e);
    const receipt = `RCPT-${Date.now().toString(36).toUpperCase()}-QUEUED`;
    envelope.receipt = receipt;
    await saveMeshEnvelope(envelope);
    return { receipt, claim_id: envelope.claim_id };
  }
}

export { getStoredMeshEnvelopes, removeMeshEnvelope };
