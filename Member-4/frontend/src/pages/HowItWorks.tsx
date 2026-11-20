// src/pages/HowItWorks.tsx
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Mic, Camera, FileCheck2, Landmark, ArrowRight, Sparkles, CheckCircle2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { speakText } from '../utils/tts';

export const HowItWorks: React.FC = () => {
  const { t, i18n } = useTranslation();

  const steps = [
    {
      num: '01',
      tag: t('howItWorks.step1Tag', 'VOICE AI'),
      title: t('howItWorks.step1Title', '1. Speak in your language'),
      desc: t(
        'howItWorks.step1Desc',
        'Press the red record button and describe what the water took: your house, crop, livestock, or family documents. No typing required.'
      ),
      icon: <Mic size={24} />,
      accentColor: '#D97706', // Turmeric Amber / Golden Yellow
      accentLight: '#FEF3C7',
      accentBorder: '#FDE68A',
      gradient: 'linear-gradient(135deg, #F59E0B 0%, #FBBF24 100%)',
      badgeBg: '#FFFBEB',
      badgeText: '#B45309',
    },
    {
      num: '02',
      tag: t('howItWorks.step2Tag', 'GPS & PHOTOS'),
      title: t('howItWorks.step2Title', '2. Show damage photos'),
      desc: t(
        'howItWorks.step2Desc',
        'Take photos of broken walls, submerged fields, or lost belongings. Automatic GPS coordinates and timestamps confirm authenticity.'
      ),
      icon: <Camera size={24} />,
      accentColor: '#059669', // Banana Leaf Emerald Green
      accentLight: '#D1FAE5',
      accentBorder: '#A7F3D0',
      gradient: 'linear-gradient(135deg, #10B981 0%, #34D399 100%)',
      badgeBg: '#ECFDF5',
      badgeText: '#047857',
    },
    {
      num: '03',
      tag: t('howItWorks.step3Tag', 'SDRF NORMS'),
      title: t('howItWorks.step3Title', '3. Get verified claim form'),
      desc: t(
        'howItWorks.step3Desc',
        'Gemini maps your losses to exact SDRF compensation norms and suggests legal proof substitutions for any lost identity papers.'
      ),
      icon: <FileCheck2 size={24} />,
      accentColor: '#2563EB', // Royal River Blue
      accentLight: '#DBEAFE',
      accentBorder: '#BFDBFE',
      gradient: 'linear-gradient(135deg, #2563EB 0%, #60A5FA 100%)',
      badgeBg: '#EFF6FF',
      badgeText: '#1D4ED8',
    },
    {
      num: '04',
      tag: t('howItWorks.step4Tag', 'DIRECT TO BANK'),
      title: t('howItWorks.step4Title', '4. Track until paid'),
      desc: t(
        'howItWorks.step4Desc',
        'Download your official PDF application. Track your verification timeline step-by-step until DBT relief reaches your bank account.'
      ),
      icon: <Landmark size={24} />,
      accentColor: '#EA580C', // Terracotta Orange
      accentLight: '#FFEDD5',
      accentBorder: '#FED7AA',
      gradient: 'linear-gradient(135deg, #EA580C 0%, #FB923C 100%)',
      badgeBg: '#FFF7ED',
      badgeText: '#C2410C',
    },
  ];

  const handleListenAll = () => {
    const text = steps.map((s) => `${s.title}: ${s.desc}`).join('. ');
    speakText(text, i18n.language);
  };

  return (
    <section
      id="how-it-works"
      className="section-mobile-pad"
      style={{
        padding: 'clamp(50px, 7vw, 90px) clamp(16px, 4vw, 4vw) clamp(50px, 6vw, 80px) clamp(16px, 4vw, 4vw)',
        position: 'relative',
        overflow: 'hidden',
      }}
      aria-labelledby="how-it-works-heading"
    >
      <div
        style={{
          maxWidth: '1380px',
          margin: '0 auto',
        }}
      >
        {/* Section Header with Warm Golden Highlight Pill */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'flex-end',
            justifyContent: 'space-between',
            gap: '20px',
            marginBottom: '40px',
          }}
        >
          <div>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '6px 14px',
                borderRadius: '999px',
                backgroundColor: '#FEF3C7',
                border: '1px solid #FCD34D',
                color: '#92400E',
                fontSize: '0.86rem',
                fontWeight: 700,
                letterSpacing: '0.5px',
                textTransform: 'uppercase',
                marginBottom: '12px',
                boxShadow: '0 2px 6px rgba(245, 158, 11, 0.15)',
              }}
            >
              <Sparkles size={15} style={{ color: '#D97706' }} />
              <span>{t('howItWorks.badge', 'Simple 4-Step Recovery Workflow')}</span>
            </div>

            <h2
              id="how-it-works-heading"
              style={{
                fontSize: 'clamp(2.1rem, 3.4vw, 2.85rem)',
                margin: 0,
                color: 'var(--text)',
                lineHeight: 1.15,
                fontWeight: 800,
              }}
            >
              {t('howItWorks.heading', 'How Aapke Liye Prepares Your Relief Claim')}
            </h2>
            <p
              style={{
                fontSize: 'clamp(1.08rem, 1.25vw, 1.22rem)',
                color: 'var(--text-muted)',
                margin: '10px 0 0 0',
                maxWidth: '680px',
                fontWeight: 600,
              }}
            >
              {t(
                'howItWorks.subtitle',
                'Designed for low connectivity and zero paperwork. From spoken words to an official SDRF relief claim.'
              )}
            </p>
          </div>

          <button
            onClick={handleListenAll}
            className="btn-pill btn-outline-pill"
            style={{
              padding: '12px 24px',
              minHeight: '48px',
              fontSize: '1rem',
              fontWeight: 800,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              backgroundColor: '#FFFFFF',
              borderColor: '#F59E0B',
              color: '#92400E',
              boxShadow: '0 2px 8px rgba(245, 158, 11, 0.12)',
            }}
            aria-label={t('howItWorks.listenStepsAria', 'Listen to all steps explained aloud')}
          >
            <span>🔊 {t('howItWorks.listenSteps', 'Listen to all 4 steps')}</span>
          </button>
        </div>

        {/* 4 Cards strictly in ONE Line */}
        <div
          className="how-it-works-row"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
            gap: '16px',
            alignItems: 'stretch',
          }}
        >
          {steps.map((step, idx) => (
            <div
              key={idx}
              className="how-it-works-card"
              style={{
                backgroundColor: '#FFFFFF',
                borderRadius: '18px',
                border: '1px solid var(--border)',
                boxShadow: '0 6px 20px rgba(14, 42, 56, 0.05)',
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                transition: 'all 0.28s cubic-bezier(0.16, 1, 0.3, 1)',
                position: 'relative',
              }}
            >
              {/* Vibrant Colored Gradient Top Accent Bar */}
              <div
                style={{
                  height: '6px',
                  width: '100%',
                  background: step.gradient,
                }}
              />

              <div
                style={{
                  padding: '22px 18px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '14px',
                  flex: 1,
                }}
              >
                {/* Header row with Icon, Tag, and Big Number */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div
                    style={{
                      width: '46px',
                      height: '46px',
                      borderRadius: '12px',
                      backgroundColor: step.accentLight,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: step.accentColor,
                      boxShadow: `0 2px 8px ${step.accentLight}`,
                    }}
                  >
                    {step.icon}
                  </div>

                  <span
                    style={{
                      fontSize: '1.75rem',
                      fontWeight: 800,
                      color: step.accentColor,
                      opacity: 0.85,
                      lineHeight: 1,
                      letterSpacing: '-1px',
                    }}
                  >
                    {step.num}
                  </span>
                </div>

                {/* Sub-tag badge */}
                <div>
                  <span
                    style={{
                      display: 'inline-block',
                      padding: '3px 8px',
                      borderRadius: '6px',
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      letterSpacing: '0.5px',
                      backgroundColor: step.badgeBg,
                      color: step.badgeText,
                      border: `1px solid ${step.accentBorder}`,
                    }}
                  >
                    {step.tag}
                  </span>
                </div>

                {/* Title */}
                <h3
                  style={{
                    fontSize: '1.24rem',
                    margin: 0,
                    color: 'var(--text)',
                    lineHeight: 1.25,
                    fontWeight: 800,
                  }}
                >
                  {step.title}
                </h3>

                {/* Description */}
                <p
                  style={{
                    fontSize: '1rem',
                    color: 'var(--text-muted)',
                    lineHeight: 1.55,
                    margin: 0,
                    flex: 1,
                    fontWeight: 600,
                  }}
                >
                  {step.desc}
                </p>
              </div>

              {/* Card Footer status indicator */}
              <div
                style={{
                  padding: '12px 18px',
                  backgroundColor: '#F8FBFC',
                  borderTop: '1px solid #EDF3F6',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: '0.88rem',
                  fontWeight: 700,
                  color: step.accentColor,
                }}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <CheckCircle2 size={13} style={{ color: step.accentColor }} />
                  {t('howItWorks.stepOf', { num: idx + 1, defaultValue: `Step ${idx + 1} of 4` })}
                </span>
                {idx < 3 ? (
                  <span style={{ color: '#94A3B8', fontSize: '0.82rem' }}>
                    {t('howItWorks.next', 'Next →')}
                  </span>
                ) : (
                  <span style={{ color: step.accentColor, fontWeight: 700 }}>
                    {t('howItWorks.complete', 'Complete! ✓')}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Attractive Golden / Amber Benefit Banner */}
        <div
          className="benefit-banner"
          style={{
            marginTop: '34px',
            padding: '24px 28px',
            borderRadius: '16px',
            background: 'linear-gradient(90deg, #FEF3C7 0%, #FFFBEB 50%, #E0F2FE 100%)',
            border: '1.5px solid #FCD34D',
            boxShadow: '0 4px 16px rgba(245, 158, 11, 0.12)',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div
              style={{
                width: '46px',
                height: '46px',
                borderRadius: '50%',
                backgroundColor: '#F59E0B',
                color: '#FFFFFF',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 700,
                fontSize: '1.3rem',
                flexShrink: 0,
                boxShadow: '0 3px 8px rgba(245, 158, 11, 0.35)',
              }}
            >
              ⚡
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: '1.12rem', color: '#78350F' }}>
                {t('howItWorks.bannerTime', 'Takes less than 3 minutes. No internet or documents needed to start.')}
              </div>
              <div style={{ fontSize: '0.98rem', color: '#92400E', fontWeight: 600 }}>
                {t(
                  'howItWorks.bannerGemini',
                  'Gemini translates your spoken dialect directly into official government SDRF norms.'
                )}
              </div>
            </div>
          </div>

          <Link
            to="/claim"
            className="btn-pill btn-orange-pill"
            style={{
              padding: '12px 28px',
              minHeight: '48px',
              fontSize: '1.05rem',
              fontWeight: 800,
              gap: '8px',
            }}
          >
            <span>{t('howItWorks.startClaimNow', 'Start your claim now')}</span>
            <ArrowRight size={18} />
          </Link>
        </div>
      </div>
    </section>
  );
};

export default HowItWorks;
