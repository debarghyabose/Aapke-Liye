// src/pages/Track.tsx
import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Search,
  Volume2,
  Clock,
  FileText,
  Check,
  ShieldAlert,
} from 'lucide-react';
import {
  getStatus,
  DEMO_MODE,
  errorText,
  claimsOnThisDevice,
  getClaimPdf,
  draftDocument,
  saveTextFile,
} from '../api/client';
import { StatusOut } from '../types/api';
import { MOCK_CLAIM_ID, MOCK_STATUS } from '../mocks/sampleData';
import { speakText } from '../utils/tts';

export const Track: React.FC = () => {
  const { i18n, t } = useTranslation();
  const [searchParams] = useSearchParams();
  const initialId =
    searchParams.get('id') || (DEMO_MODE ? MOCK_CLAIM_ID : claimsOnThisDevice().slice(-1)[0] || '');

  const [claimIdInput, setClaimIdInput] = useState<string>(initialId);
  const [statusData, setStatusData] = useState<StatusOut | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [trackError, setTrackError] = useState<string | null>(null);
  // Legal follow-up letters are offered once a claim has waited 14 days without approval.
  const submittedAt = statusData?.timeline.find((e) => e.status === 'Submitted')?.at;
  const isStuckMoreThan14Days =
    DEMO_MODE ||
    (!!statusData &&
      ['Submitted', 'Verified'].includes(statusData.status) &&
      !!submittedAt &&
      Date.now() - new Date(submittedAt).getTime() > 14 * 24 * 60 * 60 * 1000);
  const [selectedGrievanceDraft, setSelectedGrievanceDraft] = useState<string | null>(null);
  const [draftText, setDraftText] = useState<string | null>(null);
  const [draftFile, setDraftFile] = useState<string>('letter.txt');
  const [drafting, setDrafting] = useState<boolean>(false);
  const LETTER_DOC: Record<string, string> = { bdo: 'followup_letter', grievance: 'grievance', rti: 'rti_application' };

  const openLetter = async (id: string, name: string) => {
    setSelectedGrievanceDraft(name);
    setDraftText(null);
    if (DEMO_MODE || !statusData) return;
    setDrafting(true);
    setTrackError(null);
    try {
      const d = await draftDocument(statusData.claim_id, LETTER_DOC[id]);
      setDraftText(d.text);
      setDraftFile(`${LETTER_DOC[id]}-${statusData.claim_id}.txt`);
    } catch (e) {
      setTrackError(errorText(e));
      setSelectedGrievanceDraft(null);
    } finally {
      setDrafting(false);
    }
  };

  useEffect(() => {
    if (initialId) {
      handleSearch(initialId);
    }
  }, [initialId]);

  const handleSearch = async (idToSearch?: string) => {
    const id = idToSearch || claimIdInput.trim();
    if (!id) return;

    setLoading(true);
    try {
      setTrackError(null);
      const data = await getStatus(id);
      setStatusData(data);
    } catch (e) {
      if (DEMO_MODE) setStatusData(MOCK_STATUS);
      else {
        setStatusData(null);
        setTrackError(errorText(e));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleListenStatus = () => {
    if (!statusData) return;
    const timelineText = statusData.timeline
      .map((item) => `${t('track.statusLabel', { status: item.status, defaultValue: `Status: ${item.status}` })}. ${item.note || ''}`)
      .join('. ');
    const fullText = `${t('track.refLabel', 'Relief Claim Reference')} ${statusData.claim_id}. ${t('track.statusLabel', { status: statusData.status, defaultValue: `Status: ${statusData.status}` })}. ${timelineText}`;
    speakText(fullText, i18n.language);
  };

  const statusOrder = [
    { key: 'Submitted', label: t('track.statusSubmitted', 'Submitted') },
    { key: 'Verified', label: t('track.statusVerified', 'Verified') },
    { key: 'Approved', label: t('track.statusApproved', 'Approved') },
    { key: 'Paid', label: t('track.statusPaid', 'Paid') },
  ];

  return (
    <div
      style={{
        maxWidth: '940px',
        margin: '24px auto 60px auto',
        padding: '0 clamp(14px, 3.5vw, 28px)',
      }}
    >
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: 'clamp(2.1rem, 3.8vw, 2.9rem)', marginBottom: '8px', color: 'var(--text)', fontWeight: 800 }}>
          {t('track.title', 'Track Your Relief Claim')}
        </h1>
        <p style={{ color: 'var(--text-muted)', margin: 0, fontSize: 'clamp(1.05rem, 1.2vw, 1.15rem)', fontWeight: 600 }}>
          {t(
            'track.subtitle',
            'Check real-time verification progress by District Authorities, Field Inspectors, and Direct Bank Transfer (DBT).'
          )}
        </p>
      </div>

      {/* Search Input Box */}
      <div
        className="card-soft track-search-row"
        style={{
          display: 'flex',
          gap: '12px',
          alignItems: 'center',
          marginBottom: '28px',
          padding: '16px 20px',
          boxShadow: '0 4px 16px rgba(26, 75, 117, 0.06)',
        }}
      >
        <div style={{ flex: 1, width: '100%' }}>
          <input
            type="text"
            value={claimIdInput}
            onChange={(e) => setClaimIdInput(e.target.value)}
            placeholder={t('track.placeholder', 'e.g. CLM-2026-WB-8492')}
            aria-label={t('track.inputAria', 'Claim ID input')}
            style={{
              width: '100%',
              minHeight: '48px',
              padding: '12px 20px',
              borderRadius: '999px',
              border: '1.5px solid var(--border)',
              fontSize: '1.08rem',
              fontWeight: 800,
              color: 'var(--text)',
              backgroundColor: '#FFFFFF',
              outline: 'none',
            }}
          />
        </div>

        <button
          onClick={() => handleSearch()}
          disabled={loading}
          className="btn-pill btn-orange-pill"
          style={{ gap: '8px', minWidth: '140px', minHeight: '48px', fontSize: '1.05rem', fontWeight: 800 }}
        >
          <Search size={18} />
          <span>{loading ? t('track.searching', 'Searching…') : t('track.trackBtn', 'Track')}</span>
        </button>
      </div>

      {trackError && (
        <div role="alert" style={{ margin: '16px 0', padding: '14px 18px', borderRadius: '12px', background: '#FDECEA', color: '#8A1C1C', fontWeight: 700 }}>
          {trackError}
        </div>
      )}

      {statusData && (
        <div className="card-soft track-results-card" style={{ padding: 'clamp(24px, 4vw, 40px) clamp(16px, 3.5vw, 36px)' }}>
          {/* Header of Track Results */}
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              justifyContent: 'space-between',
              alignItems: 'center',
              borderBottom: '1.5px solid var(--border)',
              paddingBottom: '24px',
              marginBottom: '32px',
              gap: '16px',
            }}
          >
            <div>
              <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                {t('track.refLabel', 'Relief Claim Reference')}
              </span>
              <h2
                style={{
                  fontSize: '2rem',
                  color: 'var(--primary)',
                  margin: '4px 0 0 0',
                }}
              >
                {statusData.claim_id}
              </h2>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span
                style={{
                  backgroundColor: 'rgba(42, 123, 76, 0.14)',
                  color: 'var(--leaf)',
                  padding: '8px 20px',
                  borderRadius: '999px',
                  fontWeight: 700,
                  fontSize: '0.95rem',
                }}
              >
                ● {t('track.statusLabel', { status: statusData.status, defaultValue: `Status: ${statusData.status}` })}
              </span>

              <button
                onClick={handleListenStatus}
                className="btn-outline-pill"
                style={{
                  padding: '8px 18px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  cursor: 'pointer',
                  fontSize: '0.9rem',
                }}
                aria-label={t('track.listenAria', 'Listen to tracking updates in your language')}
              >
                <Volume2 size={16} style={{ color: 'var(--accent)' }} />
                <span>🔊 {t('track.listen', 'Listen')}</span>
              </button>
            </div>
          </div>

          {/* Stepper overview (Submitted -> Verified -> Approved -> Paid) */}
          <div
            className="track-stepper"
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              position: 'relative',
              marginBottom: '40px',
              padding: '0 12px',
            }}
          >
            {/* Connecting line */}
            <div
              style={{
                position: 'absolute',
                top: '22px',
                left: '30px',
                right: '30px',
                height: '3px',
                backgroundColor: 'var(--border)',
                zIndex: 1,
              }}
            />

            {statusOrder.map((stepItem, idx) => {
              const rawStatuses = ['Submitted', 'Verified', 'Approved', 'Paid'];
              const currentIdx = rawStatuses.indexOf(statusData.status);
              const isPastOrCurrent = currentIdx >= idx;
              const isCurrent = currentIdx === idx;

              return (
                <div
                  key={stepItem.key}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    zIndex: 2,
                    textAlign: 'center',
                  }}
                >
                  <div
                    className="track-stepper-circle"
                    style={{
                      width: '44px',
                      height: '44px',
                      borderRadius: '50%',
                      backgroundColor: isPastOrCurrent ? 'var(--primary)' : 'var(--bg-alt)',
                      color: isPastOrCurrent ? '#FFFFFF' : 'var(--text-muted)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 800,
                      border: isCurrent ? '4px solid rgba(244, 96, 54, 0.4)' : 'none',
                    }}
                  >
                    {isPastOrCurrent ? <Check size={20} /> : idx + 1}
                  </div>
                  <span
                    className="track-stepper-label"
                    style={{
                      marginTop: '8px',
                      fontSize: '0.94rem',
                      fontWeight: isCurrent ? 800 : 700,
                      color: isCurrent ? 'var(--accent)' : isPastOrCurrent ? 'var(--primary)' : 'var(--text-muted)',
                    }}
                  >
                    {stepItem.label}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Vertical Timeline */}
          <h3 style={{ fontSize: '1.3rem', marginBottom: '20px', color: 'var(--text)' }}>
            {t('track.historyTitle', 'Verification History')}
          </h3>

          <div style={{ position: 'relative', paddingLeft: '32px', marginBottom: '40px' }}>
            <div
              style={{
                position: 'absolute',
                left: '12px',
                top: '8px',
                bottom: '12px',
                width: '2px',
                backgroundColor: 'var(--border)',
              }}
            />

            {statusData.timeline.map((event, eIdx) => (
              <div key={eIdx} style={{ position: 'relative', marginBottom: '24px' }}>
                <div
                  style={{
                    position: 'absolute',
                    left: '-26px',
                    top: '4px',
                    width: '14px',
                    height: '14px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--primary)',
                    border: '3px solid #FFFFFF',
                  }}
                />

                <div
                  style={{
                    backgroundColor: '#FFFFFF',
                    borderRadius: '14px',
                    padding: '18px 22px',
                    border: '1.5px solid var(--border)',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '6px',
                    }}
                  >
                    <strong style={{ color: 'var(--primary)', fontSize: '1.05rem' }}>
                      {event.status}
                    </strong>
                    <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={14} /> {new Date(event.at).toLocaleDateString()} · {new Date(event.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>

                  <p style={{ margin: 0, fontSize: '0.95rem', color: 'var(--text-muted)', lineHeight: 1.55 }}>
                    {event.note}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* If stuck > 14 days */}
          {isStuckMoreThan14Days && (
            <div
              style={{
                backgroundColor: 'rgba(231, 111, 81, 0.08)',
                border: '1.5px solid var(--border)',
                borderRadius: '18px',
                padding: '30px',
                marginTop: '36px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
                <ShieldAlert size={24} style={{ color: 'var(--accent)' }} />
                <h4 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--text)' }}>
                  {t('track.stuckTitle', 'Statutory Action: Claim In Process > 14 Days')}
                </h4>
              </div>
              <p style={{ fontSize: '0.95rem', color: 'var(--text-muted)', marginBottom: '22px', lineHeight: 1.55 }}>
                {t(
                  'track.stuckDesc',
                  'Under Citizen Charter guidelines, flood relief claims must be processed within two weeks. If your relief is pending without field clearance, download pre-formatted legal draft petitions:'
                )}
              </p>

              <div
                className="track-letters-grid"
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                  gap: '16px',
                  marginBottom: '20px',
                }}
              >
                {[
                  {
                    id: 'bdo',
                    name: t('track.letter1Name', 'BDO / SDM Urgent Reminder Letter'),
                    desc: t('track.letter1Desc', 'Formal notice citing SDRF 2022–26 timeline regulations for urgent sanction.'),
                  },
                  {
                    id: 'grievance',
                    name: t('track.letter2Name', 'State Grievance Portal Petition'),
                    desc: t('track.letter2Desc', 'Pre-drafted complaint for State CMO Grievance / District Magistrate portal.'),
                  },
                  {
                    id: 'rti',
                    name: t('track.letter3Name', 'Right to Information (RTI) Inquiry'),
                    desc: t('track.letter3Desc', 'Statutory Section 6(1) query seeking daily progress inspection sheet.'),
                  },
                ].map((letter) => (
                  <div
                    key={letter.id}
                    style={{
                      backgroundColor: '#FFFFFF',
                      borderRadius: '14px',
                      padding: '20px',
                      border: '1.5px solid var(--border)',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--text)', marginBottom: '6px' }}>
                        {letter.name}
                      </div>
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.45 }}>
                        {letter.desc}
                      </div>
                    </div>

                    <button
                      onClick={() => openLetter(letter.id, letter.name)}
                      className="btn-outline-pill"
                      style={{
                        padding: '8px 16px',
                        fontSize: '0.88rem',
                        marginTop: '16px',
                        width: '100%',
                        justifyContent: 'center',
                      }}
                    >
                      <FileText size={14} />
                      <span>{t('track.generateLetter', 'Generate Ready Letter')}</span>
                    </button>
                  </div>
                ))}
              </div>

              {selectedGrievanceDraft && (
                <div
                  style={{
                    backgroundColor: '#FFFFFF',
                    border: '1.5px solid var(--border)',
                    borderRadius: '16px',
                    padding: '22px',
                    marginTop: '20px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <strong style={{ color: 'var(--primary)', fontSize: '1.05rem' }}>
                      {t('track.draftTitle', { title: selectedGrievanceDraft, defaultValue: `Generated Draft: ${selectedGrievanceDraft}` })}
                    </strong>
                    <button
                      onClick={() => setSelectedGrievanceDraft(null)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', fontWeight: 700 }}
                    >
                      {t('track.close', 'Close')}
                    </button>
                  </div>
                  <pre
                    style={{
                      fontSize: '0.85rem',
                      color: 'var(--text)',
                      backgroundColor: 'var(--bg)',
                      padding: '18px',
                      borderRadius: '10px',
                      whiteSpace: 'pre-wrap',
                      fontFamily: 'monospace',
                      border: '1px solid var(--border)',
                    }}
                  >
                    {!DEMO_MODE
                      ? drafting
                        ? t('track.drafting', 'Preparing your letter…')
                        : draftText
                      : t('track.letterTemplate', {
                      claimId: statusData.claim_id,
                      name: DEMO_MODE ? 'Sunita Mondal' : '__________',
                      defaultValue: `To,\nThe Block Development Officer (BDO) / Sub-Divisional Magistrate,\nDistrict Disaster Relief Cell.\n\nSubject: Urgent Sanction of SDRF Relief Claim [Ref: ${statusData.claim_id}]\n\nRespected Sir/Madam,\nI, Sunita Mondal, submitted my disaster relief claim on 15/10/2026 for total house damage and crop loss. More than 14 days have elapsed since field inspection. As per standard SDRF relief norms, kindly release the pending DBT compensation to avoid ongoing distress to my family.\n\nClaim ID: ${statusData.claim_id}\nAttached: Geo-tagged photo verification receipt.`,
                        })}
                  </pre>
                  <button
                    onClick={() => {
                      if (DEMO_MODE) window.open('/sample-claim.pdf', '_blank');
                      else if (draftText) saveTextFile(draftText, draftFile);
                    }}
                    className="btn-pill btn-orange-pill"
                    style={{ minHeight: '44px', padding: '8px 26px', fontSize: '0.92rem', marginTop: '14px' }}
                  >
                    {t('track.downloadPrint', 'Download & Print Formal Letter')}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Track;
