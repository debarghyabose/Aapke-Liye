// src/pages/Mesh.tsx
// Phone-to-Phone Emergency Mesh Relay Screen (Member 3 Helper & Member 5 Spec)
import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import QRCode from 'qrcode';
import {
  Radio,
  QrCode,
  Scan,
  Send,
  Download,
  CheckCircle2,
  Copy,
  Clock,
  Wifi,
  WifiOff,
  AlertCircle,
  FileCheck,
  Share2,
} from 'lucide-react';
import {
  claimsOnThisDevice,
  getClaim,
  sealClaimEnvelope,
  submitMeshEnvelope,
  getStoredMeshEnvelopes,
  importMeshEnvelope,
  checkMeshReceipt,
} from '../api/client';
import { ClaimOut, SealedClaimEnvelope } from '../types/api';
import { queueOfflineItem } from '../utils/indexedDB';

export const Mesh: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<'hand' | 'carry'>('hand');
  const [deviceClaims, setDeviceClaims] = useState<ClaimOut[]>([]);
  const [selectedClaimId, setSelectedClaimId] = useState<string>('');
  const [envelope, setEnvelope] = useState<SealedClaimEnvelope | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [isSealing, setIsSealing] = useState<boolean>(false);
  const [receiptMsg, setReceiptMsg] = useState<string | null>(null);
  const [sealError, setSealError] = useState<string | null>(null);

  // Canvas for QR Code
  const qrCanvasRef = useRef<HTMLCanvasElement | null>(null);

  // "Carry a Claim" state
  const [carriedEnvelopes, setCarriedEnvelopes] = useState<SealedClaimEnvelope[]>([]);
  const [manualEnvelopeText, setManualEnvelopeText] = useState<string>('');
  const [scanError, setScanError] = useState<string | null>(null);
  const [uploadingCarried, setUploadingCarried] = useState<boolean>(false);

  // Load claims on this device
  useEffect(() => {
    const loadClaims = async () => {
      const ids = claimsOnThisDevice();
      const loaded: ClaimOut[] = [];
      for (const id of ids) {
        try {
          const c = await getClaim(id);
          if (c) loaded.push(c);
        } catch {
          // ignore
        }
      }
      setDeviceClaims(loaded);
      if (loaded.length > 0) {
        setSelectedClaimId(loaded[loaded.length - 1].id);
      }
    };
    loadClaims();
    loadCarried();
  }, []);

  const loadCarried = async () => {
    try {
      const list = await getStoredMeshEnvelopes();
      setCarriedEnvelopes(list);
    } catch (e) {
      console.warn('Could not load mesh envelopes:', e);
    }
  };

  // Seal claim and generate QR code
  useEffect(() => {
    if (!selectedClaimId || activeTab !== 'hand') return;
    const seal = async () => {
      setIsSealing(true);
      setSealError(null);
      try {
        const claim = deviceClaims.find((c) => c.id === selectedClaimId);
        if (claim) {
          // Member 3's encrypted envelope: only the relief office can open it.
          const env = await checkMeshReceipt(await sealClaimEnvelope(claim));
          setEnvelope(env);
          if (!env.fits_in_qr) {
            setSealError(
              t('mesh.tooBigForQr', 'This claim is too big for one QR code. Use "Copy Sealed Text" and send it to the neighbour instead.')
            );
            const ctx = qrCanvasRef.current?.getContext('2d');
            if (ctx && qrCanvasRef.current) ctx.clearRect(0, 0, qrCanvasRef.current.width, qrCanvasRef.current.height);
          } else if (qrCanvasRef.current) {
            const qrData = env.sealed_text;
            await QRCode.toCanvas(qrCanvasRef.current, qrData, {
              width: 280,
              margin: 2,
              color: {
                dark: '#1B1B1B',
                light: '#FFFFFF',
              },
            });
          }
        }
      } catch (err: any) {
        console.warn('Could not seal the claim:', err);
        setEnvelope(null);
        setSealError(err?.message || t('mesh.sealFailed', 'Could not seal this claim.'));
      } finally {
        setIsSealing(false);
      }
    };
    seal();
  }, [selectedClaimId, activeTab, deviceClaims]);

  const handleCopyEnvelope = () => {
    if (!envelope) return;
    navigator.clipboard.writeText(envelope.sealed_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  };

  const handleImportScannedText = async (e: React.FormEvent) => {
    e.preventDefault();
    setScanError(null);
    try {
      const newEnv: SealedClaimEnvelope = await importMeshEnvelope(manualEnvelopeText);
      await queueOfflineItem({
        type: 'mesh_relay',
        claimId: newEnv.claim_id,
        payload: newEnv,
      });
      setManualEnvelopeText('');
      await loadCarried();
      setReceiptMsg(t('mesh.importSuccess', 'Claim envelope securely saved to this device for delivery!'));
      setTimeout(() => setReceiptMsg(null), 4000);
    } catch (err: any) {
      setScanError(t('mesh.invalidEnvelope', 'Invalid QR code or envelope JSON. Please check and try again.'));
    }
  };

  const handleUploadAllCarried = async () => {
    setUploadingCarried(true);
    try {
      let delivered = 0;
      const errors: string[] = [];
      for (const env of carriedEnvelopes.filter((e) => !e.own)) {
        if (!env.receipt) {
          const res = await submitMeshEnvelope(env);
          if (res.delivered) delivered += 1;
          else if (res.error) errors.push(res.error);
        }
      }
      await loadCarried();
      setScanError(errors.length ? `${errors.length} not delivered yet: ${errors[0]}` : null);
      setReceiptMsg(
        delivered
          ? t('mesh.deliveredN', {
              count: delivered,
              defaultValue: `${delivered} claim(s) delivered. Signed receipts received from the relief office.`,
            })
          : null
      );
      setTimeout(() => setReceiptMsg(null), 6000);
    } finally {
      setUploadingCarried(false);
    }
  };

  return (
    <div className="page-container" style={{ maxWidth: '840px', margin: '0 auto', padding: '24px 16px' }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: '28px' }}>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: '#FFF3E0',
            color: '#B26A00',
            padding: '6px 14px',
            borderRadius: '999px',
            fontSize: '0.88rem',
            fontWeight: 700,
            marginBottom: '12px',
          }}
        >
          <Radio size={18} />
          <span>{t('mesh.badge', 'Phone-to-Phone Emergency Mesh')}</span>
        </div>
        <h1
          style={{
            fontFamily: 'var(--font-serif)',
            fontSize: 'clamp(1.75rem, 4vw, 2.3rem)',
            color: 'var(--secondary)',
            margin: '0 0 10px 0',
          }}
        >
          {t('mesh.title', 'Emergency Mesh Claim Relay')}
        </h1>
        <p style={{ maxWidth: '600px', margin: '0 auto', color: 'var(--muted)', fontSize: '0.95rem', lineHeight: 1.5 }}>
          {t(
            'mesh.subtitle',
            'When mobile towers are down, stranded victims can hand a cryptographically sealed claim to a moving neighbour, volunteer, or rescue boat via QR code until it reaches signal.'
          )}
        </p>
      </div>

      {receiptMsg && (
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
          <span>{receiptMsg}</span>
        </div>
      )}

      {/* Tabs */}
      <div
        style={{
          display: 'flex',
          borderBottom: '2px solid var(--border)',
          marginBottom: '24px',
          gap: '8px',
        }}
      >
        <button
          type="button"
          onClick={() => setActiveTab('hand')}
          style={{
            flex: 1,
            minHeight: '48px',
            padding: '12px 16px',
            fontWeight: 700,
            fontSize: '1rem',
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'hand' ? '3px solid var(--accent)' : '3px solid transparent',
            color: activeTab === 'hand' ? 'var(--accent)' : 'var(--muted)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
          }}
        >
          <QrCode size={20} />
          <span>{t('mesh.tabHand', '1. Hand to a Neighbour')}</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('carry')}
          style={{
            flex: 1,
            minHeight: '48px',
            padding: '12px 16px',
            fontWeight: 700,
            fontSize: '1rem',
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'carry' ? '3px solid var(--accent)' : '3px solid transparent',
            color: activeTab === 'carry' ? 'var(--accent)' : 'var(--muted)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
          }}
        >
          <Scan size={20} />
          <span>
            {t('mesh.tabCarry', '2. Carry a Claim')}
            {carriedEnvelopes.length > 0 && ` (${carriedEnvelopes.length})`}
          </span>
        </button>
      </div>

      {/* TAB 1: HAND TO A NEIGHBOUR */}
      {activeTab === 'hand' && (
        <div className="card-soft" style={{ padding: '24px' }}>
          {deviceClaims.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 20px' }}>
              <AlertCircle size={40} style={{ color: 'var(--muted)', margin: '0 auto 12px auto' }} />
              <h3 style={{ margin: '0 0 8px 0', fontSize: '1.1rem', color: 'var(--secondary)' }}>
                {t('mesh.noClaimsOnDevice', 'No filed claims found on this phone')}
              </h3>
              <p style={{ margin: '0 auto 18px auto', fontSize: '0.9rem', color: 'var(--muted)', maxWidth: '420px' }}>
                {t('mesh.noClaimsHelp', 'Start a relief claim first (even offline). Once completed, you can generate a sealed relay QR code here.')}
              </p>
              <button
                type="button"
                onClick={() => navigate('/claim')}
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
                {t('claim.heroCta', 'Start Relief Claim')}
              </button>
            </div>
          ) : (
            <div>
              <div style={{ marginBottom: '18px' }}>
                <label style={{ display: 'block', fontSize: '0.88rem', fontWeight: 600, marginBottom: '6px' }}>
                  {t('mesh.selectClaimToHand', 'Select Claim to Seal & Hand Over:')}
                </label>
                <select
                  value={selectedClaimId}
                  onChange={(e) => setSelectedClaimId(e.target.value)}
                  style={{
                    width: '100%',
                    minHeight: '48px',
                    padding: '10px 14px',
                    borderRadius: '8px',
                    border: '1.5px solid var(--border)',
                    fontSize: '0.95rem',
                    fontWeight: 600,
                  }}
                >
                  {deviceClaims.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.id} — {c.fields.name || 'Claimant'} ({c.fields.village || 'Village'})
                    </option>
                  ))}
                </select>
              </div>

              {/* QR Code Presentation */}
              <div
                style={{
                  backgroundColor: '#FFFFFF',
                  border: '2px solid var(--border)',
                  borderRadius: '12px',
                  padding: '24px',
                  textAlign: 'center',
                  marginBottom: '20px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '16px' }}>
                  <canvas ref={qrCanvasRef} style={{ maxWidth: '100%', height: 'auto', borderRadius: '8px' }} />
                </div>
                {sealError && (
                  <p role="alert" style={{ color: '#8A1C1C', fontWeight: 700, margin: '0 0 12px 0' }}>
                    {sealError}
                  </p>
                )}

                <div
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    backgroundColor: '#E8F5E9',
                    color: 'var(--primary)',
                    padding: '4px 12px',
                    borderRadius: '999px',
                    fontSize: '0.82rem',
                    fontWeight: 700,
                    marginBottom: '10px',
                  }}
                >
                  <CheckCircle2 size={16} />
                  <span>{t('mesh.cryptographicallySealed', 'AES-256 Sealed & Signed for SDMA Server')}</span>
                </div>

                <p style={{ margin: '0 0 16px 0', fontSize: '0.9rem', color: 'var(--muted)', maxWidth: '480px', marginInline: 'auto' }}>
                  {t(
                    'mesh.qrInstructions',
                    'Ask your neighbour or relief worker to open Aapke Liye and scan this code under "Carry a Claim". Your identity remains encrypted until it reaches the government office.'
                  )}
                </p>

                {envelope?.receipt ? (
                  <div
                    style={{
                      backgroundColor: '#E8F5E9',
                      border: '1.5px solid var(--primary)',
                      borderRadius: '8px',
                      padding: '12px',
                      color: 'var(--primary)',
                      fontWeight: 700,
                    }}
                  >
                    Delivered ✓ Intake Receipt: {envelope.receipt}
                  </div>
                ) : (
                  <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', flexWrap: 'wrap' }}>
                    <button
                      type="button"
                      onClick={handleCopyEnvelope}
                      className="btn-outline-pill"
                      style={{
                        minHeight: '44px',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '10px 18px',
                        fontWeight: 600,
                        cursor: 'pointer',
                      }}
                    >
                      <Copy size={16} />
                      <span>{copied ? t('common.copied', 'Copied!') : t('mesh.copyEnvelopeText', 'Copy Sealed Text')}</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: CARRY A CLAIM */}
      {activeTab === 'carry' && (
        <div className="card-soft" style={{ padding: '24px' }}>
          <div style={{ marginBottom: '20px' }}>
            <h2 style={{ margin: '0 0 6px 0', fontSize: '1.25rem', color: 'var(--secondary)' }}>
              {t('mesh.carryTitle', 'Relay Neighbour Claims')}
            </h2>
            <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--muted)' }}>
              {t(
                'mesh.carrySubtitle',
                'If you are travelling toward a road, relief camp, or mobile tower, scan your neighbours’ QR codes. This phone will hold them securely and upload them the moment mobile signal returns.'
              )}
            </p>
          </div>

          {/* Import / Paste Input */}
          <form onSubmit={handleImportScannedText} style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', fontSize: '0.88rem', fontWeight: 600, marginBottom: '6px' }}>
              {t('mesh.pasteScanLabel', 'Scan result or paste sealed claim JSON:')}
            </label>
            <textarea
              rows={3}
              value={manualEnvelopeText}
              onChange={(e) => setManualEnvelopeText(e.target.value)}
              placeholder='{"aapke_mesh":"v1", ...}'
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: '8px',
                border: '1.5px solid var(--border)',
                fontFamily: 'monospace',
                fontSize: '0.85rem',
                marginBottom: '10px',
              }}
            />
            {scanError && (
              <p style={{ color: '#C62828', fontSize: '0.85rem', margin: '0 0 10px 0', fontWeight: 600 }}>
                {scanError}
              </p>
            )}
            <button
              type="submit"
              disabled={!manualEnvelopeText.trim()}
              className="btn-primary"
              style={{
                minHeight: '48px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 22px',
                borderRadius: '8px',
                fontWeight: 700,
                backgroundColor: 'var(--accent)',
                color: '#FFFFFF',
                border: 'none',
                cursor: 'pointer',
              }}
            >
              <Scan size={18} />
              <span>{t('mesh.addCarriedClaim', 'Store Claim on This Phone')}</span>
            </button>
          </form>

          {/* List of currently carried envelopes */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <h3 style={{ margin: 0, fontSize: '1.05rem', color: 'var(--secondary)' }}>
                {t('mesh.claimsWaitingForSignal', 'Claims Held on This Phone ({{count}})', {
                  count: carriedEnvelopes.length,
                  defaultValue: `Claims Held on This Phone (${carriedEnvelopes.length})`,
                })}
              </h3>

              {carriedEnvelopes.length > 0 && (
                <button
                  type="button"
                  onClick={handleUploadAllCarried}
                  disabled={uploadingCarried}
                  className="btn-primary"
                  style={{
                    minHeight: '44px',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '8px 16px',
                    borderRadius: '8px',
                    fontWeight: 700,
                    backgroundColor: 'var(--primary)',
                    color: '#FFFFFF',
                    border: 'none',
                    cursor: 'pointer',
                  }}
                >
                  <Send size={16} />
                  <span>{uploadingCarried ? 'Uploading…' : t('mesh.syncCarriedNow', 'Sync Carried Claims')}</span>
                </button>
              )}
            </div>

            {carriedEnvelopes.length === 0 ? (
              <div
                style={{
                  border: '1px dashed var(--border)',
                  borderRadius: '8px',
                  padding: '24px',
                  textAlign: 'center',
                  color: 'var(--muted)',
                  fontSize: '0.9rem',
                }}
              >
                {t('mesh.noCarriedEnvelopes', 'No claims currently being carried on this device.')}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {carriedEnvelopes.map((env) => (
                  <div
                    key={env.claim_id}
                    style={{
                      border: '1.5px solid var(--border)',
                      borderRadius: '8px',
                      padding: '14px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      backgroundColor: '#FFFFFF',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontWeight: 700, color: 'var(--secondary)' }}>{env.claim_id}</span>
                        {env.priority === 'urgent' && (
                          <span
                            style={{
                              backgroundColor: '#FFEBEE',
                              color: '#C62828',
                              fontSize: '0.72rem',
                              fontWeight: 800,
                              padding: '2px 6px',
                              borderRadius: '4px',
                            }}
                          >
                            URGENT
                          </span>
                        )}
                      </div>
                      <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: 'var(--muted)' }}>
                        {env.summary.name} · {env.summary.village} ({env.summary.disaster_type})
                      </p>
                    </div>

                    <div>
                      {env.receipt ? (
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            backgroundColor: '#E8F5E9',
                            color: 'var(--primary)',
                            padding: '4px 10px',
                            borderRadius: '999px',
                            fontSize: '0.8rem',
                            fontWeight: 700,
                          }}
                        >
                          <CheckCircle2 size={14} />
                          <span>Delivered ✓</span>
                        </span>
                      ) : (
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            backgroundColor: '#FFF3E0',
                            color: '#B26A00',
                            padding: '4px 10px',
                            borderRadius: '999px',
                            fontSize: '0.8rem',
                            fontWeight: 700,
                          }}
                        >
                          <Clock size={14} />
                          <span>Waiting for signal</span>
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Mesh;
