// src/mocks/sampleData.ts
import { ClaimOut, StatusOut, StaffClaimOut } from '../types/api';

export const MOCK_CLAIM_ID = "CLM-2026-WB-8492";

export const MOCK_SAMPLE_CLAIM: ClaimOut = {
  id: MOCK_CLAIM_ID,
  language: "bn",
  disaster_type: "flood",
  transcript: "আমাদের গ্রাম ঘাটাল, পশ্চিম মেদিনীপুর। জলে আমাদের মাটির ঘর সম্পূর্ণ ভেঙে গেছে। ২ বিঘা ধান ডুবে গেছে, এবং দুটি গরু মারা গেছে। আধার কার্ড আর রেশন কার্ড বন্যায় ভেসে গেছে।",
  fields: {
    name: "Sunita Mondal",
    phone: "+91 98301 23456",
    village: "Ghatal Block-II",
    district: "Paschim Medinipur",
    state: "West Bengal",
    disaster_type: "flood",
    date_of_incident: "2026-10-14",
    losses: [
      {
        category: "house",
        item: "fully_damaged_plain",
        quantity: 1,
        damage_percent: 100
      },
      {
        category: "crop",
        item: "rainfed",
        quantity: 0.8,
        damage_percent: 100
      },
      {
        category: "livestock",
        item: "milch_large",
        quantity: 2,
        damage_percent: 100
      },
      {
        category: "household",
        item: "clothing",
        quantity: 1
      },
      {
        category: "household",
        item: "utensils",
        quantity: 1
      }
    ],
    documents_lost: ["aadhaar", "ration_card", "land_record"],
    bank_account_available: true
  },
  missing_fields: ["bank_account_number"],
  follow_up_questions: [
    {
      field: "bank_account_number",
      question: "আপনার বা পরিবারের কারো কি ব্যাংক পাসবই বা অ্যাকাউন্ট নম্বর মনে আছে? (বা আধার লিঙ্ক করা কোনো অ্যাকাউন্ট আছে?)",
      suggested_answers: ["হ্যাঁ, স্টেট ব্যাংকে আছে", "আধার দিয়ে টাকা তুলতাম", "এখন মনে নেই, পরে দেব"]
    }
  ],
  relief: {
    total: 206300,
    currency: "INR",
    breakdown: [
      {
        scheme_name: "SDRF Norms (2022-26)",
        category: "house",
        item: "Fully Damaged Plain House",
        quantity: 1,
        rate: 120000,
        amount: 120000,
        description: "Standard state disaster relief for total house collapse"
      },
      {
        scheme_name: "SDRF Norms (2022-26)",
        category: "livestock",
        item: "Milch Cattle (Large)",
        quantity: 2,
        rate: 37500,
        amount: 75000,
        description: "Assistance for milch cows/buffaloes lost"
      },
      {
        scheme_name: "PMFBY / SDRF Crop",
        category: "crop",
        item: "Rainfed Paddy Crop (>33% loss)",
        quantity: 0.8,
        rate: 8500,
        amount: 6800,
        description: "Crop input subsidy for small/marginal farmers"
      },
      {
        scheme_name: "SDRF Household Kit",
        category: "household",
        item: "Immediate Clothing & Utensils",
        quantity: 1,
        rate: 4500,
        amount: 4500,
        description: "Emergency relief assistance for washed away belongings"
      }
    ],
    matched_schemes: ["SDRF Relief Fund", "PMFBY Crop Assistance", "PMAY-G Housing Rebuild Priority"]
  },
  proof_suggestions: [
    {
      document: "Aadhaar Card",
      suggestions: [
        "Voter ID, ration card or any other photo ID if available",
        "Attestation by Gram Panchayat Pradhan or Ward Councillor",
        "Apply for quick reprint at local Aadhaar Seva Kendra (draft letter ready below)"
      ]
    },
    {
      document: "Ration Card",
      suggestions: [
        "Name in local PDS / ration dealer beneficiary register",
        "Panchayat attestation of family household members"
      ]
    },
    {
      document: "Land Record / RoR",
      suggestions: [
        "Khatian / Banglarbhumi digital RoR copy from land portal",
        "Geo-tagged photos of plot taken via this app + neighbour attestation",
        "Certificate from Block Land & Land Reforms Office (BL&LRO)"
      ]
    }
  ],
  status: "Draft",
  pdf_url: `/claims/${MOCK_CLAIM_ID}/pdf`,
  photos: [
    {
      id: 101,
      sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      lat: 22.6683,
      lon: 87.7214,
      taken_at: "2026-10-15T09:42:00.000Z",
      verification: {
        status: "complete",
        damage_level: "total",
        gemini_reason: "Mud and tin roof structure completely collapsed into standing floodwater. Water mark exceeds 4 feet on remaining mud wall.",
        gps_valid: true,
        time_valid: true,
        exif_valid: true,
        duplicate: false
      }
    },
    {
      id: 102,
      sha256: "a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e",
      lat: 22.6685,
      lon: 87.7219,
      taken_at: "2026-10-15T09:48:00.000Z",
      verification: {
        status: "complete",
        damage_level: "severe",
        gemini_reason: "Submerged paddy crop showing heavy siltation and decaying standing stalks under river water.",
        gps_valid: true,
        time_valid: true,
        exif_valid: true,
        duplicate: false
      }
    }
  ],
  recordings: [
    { id: 1, status: "processed" }
  ],
  history: [
    { status: "Draft", note: "Initial voice claim recorded in local language", at: "2026-10-15T09:30:00.000Z" }
  ],
  consent_text_version: "v1",
  consent_given_at: "2026-10-15T09:28:00.000Z",
  submitted_at: null,
  created_at: "2026-10-15T09:28:00.000Z",
  updated_at: "2026-10-15T09:50:00.000Z"
};

export const MOCK_STATUS: StatusOut = {
  claim_id: MOCK_CLAIM_ID,
  status: "Submitted",
  updated_at: "2026-10-16T11:15:00.000Z",
  timeline: [
    {
      status: "Submitted",
      note: "Relief claim submitted by claimant. PDF generated and sent to BDO office queue.",
      at: "2026-10-15T10:00:00.000Z"
    },
    {
      status: "Verified",
      note: "Panchayat Field Officer confirmed house damage via geo-tagged photos and neighbours' statement.",
      at: "2026-10-18T14:30:00.000Z"
    },
    {
      status: "Approved",
      note: "Sub-Divisional Magistrate (SDM) approved relief sanction order under SDRF rules.",
      at: "2026-10-22T16:00:00.000Z"
    }
  ]
};

export const MOCK_STAFF_CLAIMS: StaffClaimOut[] = [
  {
    ...MOCK_SAMPLE_CLAIM,
    id: "CLM-2026-WB-8492",
    status: "Submitted",
    vulnerability_flags: {
      is_elderly: false,
      is_disabled: false,
      is_single_mother: true
    },
    photos: [
      {
        ...MOCK_SAMPLE_CLAIM.photos[0],
        duplicate_of_claim_id: null
      },
      {
        ...MOCK_SAMPLE_CLAIM.photos[1],
        duplicate_of_claim_id: null
      }
    ]
  },
  {
    ...MOCK_SAMPLE_CLAIM,
    id: "CLM-2026-WB-8499",
    status: "Submitted",
    fields: {
      ...MOCK_SAMPLE_CLAIM.fields,
      name: "Biren Karmakar",
      phone: "+91 97345 88123",
      village: "Daspur-I",
      losses: [
        { category: "house", item: "partially_damaged_kutcha", quantity: 1, damage_percent: 50 },
        { category: "crop", item: "rainfed", quantity: 1.5, damage_percent: 80 }
      ]
    },
    relief: {
      total: 16750,
      currency: "INR",
      breakdown: [
        { scheme_name: "SDRF Norms", category: "house", item: "Kutcha house partial damage", quantity: 1, rate: 4000, amount: 4000 },
        { scheme_name: "SDRF Crop", category: "crop", item: "Rainfed paddy loss", quantity: 1.5, rate: 8500, amount: 12750 }
      ],
      matched_schemes: ["SDRF Relief"]
    },
    vulnerability_flags: {
      is_elderly: true,
      is_disabled: true,
      is_single_mother: false
    },
    photos: [
      {
        id: 201,
        sha256: "f4a1...99",
        lat: 22.6102,
        lon: 87.7011,
        taken_at: "2026-10-16T11:00:00Z",
        verification: {
          status: "complete",
          damage_level: "partial",
          gemini_reason: "Mud wall crack on eastern boundary. Roof thatch partially blown off.",
          gps_valid: true,
          time_valid: true,
          exif_valid: true,
          duplicate: false
        },
        duplicate_of_claim_id: null
      }
    ]
  },
  {
    ...MOCK_SAMPLE_CLAIM,
    id: "CLM-2026-WB-8510",
    status: "Submitted",
    fields: {
      ...MOCK_SAMPLE_CLAIM.fields,
      name: "Tapan Majhi",
      village: "Keshpur",
      losses: [
        { category: "house", item: "fully_damaged_plain", quantity: 1, damage_percent: 100 }
      ]
    },
    vulnerability_flags: {
      is_elderly: false,
      is_disabled: false,
      is_single_mother: false
    },
    photos: [
      {
        id: 301,
        sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", // duplicate hash!
        lat: 22.6683,
        lon: 87.7214,
        taken_at: "2026-10-15T09:42:00.000Z",
        verification: {
          status: "complete",
          damage_level: "total",
          gemini_reason: "Flagged: Same photo hash already submitted in claim CLM-2026-WB-8492.",
          gps_valid: true,
          time_valid: true,
          exif_valid: true,
          duplicate: true
        },
        duplicate_of_claim_id: "CLM-2026-WB-8492"
      }
    ]
  }
];

// Helper to provide fully localized mock data whenever language switches
export function getLocalizedSampleClaim(t: (key: string, defaultValue?: string) => string): ClaimOut {
  return {
    ...MOCK_SAMPLE_CLAIM,
    transcript: t('mock.sunitaTranscript', MOCK_SAMPLE_CLAIM.transcript),
    follow_up_questions: [
      {
        field: "bank_account_number",
        question: t('mock.qBank', MOCK_SAMPLE_CLAIM.follow_up_questions[0].question),
        suggested_answers: [
          t('mock.ansBank1', 'Yes, I have an account in State Bank'),
          t('mock.ansBank2', 'I used to withdraw cash using Aadhaar (AEPS)'),
          t('mock.ansBank3', "I don't recall now, will provide later")
        ]
      }
    ],
    relief: {
      ...MOCK_SAMPLE_CLAIM.relief!,
      breakdown: [
        {
          ...MOCK_SAMPLE_CLAIM.relief!.breakdown[0],
          item: t('mock.lossHouse', MOCK_SAMPLE_CLAIM.relief!.breakdown[0].item),
          description: t('mock.lossHouseDesc', MOCK_SAMPLE_CLAIM.relief!.breakdown[0].description)
        },
        {
          ...MOCK_SAMPLE_CLAIM.relief!.breakdown[1],
          item: t('mock.lossCattle', MOCK_SAMPLE_CLAIM.relief!.breakdown[1].item),
          description: t('mock.lossCattleDesc', MOCK_SAMPLE_CLAIM.relief!.breakdown[1].description)
        },
        {
          ...MOCK_SAMPLE_CLAIM.relief!.breakdown[2],
          item: t('mock.lossCrop', MOCK_SAMPLE_CLAIM.relief!.breakdown[2].item),
          description: t('mock.lossCropDesc', MOCK_SAMPLE_CLAIM.relief!.breakdown[2].description)
        },
        {
          ...MOCK_SAMPLE_CLAIM.relief!.breakdown[3],
          item: t('mock.lossHousehold', MOCK_SAMPLE_CLAIM.relief!.breakdown[3].item),
          description: t('mock.lossHouseholdDesc', MOCK_SAMPLE_CLAIM.relief!.breakdown[3].description)
        }
      ]
    },
    photos: [
      {
        ...MOCK_SAMPLE_CLAIM.photos[0],
        verification: {
          ...MOCK_SAMPLE_CLAIM.photos[0].verification,
          gemini_reason: t('mock.geminiDamageReason1', MOCK_SAMPLE_CLAIM.photos[0].verification.gemini_reason)
        }
      },
      {
        ...MOCK_SAMPLE_CLAIM.photos[1],
        verification: {
          ...MOCK_SAMPLE_CLAIM.photos[1].verification,
          gemini_reason: t('mock.geminiDamageReason2', MOCK_SAMPLE_CLAIM.photos[1].verification.gemini_reason)
        }
      }
    ]
  };
}
