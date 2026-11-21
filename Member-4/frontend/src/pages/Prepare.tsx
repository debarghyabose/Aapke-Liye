// src/pages/Prepare.tsx
// Pre-Disaster Document Vault & Household Registration (Member 2's Contract)
import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  FileText,
  Upload,
  Camera,
  Trash2,
  CheckCircle2,
  ExternalLink,
  ArrowRight,
  Info,
  Home as HomeIcon,
  User,
  Phone,
  MapPin,
  Lock,
} from 'lucide-react';
import {
  registerHousehold,
  getHousehold,
  uploadVaultDocument,
  deleteVaultDocument,
  fetchVaultFileBlobUrl,
  startDigiLockerMock,
  startDigiLockerFlow,
  getSavedHouseholdId,
} from '../api/client';
import { Household, VaultDocument } from '../types/api';

const DOC_TYPES = [
  { key: 'aadhaar', labelKey: 'prepare.docAadhaar', defaultLabel: 'Aadhaar Card' },
  { key: 'ration_card', labelKey: 'prepare.docRation', defaultLabel: 'Ration Card (NFSA / PDS)' },
  { key: 'land_record', labelKey: 'prepare.docLand', defaultLabel: 'Land Record (Khatian / RoR)' },
  { key: 'bank_passbook', labelKey: 'prepare.docBank', defaultLabel: 'Bank Passbook (DBT linked)' },
];

export const Prepare: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [household, setHousehold] = useState<Household | null>(null);
  const [baselineBlobUrl, setBaselineBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [showDigiLockerModal, setShowDigiLockerModal] = useState<boolean>(false);
  const [digiLockerLoading, setDigiLockerLoading] = useState<boolean>(false);

  // Registration Form State
  const [headName, setHeadName] = useState<string>('Sunita Mondal');
  const [phone, setPhone] = useState<string>('9876543210');
  const [village, setVillage] = useState<string>('Ghatal');
  const [district, setDistrict] = useState<string>('Paschim Medinipur');
  const [state, setState] = useState<string>('');
  const [rationCardNo, setRationCardNo] = useState<string>('NFSA-WB-8839201');

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const baselineInputRef = useRef<HTMLInputElement | null>(null);
  const [currentDocType, setCurrentDocType] = useState<string>('aadhaar');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const digiStatus = params.get('digilocker');
    if (digiStatus === 'added') {
      setMsg(t('prepare.digiLockerImported', 'Sample DigiLocker documents synced into your vault.'));
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (digiStatus === 'denied') {
      setMsg(t('prepare.digiLockerDenied', 'DigiLocker consent was cancelled.'));
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    const load = async () => {
      setLoading(true);
      try {
        const savedId = getSavedHouseholdId();
        if (savedId) {
          const hh = await getHousehold(savedId);
          if (hh) {
            setHousehold(hh);
            setHeadName(hh.head_name);
            setPhone(hh.phone);
            setVillage(hh.village);
            setDistrict(hh.district);
            setState(hh.state);
            setRationCardNo(hh.ration_card_no || '');
          }
        }
      } catch (e) {
        console.warn('Could not load household:', e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [t]);

  useEffect(() => {
    let active = true;
    let objectUrlToRevoke: string | null = null;

    const loadBaseline = async () => {
      if (!household) {
        setBaselineBlobUrl(null);
        return;
      }
      const baselineDoc = (household.documents || []).find((d) => d.doc_type === 'baseline_photo');
      if (baselineDoc) {
        const blobUrl = await fetchVaultFileBlobUrl(household.id, baselineDoc.id);
        if (active && blobUrl) {
          objectUrlToRevoke = blobUrl;
          setBaselineBlobUrl(blobUrl);
          return;
        }
      }
      if (household.baseline_photo_url) {
        if (household.baseline_photo_url.startsWith('blob:') || household.baseline_photo_url.startsWith('data:')) {
          if (active) setBaselineBlobUrl(household.baseline_photo_url);
        } else {
          const blobUrl = await fetchVaultFileBlobUrl(household.id, household.baseline_photo_url);
          if (active && blobUrl) {
            objectUrlToRevoke = blobUrl;
            setBaselineBlobUrl(blobUrl);
          }
        }
      } else {
        if (active) setBaselineBlobUrl(null);
      }
    };

    loadBaseline();

    return () => {
      active = false;
      if (objectUrlToRevoke && objectUrlToRevoke.startsWith('blob:')) {
        URL.revokeObjectURL(objectUrlToRevoke);
      }
    };
  }, [household]);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMsg(null);
    try {
      const hh = await registerHousehold({
        head_name: headName,
        phone,
        village,
        district,
        state,
        ration_card_no: rationCardNo,
      });
      setHousehold(hh);
      setMsg(t('prepare.registeredSuccess', 'Household successfully registered & token secured!'));
      setTimeout(() => setMsg(null), 4000);
    } catch (err: any) {
      setMsg(err.message || 'Failed to register household');
    } finally {
      setSaving(false);
    }
  };

  const handleUploadClick = (docType: string) => {
    setCurrentDocType(docType);
    fileInputRef.current?.click();
  };

  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !household) return;
    try {
      const doc = await uploadVaultDocument(household.id, file, currentDocType);
      const updated = await getHousehold(household.id);
      if (updated) setHousehold(updated);
      setMsg(t('prepare.docUploaded', 'Document saved to encrypted vault.'));
      setTimeout(() => setMsg(null), 3000);
    } catch (err: any) {
      setMsg(err.message || 'Upload failed');
    }
  };

  const handleBaselinePhotoSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !household) return;
    try {
      await uploadVaultDocument(household.id, file, 'baseline_photo');
      const updated = await getHousehold(household.id);
      if (updated) setHousehold(updated);
      setMsg(t('prepare.baselineUploaded', 'Baseline property photo saved for before/after comparison.'));
      setTimeout(() => setMsg(null), 3000);
    } catch (err: any) {
      setMsg(err.message || 'Baseline photo upload failed');
    }
  };

  const handleDelete = async (docId: string) => {
    if (!household) return;
    try {
      await deleteVaultDocument(household.id, docId);
      const updated = await getHousehold(household.id);
      if (updated) setHousehold(updated);
    } catch (err: any) {
      setMsg(err.message || 'Delete failed');
    }
  };

  const handleDigiLockerClick = async () => {
    if (!household) return;
    setDigiLockerLoading(true);
    try {
      const flow = await startDigiLockerFlow(household.id);
      if (flow && flow.consent_url) {
        window.location.href = flow.consent_url;
        return;
      }
    } catch (e) {
      console.warn('Backend DigiLocker flow unavailable, opening in-app demo modal:', e);
    } finally {
      setDigiLockerLoading(false);
    }
    setShowDigiLockerModal(true);
  };

  const handleDigiLockerCallback = async () => {
    if (!household) return;
    setDigiLockerLoading(true);
    try {
      await startDigiLockerMock(household.id);
      const updated = await getHousehold(household.id);
      if (updated) setHousehold(updated);
      setShowDigiLockerModal(false);
      setMsg(t('prepare.digiLockerImported', 'Sample DigiLocker documents synced into your vault.'));
      setTimeout(() => setMsg(null), 4000);
    } finally {
      setDigiLockerLoading(false);
    }
  };

  return (
    <div className="page-container" style={{ maxWidth: '900px', margin: '0 auto', padding: '24px 16px' }}>
      {/* Hidden file inputs */}
      <input
        type="file"
        ref={fileInputRef}
        style={{ display: 'none' }}
        onChange={handleFileSelected}
        accept=".pdf,image/*"
      />
      <input
        type="file"
        ref={baselineInputRef}
        style={{ display: 'none' }}
        onChange={handleBaselinePhotoSelected}
        accept="image/*"
        capture="environment"
      />

      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: '32px' }}>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: '#E8F5E9',
            color: 'var(--primary)',
            padding: '6px 14px',
            borderRadius: '999px',
            fontSize: '0.88rem',
            fontWeight: 700,
            marginBottom: '12px',
          }}
        >
          <ShieldCheck size={18} />
          <span>{t('prepare.badge', 'Pre-Disaster Safeguard')}</span>
        </div>
        <h1
          style={{
            fontFamily: 'var(--font-serif)',
            fontSize: 'clamp(1.75rem, 4vw, 2.4rem)',
            color: 'var(--secondary)',
            margin: '0 0 10px 0',
          }}
        >
          {t('prepare.title', 'Disaster Document Vault')}
        </h1>
        <p style={{ maxWidth: '640px', margin: '0 auto', color: 'var(--muted)', fontSize: '1rem', lineHeight: 1.5 }}>
          {t(
            'prepare.subtitle',
            'Save your family identity papers and house baseline photos before floods arrive. When a disaster hits, you can file a claim instantly with zero lost document delays.'
          )}
        </p>
      </div>

      {msg && (
        <div
          role="alert"
          style={{
            backgroundColor: 'var(--primary)',
            color: '#FFFFFF',
            padding: '12px 18px',
            borderRadius: '8px',
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            fontWeight: 600,
          }}
        >
          <CheckCircle2 size={20} />
          <span>{msg}</span>
        </div>
      )}

      {/* STEP 1: Household Registration Card */}
      <div className="card-soft" style={{ padding: '24px', marginBottom: '28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
          <HomeIcon size={24} style={{ color: 'var(--accent)' }} />
          <h2 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--secondary)' }}>
            {household
              ? t('prepare.householdRegisteredTitle', 'Your Registered Household')
              : t('prepare.householdRegisterTitle', '1. Register Your Household')}
          </h2>
          {household && (
            <span
              style={{
                marginLeft: 'auto',
                backgroundColor: 'var(--cream)',
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '0.8rem',
                fontFamily: 'monospace',
                fontWeight: 700,
                color: 'var(--secondary)',
              }}
            >
              ID: {household.id}
            </span>
          )}
        </div>

        <form onSubmit={handleRegister}>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
              gap: '16px',
              marginBottom: '16px',
            }}
          >
            <div>
              <label style={{ display: 'block', fontSize: '0.88rem', fontWeight: 600, marginBottom: '6px' }}>
                {t('prepare.headName', 'Head of Household / Claimant Name')}
              </label>
              <input
                type="text"
                value={headName}
                onChange={(e) => setHeadName(e.target.value)}
                required
                className="input-field"
                style={{ width: '100%', padding: '10px 14px', borderRadius: '6px', border: '1px solid var(--border)' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.88rem', fontWeight: 600, marginBottom: '6px' }}>
                {t('prepare.phone', 'Mobile Phone Number')}
              </label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                required
                className="input-field"
                style={{ width: '100%', padding: '10px 14px', borderRadius: '6px', border: '1px solid var(--border)' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.88rem', fontWeight: 600, marginBottom: '6px' }}>
                {t('prepare.village', 'Village / Gram Panchayat')}
              </label>
              <input
                type="text"
                value={village}
                onChange={(e) => setVillage(e.target.value)}
                required
                className="input-field"
                style={{ width: '100%', padding: '10px 14px', borderRadius: '6px', border: '1px solid var(--border)' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.88rem', fontWeight: 600, marginBottom: '6px' }}>
                {t('prepare.district', 'District')}
              </label>
              <input
                type="text"
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
                required
                className="input-field"
                style={{ width: '100%', padding: '10px 14px', borderRadius: '6px', border: '1px solid var(--border)' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.88rem', fontWeight: 600, marginBottom: '6px' }}>
                {t('prepare.state', 'State')}
              </label>
              <input
                type="text"
                value={state}
                onChange={(e) => setState(e.target.value)}
                required
                className="input-field"
                style={{ width: '100%', padding: '10px 14px', borderRadius: '6px', border: '1px solid var(--border)' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.88rem', fontWeight: 600, marginBottom: '6px' }}>
                {t('prepare.rationCardNo', 'Ration Card Number (NFSA)')}
              </label>
              <input
                type="text"
                value={rationCardNo}
                onChange={(e) => setRationCardNo(e.target.value)}
                className="input-field"
                style={{ width: '100%', padding: '10px 14px', borderRadius: '6px', border: '1px solid var(--border)' }}
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
            <button
              type="submit"
              disabled={saving}
              className="btn-primary"
              style={{
                minHeight: '48px',
                padding: '12px 24px',
                borderRadius: '8px',
                fontWeight: 700,
                backgroundColor: 'var(--accent)',
                color: '#FFFFFF',
                border: 'none',
                cursor: 'pointer',
              }}
            >
              {saving
                ? t('common.saving', 'Saving…')
                : household
                ? t('prepare.updateHousehold', 'Update Household Details')
                : t('prepare.saveHousehold', 'Save Household to Vault')}
            </button>

            {household && (
              <button
                type="button"
                onClick={() => navigate('/claim')}
                className="btn-outline-pill"
                style={{
                  minHeight: '48px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '12px 20px',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                <span>{t('prepare.startClaimWithThis', 'Use This Household to File Claim')}</span>
                <ArrowRight size={18} />
              </button>
            )}
          </div>
        </form>
      </div>

      {/* STEP 2: Pre-Disaster Document Cards & DigiLocker */}
      {household ? (
        <div className="card-soft" style={{ padding: '24px', marginBottom: '28px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--secondary)' }}>
                {t('prepare.docsTitle', '2. My Saved Documents')}
              </h2>
              <p style={{ margin: '4px 0 0 0', fontSize: '0.88rem', color: 'var(--muted)' }}>
                {t('prepare.docsSubtitle', 'Uploaded documents are encrypted and count as available during claim verification.')}
              </p>
            </div>

            {/* DigiLocker Trigger Button */}
            <button
              type="button"
              onClick={handleDigiLockerClick}
              disabled={digiLockerLoading}
              style={{
                minHeight: '48px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                backgroundColor: '#0B4EA2',
                color: '#FFFFFF',
                padding: '10px 18px',
                borderRadius: '8px',
                fontWeight: 700,
                border: 'none',
                cursor: 'pointer',
                boxShadow: '0 2px 4px rgba(11,78,162,0.2)',
              }}
            >
              <ExternalLink size={18} />
              <span>{digiLockerLoading ? 'Connecting…' : t('prepare.digiLockerBtn', 'Import from DigiLocker (Demo)')}</span>
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
            {DOC_TYPES.map((dt) => {
              const uploadedDoc = (household.documents || []).find((d) => d.doc_type === dt.key);
              return (
                <div
                  key={dt.key}
                  style={{
                    border: uploadedDoc ? '2px solid var(--primary)' : '1px dashed var(--border)',
                    borderRadius: '10px',
                    padding: '16px',
                    backgroundColor: uploadedDoc ? '#F9FDF9' : '#FFFFFF',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    minHeight: '130px',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <span style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--secondary)' }}>
                        {t(dt.labelKey, dt.defaultLabel)}
                      </span>
                      {uploadedDoc && (
                        <span
                          style={{
                            fontSize: '0.75rem',
                            padding: '2px 8px',
                            borderRadius: '999px',
                            backgroundColor: uploadedDoc.source === 'digilocker_mock' ? '#E3F2FD' : '#E8F5E9',
                            color: uploadedDoc.source === 'digilocker_mock' ? '#0B4EA2' : 'var(--primary)',
                            fontWeight: 700,
                          }}
                        >
                          {uploadedDoc.source === 'digilocker_mock' ? 'DigiLocker (demo)' : 'Vault ✓'}
                        </span>
                      )}
                    </div>
                    {uploadedDoc ? (
                      <p style={{ margin: '8px 0 0 0', fontSize: '0.85rem', color: 'var(--muted)' }}>
                        {uploadedDoc.filename}
                      </p>
                    ) : (
                      <p style={{ margin: '8px 0 0 0', fontSize: '0.82rem', color: 'var(--muted)' }}>
                        {t('prepare.notUploaded', 'No copy saved yet.')}
                      </p>
                    )}
                  </div>

                  <div style={{ display: 'flex', gap: '10px', marginTop: '12px' }}>
                    {uploadedDoc ? (
                      <button
                        type="button"
                        onClick={() => handleDelete(uploadedDoc.id)}
                        style={{
                          minHeight: '44px',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          color: '#C62828',
                          background: 'none',
                          border: 'none',
                          cursor: 'pointer',
                          fontWeight: 600,
                          fontSize: '0.85rem',
                        }}
                      >
                        <Trash2 size={16} />
                        <span>{t('common.delete', 'Delete')}</span>
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleUploadClick(dt.key)}
                        className="btn-outline-pill"
                        style={{
                          minHeight: '44px',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '8px 16px',
                          fontSize: '0.85rem',
                          cursor: 'pointer',
                        }}
                      >
                        <Upload size={16} />
                        <span>{t('prepare.uploadBtn', 'Upload file')}</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      {/* STEP 3: Baseline Photos Card */}
      {household ? (
        <div className="card-soft" style={{ padding: '24px', marginBottom: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <Camera size={24} style={{ color: 'var(--primary)' }} />
            <div>
              <h2 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--secondary)' }}>
                {t('prepare.baselineTitle', '3. Baseline Property Photos')}
              </h2>
              <p style={{ margin: '4px 0 0 0', fontSize: '0.88rem', color: 'var(--muted)' }}>
                {t(
                  'prepare.baselineSubtitle',
                  'Take normal-time photos of your house, cattle shed, or fields. In flood time, Gemini compares current photos against this baseline.'
                )}
              </p>
            </div>
          </div>

          {household.baseline_photo_url ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '20px', flexWrap: 'wrap' }}>
              <img
                src={baselineBlobUrl || household.baseline_photo_url}
                alt="Baseline property"
                style={{ width: '160px', height: '120px', objectFit: 'cover', borderRadius: '8px', border: '2px solid var(--primary)' }}
              />
              <div>
                <span
                  style={{
                    display: 'inline-block',
                    backgroundColor: '#E8F5E9',
                    color: 'var(--primary)',
                    padding: '4px 10px',
                    borderRadius: '6px',
                    fontWeight: 700,
                    fontSize: '0.85rem',
                    marginBottom: '8px',
                  }}
                >
                  {t('prepare.baselineActive', 'Baseline Photo Active')}
                </span>
                <p style={{ margin: '0 0 10px 0', fontSize: '0.88rem', color: 'var(--muted)' }}>
                  {t('prepare.baselineReady', 'Ready to provide side-by-side verification during disaster claim review.')}
                </p>
                <button
                  type="button"
                  onClick={() => baselineInputRef.current?.click()}
                  className="btn-outline-pill"
                  style={{ minHeight: '44px', padding: '8px 16px', fontSize: '0.85rem', cursor: 'pointer' }}
                >
                  {t('prepare.replacePhoto', 'Replace photo')}
                </button>
              </div>
            </div>
          ) : (
            <div
              style={{
                border: '2px dashed var(--border)',
                borderRadius: '10px',
                padding: '30px 20px',
                textAlign: 'center',
                backgroundColor: '#FAF7F2',
              }}
            >
              <Camera size={36} style={{ color: 'var(--muted)', margin: '0 auto 12px auto' }} />
              <h3 style={{ margin: '0 0 6px 0', fontSize: '1rem', color: 'var(--secondary)' }}>
                {t('prepare.noBaselinePhoto', 'No baseline photo saved yet')}
              </h3>
              <p style={{ margin: '0 auto 16px auto', fontSize: '0.88rem', color: 'var(--muted)', maxWidth: '450px' }}>
                {t(
                  'prepare.baselineInstructions',
                  'Photograph your dwelling now while it is intact. It serves as irrefutable before-evidence.'
                )}
              </p>
              <button
                type="button"
                onClick={() => baselineInputRef.current?.click()}
                className="btn-primary"
                style={{
                  minHeight: '48px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '10px 22px',
                  borderRadius: '8px',
                  fontWeight: 700,
                  backgroundColor: 'var(--primary)',
                  color: '#FFFFFF',
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                <Camera size={18} />
                <span>{t('prepare.snapBaseline', 'Snap Baseline Photo')}</span>
              </button>
            </div>
          )}
        </div>
      ) : null}

      {/* DIGILOCKER MOCK MODAL (CLEARLY LABELLED DEMO) */}
      {showDigiLockerModal && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '16px',
          }}
        >
          <div
            style={{
              backgroundColor: '#FFFFFF',
              borderRadius: '12px',
              maxWidth: '480px',
              width: '100%',
              padding: '24px',
              boxShadow: '0 12px 32px rgba(0,0,0,0.2)',
            }}
          >
            {/* Demo Banner */}
            <div
              style={{
                backgroundColor: '#FFF3E0',
                border: '1.5px solid #FF9800',
                borderRadius: '8px',
                padding: '10px 14px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                color: '#B26A00',
                fontWeight: 700,
                fontSize: '0.9rem',
                marginBottom: '16px',
              }}
            >
              <Info size={18} />
              <span>{t('prepare.digiLockerMockBanner', 'Demo: DigiLocker Mock Consent Screen')}</span>
            </div>

            <div style={{ textAlign: 'center', marginBottom: '18px' }}>
              <div
                style={{
                  width: '56px',
                  height: '56px',
                  backgroundColor: '#0B4EA2',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#FFFFFF',
                  margin: '0 auto 12px auto',
                }}
              >
                <Lock size={28} />
              </div>
              <h3 style={{ margin: '0 0 6px 0', fontSize: '1.25rem', color: '#0B4EA2' }}>
                DigiLocker Consent (Government of India)
              </h3>
              <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--muted)' }}>
                Aapke Liye requests consent to import your verified Aadhaar and Ration Card for disaster relief claim registration.
              </p>
            </div>

            <div
              style={{
                backgroundColor: 'var(--cream)',
                borderRadius: '8px',
                padding: '14px',
                marginBottom: '20px',
                fontSize: '0.85rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <CheckCircle2 size={16} style={{ color: 'var(--primary)' }} />
                <span>UIDAI Issued Aadhaar Card (Signed XML)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle2 size={16} style={{ color: 'var(--primary)' }} />
                <span>NFSA State Department of Food & Supplies Card</span>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button
                type="button"
                onClick={() => setShowDigiLockerModal(false)}
                className="btn-outline-pill"
                style={{ minHeight: '44px', padding: '10px 18px', fontWeight: 600, cursor: 'pointer' }}
              >
                {t('common.cancel', 'Cancel')}
              </button>
              <button
                type="button"
                onClick={handleDigiLockerCallback}
                disabled={digiLockerLoading}
                style={{
                  minHeight: '44px',
                  backgroundColor: '#0B4EA2',
                  color: '#FFFFFF',
                  padding: '10px 22px',
                  borderRadius: '999px',
                  fontWeight: 700,
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                {digiLockerLoading ? 'Importing…' : t('prepare.giveConsent', 'I Consent (Demo Import)')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Prepare;
