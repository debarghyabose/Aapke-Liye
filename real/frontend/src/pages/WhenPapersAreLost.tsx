// src/pages/WhenPapersAreLost.tsx
import React from 'react';
import { useTranslation } from 'react-i18next';
import { FileQuestion, Users, MapPin, Building2, CheckCircle2, ShieldCheck, Sparkles } from 'lucide-react';
import { speakText } from '../utils/tts';

export const WhenPapersAreLost: React.FC = () => {
  const { t, i18n } = useTranslation();

  const handleListen = () => {
    const text = `${t('papersLost.title', 'When Your Papers Are Lost in the Flood')}. ${t(
      'papersLost.intro1',
      'Under official'
    )} ${t('papersLost.sdrfBold', 'State Disaster Response Fund (SDRF)')} ${t(
      'papersLost.intro2',
      'rules, affected families'
    )} ${t('papersLost.cannotBeDenied', 'cannot be denied emergency relief')} ${t(
      'papersLost.intro3',
      'solely because documents were swept away by floodwaters.'
    )}`;
    speakText(text, i18n.language);
  };

  const substitutions = [
    {
      lost: t('papersLost.card1Lost', 'Aadhaar Card Lost in Water'),
      chip: t('papersLost.card1Chip', 'PANCHAYAT LETTER'),
      solution: t(
        'papersLost.card1Solution',
        'Gram Panchayat Pradhan or Ward Councillor attestation letter + emergency biometric re-print token at nearest Seva Kendra.'
      ),
      icon: <Users size={22} />,
      accentColor: '#D97706', // Turmeric Amber / Golden Yellow
      accentBg: '#FEF3C7',
      accentBorder: '#FCD34D',
      chipBg: '#FFFBEB',
      chipText: '#B45309',
      topGradient: 'linear-gradient(90deg, #F59E0B, #FBBF24)',
    },
    {
      lost: t('papersLost.card2Lost', 'Ration Card Submerged'),
      chip: t('papersLost.card2Chip', 'PDS REGISTER MATCH'),
      solution: t(
        'papersLost.card2Solution',
        'Beneficiary match from local PDS / ration dealer register + Panchayat household family endorsement certificate.'
      ),
      icon: <Building2 size={22} />,
      accentColor: '#2563EB', // Royal River Blue
      accentBg: '#DBEAFE',
      accentBorder: '#BAE6FD',
      chipBg: '#EFF6FF',
      chipText: '#1D4ED8',
      topGradient: 'linear-gradient(90deg, #2563EB, #60A5FA)',
    },
    {
      lost: t('papersLost.card3Lost', 'Land Record / RoR Washed Away'),
      chip: t('papersLost.card3Chip', 'BHULEKH EXTRACT'),
      solution: t(
        'papersLost.card3Solution',
        'State Banglarbhumi / Bhulekh portal digital extract + geo-tagged photos of plot + neighbour witness signature.'
      ),
      icon: <MapPin size={22} />,
      accentColor: '#059669', // Emerald Green
      accentBg: '#D1FAE5',
      accentBorder: '#A7F3D0',
      chipBg: '#ECFDF5',
      chipText: '#047857',
      topGradient: 'linear-gradient(90deg, #10B981, #34D399)',
    },
    {
      lost: t('papersLost.card4Lost', 'Bank Passbook Damaged'),
      chip: t('papersLost.card4Chip', 'AADHAAR DBT SEEDED'),
      solution: t(
        'papersLost.card4Solution',
        'Aadhaar-seeded DBT direct bank lookup; bank manager certificate using linked mobile number and PMJDY records.'
      ),
      icon: <CheckCircle2 size={22} />,
      accentColor: '#EA580C', // Terracotta Orange
      accentBg: '#FFEDD5',
      accentBorder: '#FED7AA',
      chipBg: '#FFF7ED',
      chipText: '#C2410C',
      topGradient: 'linear-gradient(90deg, #EA580C, #FB923C)',
    },
  ];

  return (
    <section
      className="section-mobile-pad"
      style={{
        padding: 'clamp(50px, 6vw, 80px) clamp(16px, 4vw, 4vw)',
      }}
      aria-labelledby="lost-papers-heading"
    >
      <div
        style={{
          maxWidth: '1380px',
          margin: '0 auto',
        }}
      >
        <div
          style={{
            backgroundColor: '#FFFFFF',
            borderRadius: '24px',
            border: '1.5px solid var(--border)',
            boxShadow: '0 8px 30px rgba(14, 42, 56, 0.07)',
            overflow: 'hidden',
          }}
        >
          {/* Top Multi-Color Gradient Ribbon */}
          <div
            style={{
              height: '6px',
              width: '100%',
              background: 'linear-gradient(90deg, #F59E0B 0%, #10B981 33%, #2563EB 66%, #EA580C 100%)',
            }}
          />

          <div
            className="section-inner-card"
            style={{
              padding: '40px 36px 44px 36px',
            }}
          >
            {/* Header row */}
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '20px',
                marginBottom: '24px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <div
                  style={{
                    backgroundColor: '#FEF3C7',
                    border: '1.5px solid #FCD34D',
                    width: '52px',
                    height: '52px',
                    borderRadius: '16px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#D97706',
                    flexShrink: 0,
                    boxShadow: '0 3px 10px rgba(245, 158, 11, 0.2)',
                  }}
                >
                  <FileQuestion size={28} />
                </div>
                <div>
                  <div
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '4px 12px',
                      borderRadius: '999px',
                      backgroundColor: '#FEF3C7',
                      border: '1px solid #FCD34D',
                      color: '#92400E',
                      fontSize: '0.8rem',
                      fontWeight: 800,
                      letterSpacing: '0.5px',
                      textTransform: 'uppercase',
                      marginBottom: '6px',
                    }}
                  >
                    <Sparkles size={14} style={{ color: '#D97706' }} />
                    <span>{t('papersLost.badge', 'Legal Disaster Norms Protection')}</span>
                  </div>
                  <h2
                    id="lost-papers-heading"
                    style={{
                      fontSize: 'clamp(1.9rem, 3.2vw, 2.6rem)',
                      margin: 0,
                      color: '#000000',
                      fontWeight: 800,
                      lineHeight: 1.15,
                    }}
                  >
                    {t('papersLost.title', 'When Your Papers Are Lost in the Flood')}
                  </h2>
                </div>
              </div>

              <button
                onClick={handleListen}
                className="btn-pill btn-outline-pill"
                style={{
                  padding: '11px 24px',
                  minHeight: '48px',
                  fontSize: '1rem',
                  fontWeight: 800,
                  color: '#000000',
                  borderColor: '#F59E0B',
                  backgroundColor: '#FFFFFF',
                  boxShadow: '0 2px 8px rgba(245, 158, 11, 0.15)',
                }}
                aria-label={t('papersLost.listenAria', 'Listen to proof substitution rules')}
              >
                <span>🔊 {t('papersLost.listen', 'Listen to proof rules')}</span>
              </button>
            </div>

            <p
              style={{
                fontSize: 'clamp(1.05rem, 1.2vw, 1.15rem)',
                color: '#111111',
                lineHeight: 1.6,
                maxWidth: '960px',
                marginBottom: '32px',
                fontWeight: 600,
              }}
            >
              {t('papersLost.intro1', 'Under official')}{' '}
              <strong>{t('papersLost.sdrfBold', 'State Disaster Response Fund (SDRF)')}</strong>{' '}
              {t('papersLost.intro2', 'rules, affected families')}{' '}
              <span style={{ color: '#000000', backgroundColor: '#FEF3C7', padding: '2px 6px', borderRadius: '4px' }}>
                {t('papersLost.cannotBeDenied', 'cannot be denied emergency relief')}
              </span>{' '}
              {t('papersLost.intro3', 'solely because documents were swept away by floodwaters.')}{' '}
              <strong>{t('papersLost.appTitle', 'Aapke Liye')}</strong>{' '}
              {t('papersLost.intro4', 'prepares recognized alternative proof packages ready for revenue inspection:')}
            </p>

            {/* 4 Cards strictly in ONE Line */}
            <div
              className="how-it-works-row"
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
                gap: '16px',
              }}
            >
              {substitutions.map((sub, index) => (
                <div
                  key={index}
                  className="card-hover"
                  style={{
                    backgroundColor: '#FFFFFF',
                    borderRadius: '16px',
                    border: '1.5px solid var(--border)',
                    overflow: 'hidden',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    boxShadow: '0 4px 14px rgba(14, 42, 56, 0.05)',
                  }}
                >
                  {/* Colored top line */}
                  <div style={{ height: '4px', width: '100%', background: sub.topGradient }} />

                  <div style={{ padding: '20px 18px', display: 'flex', flexDirection: 'column', gap: '12px', flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div
                        style={{
                          width: '42px',
                          height: '42px',
                          borderRadius: '12px',
                          backgroundColor: sub.accentBg,
                          border: `1px solid ${sub.accentBorder}`,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: sub.accentColor,
                          flexShrink: 0,
                        }}
                      >
                        {sub.icon}
                      </div>

                      <span
                        style={{
                          fontSize: '0.7rem',
                          fontWeight: 800,
                          letterSpacing: '0.5px',
                          padding: '3px 8px',
                          borderRadius: '6px',
                          backgroundColor: sub.chipBg,
                          color: sub.chipText,
                          border: `1px solid ${sub.accentBorder}`,
                        }}
                      >
                        {sub.chip}
                      </span>
                    </div>

                    <strong
                      style={{
                        color: '#000000',
                        fontSize: '1.14rem',
                        lineHeight: 1.25,
                        fontWeight: 800,
                      }}
                    >
                      {sub.lost}
                    </strong>

                    <p
                      style={{
                        fontSize: '0.96rem',
                        color: '#1A1A1A',
                        margin: 0,
                        lineHeight: 1.55,
                        fontWeight: 600,
                        flex: 1,
                      }}
                    >
                      {sub.solution}
                    </p>
                  </div>

                  <div
                    style={{
                      padding: '12px 18px',
                      backgroundColor: '#F8FBFC',
                      borderTop: '1px solid #EDF3F6',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      fontSize: '0.86rem',
                      fontWeight: 700,
                      color: sub.accentColor,
                    }}
                  >
                    <ShieldCheck size={14} />
                    <span>{t('papersLost.altProofValid', 'Official SDRF Substitute Valid')}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default WhenPapersAreLost;
