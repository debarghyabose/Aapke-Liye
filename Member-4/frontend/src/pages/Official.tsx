// src/pages/Official.tsx
import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ShieldCheck,
  AlertTriangle,
  Layers,
  CheckCircle2,
  XCircle,
  Filter,
} from 'lucide-react';
import {
  getStaffClaim,
  getStaffClaimsList,
  updateStaffStatus,
  DEMO_MODE,
  errorText,
  getStaffKey,
  setStaffKey,
} from '../api/client';
import { StaffClaimOut } from '../types/api';
import { LiveMap } from '../components/LiveMap';
import { MOCK_STAFF_CLAIMS } from '../mocks/sampleData';

export const Official: React.FC = () => {
  const { t } = useTranslation();
  const [claimsList, setClaimsList] = useState<StaffClaimOut[]>([]);
  const [selectedClaim, setSelectedClaim] = useState<StaffClaimOut | null>(null);
  const [filterVulnerableOnly, setFilterVulnerableOnly] = useState<boolean>(false);
  const [statusActionNote, setStatusActionNote] = useState<string>('');
  const [staffActionSuccess, setStaffActionSuccess] = useState<string | null>(null);
  const [staffError, setStaffError] = useState<string | null>(null);
  const [keyInput, setKeyInput] = useState<string>(getStaffKey());
  const [mapRefresh, setMapRefresh] = useState<number>(0);

  useEffect(() => {
    loadClaims();
  }, []);

  const loadClaims = async () => {
    try {
      setStaffError(null);
      const list = await getStaffClaimsList();
      setClaimsList(list);
      setSelectedClaim(list[0] || null);
    } catch (e) {
      if (DEMO_MODE) {
        setClaimsList(MOCK_STAFF_CLAIMS);
        setSelectedClaim(MOCK_STAFF_CLAIMS[0]);
      } else {
        setClaimsList([]);
        setSelectedClaim(null);
        setStaffError(errorText(e));
      }
    }
  };

  const handleSelectClaim = async (id: string) => {
    try {
      const claim = await getStaffClaim(id);
      setSelectedClaim(claim);
    } catch (e) {
      if (!DEMO_MODE) setStaffError(errorText(e));
      const found = claimsList.find((c) => c.id === id);
      if (found) setSelectedClaim(found);
    }
  };

  const handleUpdateStatus = async (newStatus: string) => {
    if (!selectedClaim) return;
    if (!DEMO_MODE) {
      try {
        setStaffError(null);
        await updateStaffStatus(selectedClaim.id, newStatus, statusActionNote);
        const fresh = await getStaffClaim(selectedClaim.id);
        setSelectedClaim(fresh);
        setClaimsList((list) => list.map((c) => (c.id === fresh.id ? fresh : c)));
        setStaffActionSuccess(`Status updated to "${newStatus}" for Claim ${fresh.id}. Audit logged.`);
        setStatusActionNote('');
        setTimeout(() => setStaffActionSuccess(null), 4000);
      } catch (e) {
        setStaffError(errorText(e));
      }
      return;
    }
    const msg = t('official.auditSuccess', {
      status: newStatus,
      id: selectedClaim.id,
      defaultValue: `Status updated to "${newStatus}" for Claim ${selectedClaim.id}. Audit logged.`,
    });
    setStaffActionSuccess(msg);
    setSelectedClaim({
      ...selectedClaim,
      status: newStatus as any,
      history: [
        ...selectedClaim.history,
        {
          status: newStatus,
          note: statusActionNote || `Status updated by Revenue Officer to ${newStatus}`,
          at: new Date().toISOString(),
        },
      ],
    });
    setStatusActionNote('');
    setTimeout(() => setStaffActionSuccess(null), 4000);
  };

  const displayedClaims = claimsList.filter((c) => {
    if (!filterVulnerableOnly) return true;
    const flags = c.vulnerability_flags;
    return flags?.is_elderly || flags?.is_disabled || flags?.is_single_mother;
  });

  return (
    <div
      style={{
        maxWidth: '1360px',
        margin: '24px auto 60px auto',
        padding: '0 clamp(14px, 3.5vw, 28px)',
      }}
    >
      {!DEMO_MODE && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setStaffKey(keyInput);
            loadClaims();
            setMapRefresh((n) => n + 1);
          }}
          style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center', marginBottom: '16px' }}
        >
          <label htmlFor="staff-key" style={{ fontWeight: 700 }}>
            {t('official.staffKey', 'Staff key')}
          </label>
          <input
            id="staff-key"
            type="password"
            autoComplete="off"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            style={{ flex: '1 1 220px', minHeight: '44px', padding: '8px 14px', borderRadius: '10px', border: '1.5px solid var(--border)' }}
          />
          <button type="submit" className="btn-pill btn-outline-pill" style={{ minHeight: '44px', padding: '8px 20px', fontWeight: 800 }}>
            {t('official.loadClaims', 'Load claims')}
          </button>
          {staffError && (
            <span role="alert" style={{ color: '#8A1C1C', fontWeight: 700, flexBasis: '100%' }}>
              {staffError}
            </span>
          )}
        </form>
      )}

      {/* Official Header */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1.5px solid var(--border)',
          paddingBottom: '20px',
          marginBottom: '28px',
          gap: '16px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--primary)' }}>
            <ShieldCheck size={24} />
            <span style={{ fontWeight: 800, fontSize: '0.92rem', textTransform: 'uppercase', letterSpacing: '0.8px' }}>
              {t('official.dept', 'Government of West Bengal · Disaster Management Cell')}
            </span>
          </div>
          <h1 style={{ fontSize: 'clamp(2.1rem, 3.6vw, 2.8rem)', margin: '6px 0 0 0', color: 'var(--text)', fontWeight: 800 }}>
            {t('official.title', 'Official Verification Dashboard')}
          </h1>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span
            style={{
              backgroundColor: '#FFFFFF',
              border: '1.5px solid var(--border)',
              borderRadius: '999px',
              padding: '8px 20px',
              fontSize: '0.94rem',
              fontWeight: 800,
              color: 'var(--primary)',
              boxShadow: '0 2px 8px rgba(26, 75, 117, 0.06)',
            }}
          >
            {t('official.officer', 'Officer: Ghatal Sub-Division BDO')}
          </span>
        </div>
      </div>

      {staffActionSuccess && (
        <div
          role="status"
          style={{
            backgroundColor: 'rgba(42, 123, 76, 0.12)',
            color: 'var(--leaf)',
            border: '1.5px solid var(--border)',
            padding: '16px 22px',
            borderRadius: '14px',
            marginBottom: '26px',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            fontSize: '1rem',
          }}
        >
          <CheckCircle2 size={22} />
          <span>{staffActionSuccess}</span>
        </div>
      )}

      {/* Grid: Left Column (Map & Priority Queue), Right Column (Claim Detail Inspector) */}
      <div
        className="official-main-grid"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '24px',
        }}
      >
        {/* LEFT COLUMN: OpenStreetMap Heatmap Mock + Priority List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
          {/* District Damage Heatmap with Flowing Water effect */}
          <div className="card-soft" style={{ padding: '26px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Layers size={20} style={{ color: 'var(--primary)' }} />
                <h3 style={{ margin: 0, fontSize: '1.2rem', color: 'var(--text)' }}>
                  {t('official.heatmapTitle', 'District Flood Inundation Heatmap')}
                </h3>
              </div>
              <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                {DEMO_MODE
                  ? t('official.heatmapSub', 'OpenStreetMap · Paschim Medinipur')
                  : t('official.heatmapLive', 'Live · OpenStreetMap + Copernicus EMS flood map')}
              </span>
            </div>

            {!DEMO_MODE ? (
              <LiveMap onSelectClaim={handleSelectClaim} refreshKey={mapRefresh} />
            ) : (
            <>
            {/* Interactive SVG Map Canvas */}
            <div
              style={{
                width: '100%',
                height: '240px',
                borderRadius: '14px',
                backgroundColor: 'var(--surface-water)',
                position: 'relative',
                overflow: 'hidden',
                border: '1.5px solid var(--border)',
              }}
            >
              <svg width="100%" height="100%" style={{ position: 'absolute', inset: 0 }}>
                {/* River Shilabati meandering */}
                <path
                  d="M 0 140 Q 120 180, 240 120 T 480 160 T 700 130"
                  fill="none"
                  stroke="var(--water-deep)"
                  strokeWidth="28"
                  opacity="0.65"
                />
                <ellipse cx="180" cy="130" rx="90" ry="60" fill="var(--accent)" opacity="0.35" />
                <ellipse cx="380" cy="150" rx="110" ry="70" fill="var(--accent)" opacity="0.25" />

                <circle cx="180" cy="130" r="16" fill="var(--accent)" opacity="0.95" />
                <circle cx="340" cy="145" r="14" fill="var(--leaf)" opacity="0.95" />
                <circle cx="410" cy="160" r="12" fill="var(--primary)" opacity="0.95" />
              </svg>

              {/* Map Pins */}
              <button
                onClick={() => handleSelectClaim('CLM-2026-WB-8492')}
                style={{
                  position: 'absolute',
                  top: '110px',
                  left: '160px',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: 0,
                  transform: 'translate(-50%, -50%)',
                }}
                title="Ghatal Block-II - High Severity Total Loss"
              >
                <div
                  style={{
                    backgroundColor: 'var(--accent)',
                    color: '#FFFFFF',
                    padding: '5px 12px',
                    borderRadius: '999px',
                    fontSize: '0.78rem',
                    fontWeight: 700,
                    boxShadow: '0 2px 8px rgba(0,0,0,0.25)',
                    border: '2px solid #FFFFFF',
                  }}
                >
                  {t('official.pinGhatal', '📍 Ghatal (Sunita M.)')}
                </div>
              </button>

              <button
                onClick={() => handleSelectClaim('CLM-2026-WB-8499')}
                style={{
                  position: 'absolute',
                  top: '125px',
                  left: '320px',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: 0,
                  transform: 'translate(-50%, -50%)',
                }}
                title="Daspur - Elderly & Disabled"
              >
                <div
                  style={{
                    backgroundColor: 'var(--primary)',
                    color: '#FFFFFF',
                    padding: '5px 12px',
                    borderRadius: '999px',
                    fontSize: '0.78rem',
                    fontWeight: 700,
                    boxShadow: '0 2px 8px rgba(0,0,0,0.25)',
                    border: '2px solid #FFFFFF',
                  }}
                >
                  {t('official.pinDaspur', '📍 Daspur (Biren K.)')}
                </div>
              </button>

              <div
                style={{
                  position: 'absolute',
                  bottom: '10px',
                  right: '10px',
                  backgroundColor: 'rgba(255,255,255,0.95)',
                  padding: '4px 12px',
                  borderRadius: '999px',
                  fontSize: '0.75rem',
                  color: 'var(--text)',
                  fontWeight: 700,
                  boxShadow: '0 2px 6px rgba(0,0,0,0.1)',
                }}
              >
                🟠 {t('official.legendCollapse', 'Total Collapse')} · 🟢{' '}
                {t('official.legendInundation', 'Severe Inundation')}
              </div>
            </div>
            </>
            )}
          </div>

          {/* Priority List (Elderly, Disabled, Single Mothers) */}
          <div className="card-soft" style={{ padding: '26px' }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '18px',
              }}
            >
              <div>
                <h3 style={{ margin: 0, fontSize: '1.2rem', color: 'var(--text)' }}>
                  {t('official.claimsQueueTitle', 'Claims Queue')}
                </h3>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  {t('official.claimsQueueSub', 'Auto-prioritised by Social Vulnerability Norms')}
                </span>
              </div>

              <button
                onClick={() => setFilterVulnerableOnly(!filterVulnerableOnly)}
                className="btn-outline-pill"
                style={{
                  padding: '6px 16px',
                  fontSize: '0.85rem',
                  minHeight: '36px',
                  backgroundColor: filterVulnerableOnly ? 'var(--primary)' : '#FFFFFF',
                  color: filterVulnerableOnly ? '#FFFFFF' : 'var(--primary)',
                }}
              >
                <Filter size={13} />
                <span>{t('official.vulnerableOnly', 'Vulnerable Only')}</span>
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {displayedClaims.map((c) => {
                const isSelected = selectedClaim?.id === c.id;
                const v = c.vulnerability_flags;
                return (
                  <div
                    key={c.id}
                    onClick={() => handleSelectClaim(c.id)}
                    style={{
                      padding: '16px 20px',
                      borderRadius: '14px',
                      border: isSelected ? '2.5px solid var(--primary)' : '1px solid var(--border)',
                      backgroundColor: isSelected ? 'rgba(26, 75, 117, 0.08)' : '#FFFFFF',
                      cursor: 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <strong style={{ color: 'var(--text)', fontSize: '1.05rem' }}>
                        {c.fields.name || 'Applicant'}
                      </strong>
                      <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: 700 }}>
                        {c.id}
                      </span>
                    </div>

                    <div style={{ fontSize: '0.88rem', color: 'var(--text-muted)' }}>
                      {t('official.villageLabel', { village: c.fields.village, defaultValue: `Village: ${c.fields.village}` })} ·{' '}
                      {t('official.estLabel', {
                        amount: c.relief?.total ? c.relief.total.toLocaleString('en-IN') : '0',
                        defaultValue: `Est: ₹${c.relief?.total ? c.relief.total.toLocaleString('en-IN') : '0'}`,
                      })}
                    </div>

                    {/* Vulnerability badges */}
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {v?.is_single_mother && (
                        <span
                          style={{
                            backgroundColor: 'rgba(244, 96, 54, 0.12)',
                            color: 'var(--accent)',
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            padding: '3px 10px',
                            borderRadius: '999px',
                          }}
                        >
                          {t('official.singleMotherPriority', '★ Single Mother Priority')}
                        </span>
                      )}
                      {v?.is_elderly && (
                        <span
                          style={{
                            backgroundColor: 'rgba(231, 111, 81, 0.14)',
                            color: 'var(--earth)',
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            padding: '3px 10px',
                            borderRadius: '999px',
                          }}
                        >
                          {t('official.elderlyHousehold', '★ Elderly Household')}
                        </span>
                      )}
                      {v?.is_disabled && (
                        <span
                          style={{
                            backgroundColor: 'rgba(42, 123, 76, 0.14)',
                            color: 'var(--leaf)',
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            padding: '3px 10px',
                            borderRadius: '999px',
                          }}
                        >
                          {t('official.divyangDisabled', '★ Divyang / Disabled')}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Selected Claim Detail Inspector */}
        {selectedClaim ? (
          <div className="card-soft" style={{ padding: '36px 32px' }}>
            {/* Header info */}
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                borderBottom: '1.5px solid var(--border)',
                paddingBottom: '22px',
                marginBottom: '26px',
                gap: '12px',
              }}
            >
              <div>
                <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  {t('official.dossierTitle', 'Verification Dossier')}
                </span>
                <h2 style={{ fontSize: '1.75rem', margin: '4px 0 0 0', color: 'var(--primary)' }}>
                  {selectedClaim.fields.name} — {selectedClaim.id}
                </h2>
                <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                  {t('official.mobile', { phone: selectedClaim.fields.phone, defaultValue: `Mobile: ${selectedClaim.fields.phone}` })} ·{' '}
                  {t('official.villageLabel', {
                    village: `${selectedClaim.fields.village}, ${selectedClaim.fields.district}`,
                    defaultValue: `Village: ${selectedClaim.fields.village}, ${selectedClaim.fields.district}`,
                  })}
                </div>
              </div>

              <span
                style={{
                  backgroundColor: 'var(--bg-alt)',
                  border: '1px solid var(--border)',
                  color: 'var(--primary)',
                  padding: '6px 18px',
                  borderRadius: '999px',
                  fontWeight: 700,
                  fontSize: '0.9rem',
                }}
              >
                Status: {selectedClaim.status}
              </span>
            </div>

            {/* Photos & Duplicate Inspection */}
            <div style={{ marginBottom: '28px' }}>
              <h3 style={{ fontSize: '1.2rem', marginBottom: '14px', color: 'var(--text)' }}>
                {t('official.damagePhotosTitle', 'Damage Photos & Verification Flags')}
              </h3>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {selectedClaim.photos.map((photo) => (
                  <div
                    key={photo.id}
                    style={{
                      border: photo.duplicate_of_claim_id ? '2px solid var(--accent)' : '1px solid var(--border)',
                      borderRadius: '16px',
                      padding: '18px',
                      backgroundColor: photo.duplicate_of_claim_id ? 'rgba(244, 96, 54, 0.06)' : '#FFFFFF',
                    }}
                  >
                    {/* Duplicate photo warning banner if present */}
                    {photo.duplicate_of_claim_id && (
                      <div
                        style={{
                          backgroundColor: '#FDEAE8',
                          color: 'var(--accent)',
                          padding: '10px 16px',
                          borderRadius: '12px',
                          fontSize: '0.88rem',
                          fontWeight: 700,
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          marginBottom: '12px',
                        }}
                      >
                        <AlertTriangle size={18} />
                        <span>
                          {t('official.duplicateWarning', {
                            id: photo.duplicate_of_claim_id,
                            defaultValue: `DUPLICATE PHOTO WARNING: Identical image SHA-256 already submitted in Claim #${photo.duplicate_of_claim_id}!`,
                          })}
                        </span>
                      </div>
                    )}

                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', alignItems: 'center', marginBottom: '10px' }}>
                      <span style={{ fontWeight: 700, fontSize: '0.92rem', color: 'var(--text)' }}>
                        {t('official.photoNum', { id: photo.id, defaultValue: `Photo #${photo.id}` })}
                      </span>
                      <span
                        style={{
                          backgroundColor: 'rgba(42, 123, 76, 0.12)',
                          color: 'var(--leaf)',
                          fontSize: '0.8rem',
                          fontWeight: 700,
                          padding: '3px 12px',
                          borderRadius: '999px',
                        }}
                      >
                        {t('official.gpsMatched', {
                          lat: photo.lat?.toFixed(3),
                          lon: photo.lon?.toFixed(3),
                          defaultValue: `✓ GPS Matched (${photo.lat?.toFixed(3)}, ${photo.lon?.toFixed(3)})`,
                        })}
                      </span>
                      <span
                        style={{
                          backgroundColor: 'rgba(26, 75, 117, 0.1)',
                          color: 'var(--primary)',
                          fontSize: '0.8rem',
                          fontWeight: 700,
                          padding: '3px 12px',
                          borderRadius: '999px',
                        }}
                      >
                        {t('official.exifValid', '✓ EXIF Valid')}
                      </span>
                    </div>

                    <div style={{ fontSize: '0.92rem', color: 'var(--text)', lineHeight: 1.55 }}>
                      <strong>{t('official.geminiScore', 'Gemini Structural Damage Score:')}</strong>{' '}
                      {photo.verification.gemini_reason}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* SDRF Relief Entitlement Breakdown */}
            <div style={{ marginBottom: '28px' }}>
              <div
                style={{
                  backgroundColor: 'var(--bg-alt)',
                  border: '1.5px solid var(--border)',
                  borderRadius: '16px',
                  padding: '22px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                    {t('official.recommendedSanction', 'Recommended SDRF Sanction:')}
                  </span>
                  <strong style={{ fontSize: '1.65rem', color: 'var(--primary)' }}>
                    ₹{selectedClaim.relief?.total ? selectedClaim.relief.total.toLocaleString('en-IN') : '0'}
                  </strong>
                </div>

                <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  {t(
                    'official.sanctionNorms',
                    'Computed according to Ministry of Home Affairs SDRF/NDRF letter 33-03/2020-NDM-I norms.'
                  )}
                </div>
              </div>
            </div>

            {/* Officer Actions */}
            <div
              style={{
                backgroundColor: '#FFFFFF',
                borderRadius: '16px',
                padding: '22px',
                border: '1.5px solid var(--border)',
              }}
            >
              <h4 style={{ margin: '0 0 12px 0', fontSize: '1.05rem', color: 'var(--text)' }}>
                {t('official.takeActionTitle', 'Take Officer Action')}
              </h4>

              <input
                type="text"
                placeholder={t('official.remarksPlaceholder', 'Optional inspection remarks / field note...')}
                value={statusActionNote}
                onChange={(e) => setStatusActionNote(e.target.value)}
                style={{
                  width: '100%',
                  padding: '12px 18px',
                  borderRadius: '999px',
                  border: '1.5px solid var(--border)',
                  marginBottom: '16px',
                  fontSize: '0.92rem',
                  outline: 'none',
                  backgroundColor: 'var(--bg)',
                }}
              />

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                <button
                  onClick={() => handleUpdateStatus('Verified')}
                  className="btn-pill btn-blue-pill"
                  style={{ minHeight: '48px', padding: '10px 22px', fontSize: '0.98rem', fontWeight: 800 }}
                >
                  <CheckCircle2 size={16} /> {t('official.btnMarkVerified', 'Mark Verified')}
                </button>

                <button
                  onClick={() => handleUpdateStatus('Approved')}
                  className="btn-pill btn-green-pill"
                  style={{ minHeight: '48px', padding: '10px 22px', fontSize: '0.98rem', fontWeight: 800 }}
                >
                  <CheckCircle2 size={16} /> {t('official.btnApproveRelief', 'Approve Relief')}
                </button>

                <button
                  onClick={() => handleUpdateStatus('Paid')}
                  className="btn-pill btn-orange-pill"
                  style={{ minHeight: '48px', padding: '10px 22px', fontSize: '0.98rem', fontWeight: 800 }}
                >
                  <CheckCircle2 size={16} /> {t('official.btnReleaseDbt', 'Release DBT')}
                </button>

                <button
                  onClick={() => handleUpdateStatus('Rejected')}
                  className="btn-pill btn-outline-pill"
                  style={{ minHeight: '48px', padding: '10px 22px', fontSize: '0.98rem', fontWeight: 800 }}
                >
                  <XCircle size={16} /> {t('official.btnReject', 'Reject')}
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="card-soft" style={{ textAlign: 'center', padding: '40px' }}>
            {t('official.noClaimSelected', 'Select a claim from the queue to inspect details.')}
          </div>
        )}
      </div>
    </div>
  );
};

export default Official;
