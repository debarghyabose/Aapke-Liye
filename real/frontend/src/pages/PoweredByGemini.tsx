// src/pages/PoweredByGemini.tsx
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Sparkles, MessageSquareQuote, ScanEye } from 'lucide-react';

export const PoweredByGemini: React.FC = () => {
  const { t } = useTranslation();

  return (
    <section
      className="section-mobile-pad"
      style={{
        padding: 'clamp(50px, 6vw, 70px) clamp(16px, 4vw, 4vw) clamp(50px, 7vw, 90px) clamp(16px, 4vw, 4vw)',
      }}
      aria-label={t('gemini.title', 'Powered by Google Gemini · Transparent AI')}
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
          {/* Top Multi-Color Gradient Line */}
          <div
            style={{
              height: '6px',
              width: '100%',
              background: 'linear-gradient(90deg, #F59E0B 0%, #10B981 33%, #2563EB 66%, #F46036 100%)',
            }}
          />

          <div
            className="section-inner-card"
            style={{
              padding: '40px 36px 44px 36px',
            }}
          >
            {/* Header with Warm Golden Yellow Badge */}
            <div style={{ marginBottom: '20px' }}>
              <div
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '5px 14px',
                  borderRadius: '999px',
                  backgroundColor: '#FEF3C7',
                  border: '1px solid #FCD34D',
                  color: '#92400E',
                  fontSize: '0.84rem',
                  fontWeight: 800,
                  letterSpacing: '0.5px',
                  textTransform: 'uppercase',
                  marginBottom: '10px',
                  boxShadow: '0 2px 6px rgba(245, 158, 11, 0.15)',
                }}
              >
                <Sparkles size={15} style={{ color: '#D97706' }} />
                <span>{t('gemini.badge', 'Transparent AI · Built for Indian Field Conditions')}</span>
              </div>

              <h2
                style={{
                  fontSize: 'clamp(1.9rem, 3.1vw, 2.6rem)',
                  margin: 0,
                  fontWeight: 800,
                  color: '#000000',
                  lineHeight: 1.15,
                }}
              >
                {t('gemini.title', 'Powered by Google Gemini · Transparent AI')}
              </h2>
            </div>

            <p
              style={{
                color: '#111111',
                fontSize: 'clamp(1.05rem, 1.2vw, 1.15rem)',
                lineHeight: 1.6,
                margin: '0 0 32px 0',
                maxWidth: '960px',
                fontWeight: 600,
              }}
            >
              {t(
                'gemini.desc',
                'We use Google Gemini strictly where it solves real barriers for flood-affected families — converting spoken village dialects into verified government claim documents without requiring typing or paperwork:'
              )}
            </p>

            {/* Two Richly-styled Feature Cards */}
            <div
              className="gemini-features-grid"
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                gap: '24px',
              }}
            >
              {/* Feature 1: Speech & Dialect (Turmeric Amber / Yellow Theme) */}
              <div
                className="card-hover gemini-feature-card"
                style={{
                  backgroundColor: '#FFFDF7',
                  borderRadius: '18px',
                  border: '1.5px solid #FDE68A',
                  padding: '28px 24px',
                  display: 'flex',
                  gap: '18px',
                  boxShadow: '0 4px 16px rgba(245, 158, 11, 0.08)',
                }}
              >
                <div
                  style={{
                    backgroundColor: '#FEF3C7',
                    border: '1px solid #FCD34D',
                    width: '50px',
                    height: '50px',
                    borderRadius: '14px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#D97706',
                    flexShrink: 0,
                  }}
                >
                  <MessageSquareQuote size={26} />
                </div>
                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      display: 'inline-block',
                      padding: '3px 8px',
                      borderRadius: '6px',
                      fontSize: '0.72rem',
                      fontWeight: 800,
                      letterSpacing: '0.5px',
                      backgroundColor: '#FEF3C7',
                      color: '#92400E',
                      marginBottom: '8px',
                    }}
                  >
                    {t('gemini.card1Tag', '6 INDIC LANGUAGES')}
                  </div>
                  <strong
                    style={{
                      display: 'block',
                      fontSize: '1.18rem',
                      color: '#000000',
                      marginBottom: '8px',
                      fontWeight: 800,
                    }}
                  >
                    {t('gemini.card1Title', 'Gemini Speech & Dialect Understanding')}
                  </strong>
                  <p
                    style={{
                      fontSize: '0.94rem',
                      color: '#1A1A1A',
                      lineHeight: 1.6,
                      margin: 0,
                      fontWeight: 600,
                    }}
                  >
                    {t(
                      'gemini.card1Desc',
                      'Understands spoken accounts in Hindi, Bengali, Marathi, Telugu, Tamil & English. Translates rural idioms into structured SDRF compensation line items (mud wall collapse, submerged paddy, cattle loss).'
                    )}
                  </p>
                </div>
              </div>

              {/* Feature 2: Damage Scoring & Reason (Royal Blue & Green Theme) */}
              <div
                className="card-hover gemini-feature-card"
                style={{
                  backgroundColor: '#F8FBFF',
                  borderRadius: '18px',
                  border: '1.5px solid #BAE6FD',
                  padding: '28px 24px',
                  display: 'flex',
                  gap: '18px',
                  boxShadow: '0 4px 16px rgba(37, 99, 235, 0.08)',
                }}
              >
                <div
                  style={{
                    backgroundColor: '#DBEAFE',
                    border: '1px solid #BFDBFE',
                    width: '50px',
                    height: '50px',
                    borderRadius: '14px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#2563EB',
                    flexShrink: 0,
                  }}
                >
                  <ScanEye size={26} />
                </div>
                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      display: 'inline-block',
                      padding: '3px 8px',
                      borderRadius: '6px',
                      fontSize: '0.72rem',
                      fontWeight: 800,
                      letterSpacing: '0.5px',
                      backgroundColor: '#DBEAFE',
                      color: '#1E40AF',
                      marginBottom: '8px',
                    }}
                  >
                    {t('gemini.card2Tag', 'OBJECTIVE EVIDENCE')}
                  </div>
                  <strong
                    style={{
                      display: 'block',
                      fontSize: '1.18rem',
                      color: '#000000',
                      marginBottom: '8px',
                      fontWeight: 800,
                    }}
                  >
                    {t('gemini.card2Title', 'Gemini Damage Scoring & Reason Explanations')}
                  </strong>
                  <p
                    style={{
                      fontSize: '0.94rem',
                      color: '#1A1A1A',
                      lineHeight: 1.6,
                      margin: 0,
                      fontWeight: 600,
                    }}
                  >
                    {t(
                      'gemini.card2Desc',
                      'Analyzes photos of broken roofs and water marks, outputting plain-text evidentiary reasons and damage levels for inspecting officers instead of arbitrary black-box scores.'
                    )}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default PoweredByGemini;
