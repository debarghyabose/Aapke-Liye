// src/api/client.ts
// Standalone mock client - purely frontend, zero external backend dependencies.
import {
  ClaimCreate,
  ClaimCreated,
  ClaimFields,
  ClaimOut,
  PhotoOut,
  StaffClaimOut,
  StatusOut,
} from '../types/api';
import {
  MOCK_CLAIM_ID,
  MOCK_SAMPLE_CLAIM,
  MOCK_STATUS,
  MOCK_STAFF_CLAIMS,
} from '../mocks/sampleData';

// In-memory state persistent across pages during session
let currentClaimState: ClaimOut = JSON.parse(JSON.stringify(MOCK_SAMPLE_CLAIM));

export async function createClaim(payload: ClaimCreate): Promise<ClaimCreated> {
  await new Promise((res) => setTimeout(res, 200));
  const newId = `CLM-2026-${payload.language.toUpperCase()}-${Math.floor(1000 + Math.random() * 9000)}`;
  currentClaimState = {
    ...JSON.parse(JSON.stringify(MOCK_SAMPLE_CLAIM)),
    id: newId,
    language: payload.language,
    disaster_type: payload.disaster_type || 'flood',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    status: 'Draft',
    recordings: [{ id: 1, status: 'processed' }],
  };

  return {
    ...currentClaimState,
    claim_token: `tok_${Math.random().toString(36).substring(2, 12)}`,
  };
}

export async function getClaim(claimId: string): Promise<ClaimOut> {
  await new Promise((res) => setTimeout(res, 150));
  return { ...currentClaimState, id: claimId || currentClaimState.id };
}

export async function uploadAudio(
  claimId: string,
  _audioBlob: Blob,
  onProgressMsg?: (msg: string) => void
): Promise<ClaimOut> {
  // Simulate Gemini multimodal audio pipeline:
  // 1. Acoustic speech processing
  if (onProgressMsg) onProgressMsg('Transcribing dialect & emotional speech…');
  await new Promise((res) => setTimeout(res, 800));

  // 2. Multimodal extraction
  if (onProgressMsg) onProgressMsg('Gemini is extracting losses & matching SDRF norms…');
  await new Promise((res) => setTimeout(res, 900));

  currentClaimState.transcript =
    currentClaimState.transcript ||
    'আমাদের গ্রাম ঘাটাল, পশ্চিম মেদিনীপুর। জলে আমাদের মাটির ঘর সম্পূর্ণ ভেঙে গেছে। ২ বিঘা ধান ডুবে গেছে, এবং দুটি গরু মারা গেছে। আধার কার্ড আর রেশন কার্ড বন্যায় ভেসে গেছে।';
  
  currentClaimState.missing_fields = ['bank_account_number'];
  currentClaimState.follow_up_questions = [
    {
      field: 'bank_account_number',
      question:
        'আপনার বা পরিবারের কারো কি ব্যাংক পাসবই বা অ্যাকাউন্ট নম্বর মনে আছে? (বা আধার লিঙ্ক করা কোনো অ্যাকাউন্ট আছে?)',
      suggested_answers: [
        'হ্যাঁ, স্টেট ব্যাংকে আছে (SBI)',
        'আধার লিঙ্ক করা আছে (DBT)',
        'পাসবই জলে ভিজে গেছে, পরে দেব',
      ],
    },
  ];

  return { ...currentClaimState };
}

export async function retryAudio(claimId: string): Promise<ClaimOut> {
  await new Promise((res) => setTimeout(res, 400));
  return { ...currentClaimState };
}

export async function uploadPhoto(
  claimId: string,
  file: File,
  lat?: number,
  lon?: number,
  takenAt?: string
): Promise<ClaimOut> {
  await new Promise((res) => setTimeout(res, 600));

  const newPhoto: PhotoOut = {
    id: Date.now(),
    sha256: `sha256_${Math.random().toString(36).substring(2, 10)}`,
    lat: lat ?? 22.6683,
    lon: lon ?? 87.7214,
    taken_at: takenAt ?? new Date().toISOString(),
    url: URL.createObjectURL(file),
    verification: {
      status: 'complete',
      damage_level: 'severe',
      gemini_reason:
        'Gemini Visual Assessment: Heavy structural mud erosion, collapsed bamboo thatch and standing flood watermark exceeding 3.5 feet visible.',
      gps_valid: true,
      time_valid: true,
      exif_valid: true,
      duplicate: false,
    },
  };

  currentClaimState.photos = [newPhoto, ...currentClaimState.photos];
  return { ...currentClaimState };
}

export async function reverifyPhoto(claimId: string, photoId: number): Promise<ClaimOut> {
  await new Promise((res) => setTimeout(res, 500));
  const photo = currentClaimState.photos.find((p) => p.id === photoId);
  if (photo) {
    photo.verification.status = 'complete';
  }
  return { ...currentClaimState };
}

export async function updateFields(
  claimId: string,
  fields: Partial<ClaimFields>
): Promise<ClaimOut> {
  await new Promise((res) => setTimeout(res, 200));
  currentClaimState.fields = { ...currentClaimState.fields, ...fields };
  return { ...currentClaimState };
}

export async function submitClaim(claimId: string): Promise<ClaimOut> {
  await new Promise((res) => setTimeout(res, 700));
  currentClaimState.status = 'Submitted';
  currentClaimState.submitted_at = new Date().toISOString();
  currentClaimState.pdf_url = '/sample-claim.pdf';
  currentClaimState.history.push({
    status: 'Submitted',
    note: 'Claim package cryptographically sealed & sent to BDO queue.',
    at: new Date().toISOString(),
  });
  return { ...currentClaimState };
}

export async function getClaimPdf(_claimId: string): Promise<Blob> {
  try {
    const res = await fetch('/sample-claim.pdf');
    if (res.ok) {
      return await res.blob();
    }
  } catch (e) {
    console.warn('Could not fetch sample-claim.pdf, creating fallback text blob', e);
  }

  return new Blob(
    [
      `GOVERNMENT RELIEF CLAIM FORM\nClaim Reference ID: ${_claimId}\nApplicant: ${currentClaimState.fields.name || 'Sunita Mondal'}\nEstimated SDRF Assistance: ₹2,06,300\nStatus: Submitted to BDO Office\nAapke Liye Standalone System`,
    ],
    { type: 'application/pdf' }
  );
}

export async function getStatus(claimId: string): Promise<StatusOut> {
  await new Promise((res) => setTimeout(res, 250));
  return {
    ...MOCK_STATUS,
    claim_id: claimId || currentClaimState.id || MOCK_CLAIM_ID,
    status: currentClaimState.status || 'Submitted',
  };
}

export async function getStaffClaim(claimId: string): Promise<StaffClaimOut> {
  await new Promise((res) => setTimeout(res, 250));
  const found = MOCK_STAFF_CLAIMS.find((c) => c.id === claimId);
  return found || MOCK_STAFF_CLAIMS[0];
}

export async function getStaffClaimsList(): Promise<StaffClaimOut[]> {
  await new Promise((res) => setTimeout(res, 200));
  return MOCK_STAFF_CLAIMS;
}
