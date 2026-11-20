// src/types/api.ts
// Derived directly from Member-2/backend/app/schemas.py

export interface Loss {
  category: string; // "house" | "crop" | "livestock" | "household" | "ex_gratia"
  item: string;
  quantity: number;
  damage_percent?: number | null;
}

export interface ClaimFields {
  name?: string | null;
  phone?: string | null;
  village?: string | null;
  district?: string | null;
  state?: string | null;
  disaster_type?: string | null;
  date_of_incident?: string | null; // YYYY-MM-DD
  losses?: Loss[] | null;
  documents_lost?: string[] | null;
  bank_account_available?: boolean | null;
  [key: string]: any;
}

export interface ClaimCreate {
  language: string;
  disaster_type?: string | null;
  consent: true;
  consent_text_version: string;
}

export interface ClaimFieldsUpdate {
  fields: ClaimFields;
}

export interface StatusUpdate {
  status: string;
  note?: string | null;
}

export interface PhotoVerification {
  status: 'pending' | 'complete';
  damage_level?: 'none' | 'partial' | 'severe' | 'total';
  gemini_reason?: string;
  gps_valid?: boolean;
  time_valid?: boolean;
  exif_valid?: boolean;
  duplicate?: boolean;
  [key: string]: any;
}

export interface PhotoOut {
  id: number;
  sha256: string;
  lat: number | null;
  lon: number | null;
  taken_at: string | null;
  verification: PhotoVerification;
  url?: string;
  duplicate_of_claim_id?: string | null; // officials only
}

export interface StaffPhotoOut extends PhotoOut {
  duplicate_of_claim_id?: string | null;
}

export interface RecordingOut {
  id: number;
  status: string; // "pending" | "processed"
}

export interface StatusEventOut {
  status: string;
  note: string | null;
  at: string;
}

export interface StatusOut {
  claim_id: string;
  status: string;
  updated_at: string;
  timeline: StatusEventOut[];
}

export interface ReliefScheme {
  scheme_name: string;
  category: string;
  item: string;
  quantity: number;
  rate: number;
  amount: number;
  description?: string;
}

export interface ReliefSummary {
  total: number;
  currency: string;
  breakdown: ReliefScheme[];
  matched_schemes: string[]; // ["SDRF", "PMFBY", "PMAY-G"]
  estimate_only?: boolean; // rules still marked "sample" by Member 5
  may_also_qualify?: Array<{
    scheme_code: string;
    scheme_name?: string;
    estimated_amount?: number;
    conditions?: string[];
  }>;
}

export interface ClaimOut {
  id: string;
  language: string;
  disaster_type: string | null;
  transcript: string | null;
  fields: ClaimFields;
  missing_fields: string[];
  follow_up_questions: Array<{
    field: string;
    question: string;
    suggested_answers?: string[];
  }>;
  relief: ReliefSummary | null;
  proof_suggestions: Array<{
    document: string;
    suggestions: string[];
  }>;
  status: 'Draft' | 'Submitted' | 'Verified' | 'Approved' | 'Paid' | 'Rejected';
  pdf_url?: string | null;
  photos: PhotoOut[];
  recordings: RecordingOut[];
  history: StatusEventOut[];
  consent_text_version: string;
  consent_given_at: string;
  submitted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClaimCreated extends ClaimOut {
  claim_token: string;
}

export interface StaffClaimOut extends ClaimOut {
  photos: StaffPhotoOut[];
  vulnerability_flags?: {
    is_elderly?: boolean;
    is_disabled?: boolean;
    is_single_mother?: boolean;
  };
}

