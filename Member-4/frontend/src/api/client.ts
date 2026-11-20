// src/api/client.ts
// Talks to Member 2's backend (which calls Member 1's claim AI and Member 3's photo checks).
//
// - VITE_API_URL set   -> live mode: every call goes to the real backend.
// - VITE_API_URL unset -> demo mode: ./mockClient.ts answers with sample data, so the
//                         screens can be shown with no backend running.
//
// Member 2 returns its own shapes (see Member-2/backend/app/schemas.py). The `to*` functions
// below translate them into the shapes the screens use (src/types/api.ts), so pages never
// need to know the backend's field names.
import * as mock from './mockClient';
import {
  ClaimCreate,
  ClaimCreated,
  ClaimFields,
  ClaimOut,
  PhotoOut,
  PhotoVerification,
  ReliefScheme,
  ReliefSummary,
  StaffClaimOut,
  StatusOut,
} from '../types/api';

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
  if (e instanceof TypeError) return 'Cannot reach the Aapke Liye server. Check your connection and try again.';
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

function saveToken(claimId: string, token: string) {
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
  if (!t) throw new ApiError(404, 'This claim was filed on another device. Open it on the phone that filed it.');
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

// Photos are never sent back to the claimant by the server (they are stored encrypted), so
// we keep a local preview of each one we upload, keyed by its sha256.
const photoPreviews: Record<string, string> = {};

async function sha256Hex(file: Blob): Promise<string | null> {
  try {
    const buf = await crypto.subtle.digest('SHA-256', await file.arrayBuffer());
    return Array.from(new Uint8Array(buf))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('');
  } catch {
    return null; // crypto.subtle needs https or localhost
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
    url: photoPreviews[p.sha256],
    duplicate_of_claim_id: p.duplicate_of_claim_id,
    verification: {
      ...v,
      status: v.status === 'complete' ? 'complete' : 'pending',
      damage_level: v.status === 'complete' ? damageLevel(v.damage_score, v.damage_detected) : undefined,
      gemini_reason:
        v.status === 'complete'
          ? notes.join(' ') || (v.damage_detected ? 'Damage detected in the photo.' : 'No damage detected.')
          : 'Photo saved. Checking is not available right now; it will be checked again.',
      gps_valid: v.gps_ok,
      time_valid: v.timestamp_ok,
      exif_valid: v.gps_ok && v.timestamp_ok,
      duplicate: v.duplicate,
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
      description: l.note || undefined,
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
    may_also_qualify: others,
  } as ReliefSummary;
}

function toClaim(c: any): ClaimOut {
  const questions: any[] = c.follow_up_questions || [];
  const missing: string[] = c.missing_fields || [];
  return {
    ...c,
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

// ---------- API (same function names the pages already use) ----------

export async function createClaim(payload: ClaimCreate): Promise<ClaimCreated> {
  if (DEMO_MODE) return mock.createClaim(payload);
  const c = await request<any>('/claims', { method: 'POST', body: JSON.stringify(payload) });
  saveToken(c.id, c.claim_token);
  return { ...toClaim(c), claim_token: c.claim_token };
}

export async function getClaim(claimId: string): Promise<ClaimOut> {
  if (DEMO_MODE) return mock.getClaim(claimId);
  return toClaim(await request<any>(`/claims/${claimId}`, { claimId }));
}

export async function uploadAudio(claimId: string, audioBlob: Blob, onProgressMsg?: (m: string) => void): Promise<ClaimOut> {
  if (DEMO_MODE) return mock.uploadAudio(claimId, audioBlob, onProgressMsg);
  onProgressMsg?.('Understanding what you said…');
  const form = new FormData();
  const ext = (audioBlob.type.split('/')[1] || 'webm').split(';')[0];
  form.append('audio', new File([audioBlob], `recording.${ext}`, { type: audioBlob.type.split(';')[0] || 'audio/webm' }));
  return toClaim(await request<any>(`/claims/${claimId}/audio`, { method: 'POST', body: form, claimId }));
}

/** A typed answer, a tapped suggestion, or speech the phone turned into text. */
export async function sendText(claimId: string, text: string): Promise<ClaimOut> {
  if (DEMO_MODE) return mock.getClaim(claimId);
  return toClaim(
    await request<any>(`/claims/${claimId}/text`, { method: 'POST', body: JSON.stringify({ text }), claimId })
  );
}

export async function retryAudio(claimId: string): Promise<ClaimOut> {
  if (DEMO_MODE) return mock.retryAudio(claimId);
  return toClaim(await request<any>(`/claims/${claimId}/audio/retry`, { method: 'POST', claimId }));
}

export async function uploadPhoto(claimId: string, file: File, lat?: number, lon?: number, takenAt?: string): Promise<ClaimOut> {
  if (DEMO_MODE) return mock.uploadPhoto(claimId, file, lat, lon, takenAt);
  const digest = await sha256Hex(file);
  if (digest) photoPreviews[digest] = URL.createObjectURL(file);
  const form = new FormData();
  form.append('photo', file);
  if (lat != null) form.append('lat', String(lat));
  if (lon != null) form.append('lon', String(lon));
  form.append('taken_at', takenAt || new Date(file.lastModified || Date.now()).toISOString());
  return toClaim(await request<any>(`/claims/${claimId}/photos`, { method: 'POST', body: form, claimId }));
}

export async function reverifyPhoto(claimId: string, photoId: number): Promise<ClaimOut> {
  if (DEMO_MODE) return mock.reverifyPhoto(claimId, photoId);
  return toClaim(await request<any>(`/claims/${claimId}/photos/${photoId}/reverify`, { method: 'POST', claimId }));
}

export async function updateFields(claimId: string, fields: Partial<ClaimFields>): Promise<ClaimOut> {
  if (DEMO_MODE) return mock.updateFields(claimId, fields);
  return toClaim(
    await request<any>(`/claims/${claimId}`, { method: 'PATCH', body: JSON.stringify({ fields }), claimId })
  );
}

export async function submitClaim(claimId: string): Promise<ClaimOut> {
  if (DEMO_MODE) return mock.submitClaim(claimId);
  return toClaim(await request<any>(`/claims/${claimId}/submit`, { method: 'POST', claimId }));
}

/** Downloads the relief form PDF and opens the browser's save dialog. */
export async function getClaimPdf(claimId: string): Promise<Blob> {
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
  if (DEMO_MODE) return mock.getStatus(claimId);
  return request<StatusOut>(`/status/${claimId}`, { claimId });
}

// ---------- ready-to-sign letters (Member 1 fills Member 5's legal templates) ----------

export interface DraftLetter {
  doc_type: string;
  title: string;
  text: string;
  missing_fields: string[]; // left as [TO FILL: ...] in the text
}

export async function draftDocument(claimId: string, docType: string): Promise<DraftLetter> {
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

/** Member 1's escalation ladder: which letter to send next for a stuck claim. */
export async function getEscalation(claimId: string): Promise<Escalation> {
  return request<Escalation>(`/claims/${claimId}/escalation`, { claimId });
}

/** Member 3's live map data through Member 2: claims.geojson, flood-extent.geojson, summary, fraud-flags. */
export async function getDashboard(view: string): Promise<any> {
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
