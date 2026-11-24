// src/pages/Hero.tsx
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { ArrowRight, Search, Volume2 } from 'lucide-react';
import { speakText } from '../utils/tts';

export const Hero: React.FC = () => {
  const { t, i18n } = useTranslation();

  const handleListenHero = () => {
    const textToRead = `${t(
      'hero.title',
      "Lost your home to the water? Your relief shouldn't be lost too."
    )}. ${t(
      'hero.subtitle',
      'Speak in your own language. Show what was damaged. We prepare your government relief claim — even if your papers are gone.'
    )}`;
    speakText(textToRead, i18n.language);
  };

  return (
    <>
      {/* ================= HERO ILLUSTRATION SECTION (100% UNIFORM ALIGNMENT ACROSS ALL LANGUAGES) ================= */}
      <section
        className="hero-section-wrap"
        style={{
          position: 'relative',
          width: '100%',
          minHeight: '100vh',
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'flex-start',
          backgroundColor: '#E4ECEF',
        }}
        aria-label="Disaster Relief Hero"
      >
        {/* Background Illustrated Image: Exact 1024x571 with Serene River-Blue Water */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            overflow: 'hidden',
            zIndex: 1,
          }}
        >
          <img
            src="/Mother_speaking_into_phone_81a00bd8.jpg"
            alt={t('hero.altHero', 'A mother speaking into the Aapke Liye app beside her flooded home')}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              objectPosition: 'right center',
              display: 'block',
            }}
          />
        </div>

        {/* Soft, delicate mist on the left: ensures bold black text is 100% crisp and readable while keeping the full image visible */}
        <div
          className="hero-mist-overlay"
          style={{
            position: 'absolute',
            inset: 0,
            background:
              'linear-gradient(90deg, rgba(255, 255, 255, 0.72) 0%, rgba(255, 255, 255, 0.42) 36%, rgba(255, 255, 255, 0.1) 54%, transparent 72%)',
            zIndex: 2,
            pointerEvents: 'none',
          }}
        />

        {/* Main Content Area: Aligned proudly across the open space, bold, elegant & prominent */}
        <div
          className="hero-content-wrap"
          style={{
            position: 'relative',
            zIndex: 10,
            width: '100%',
            maxWidth: '1440px',
            margin: '0 auto',
            padding: 'clamp(40px, 6vw, 80px) clamp(24px, 5vw, 80px) 40px clamp(24px, 5vw, 80px)',
            display: 'flex',
            alignItems: 'flex-start',
            boxSizing: 'border-box',
            minHeight: 'calc(100vh - 70px)',
          }}
        >
          <div
            className="hero-content-box"
            style={{
              maxWidth: 'clamp(320px, 60vw, 780px)',
              width: '100%',
              textAlign: 'left',
              marginTop: 'clamp(10px, 3vw, 32px)',
            }}
          >
            {/* H1 Title: Bold, Elegant Pure Black Headline Filling the Page Proudly */}
            <h1
              style={{
                fontSize: 'clamp(2.6rem, 4.5vw, 4.5rem)',
                lineHeight: 1.12,
                fontWeight: 900,
                color: '#000000',
                marginBottom: '20px',
                letterSpacing: '-0.02em',
                wordBreak: 'break-word',
                overflowWrap: 'break-word',
                textShadow:
                  '0 2px 6px rgba(255, 255, 255, 0.98), 0 0 18px rgba(255, 255, 255, 0.95), 0 0 32px rgba(255, 255, 255, 0.88)',
              }}
            >
              {t('hero.title', "Lost your home to the water? Your relief shouldn't be lost too.")}
            </h1>

            {/* Subtitle: Pure Bold Black, Clean & Highly Readable */}
            <p
              style={{
                fontSize: 'clamp(1.3rem, 1.7vw, 1.65rem)',
                lineHeight: 1.5,
                color: '#000000',
                marginBottom: '28px',
                maxWidth: '680px',
                fontWeight: 700,
                wordBreak: 'break-word',
                overflowWrap: 'break-word',
                textShadow:
                  '0 1px 4px rgba(255, 255, 255, 0.98), 0 0 14px rgba(255, 255, 255, 0.92)',
              }}
            >
              {t(
                'hero.subtitle',
                'Speak in your own language. Show what was damaged. We prepare your government relief claim — even if your papers are gone.'
              )}
            </p>

            {/* Action Buttons: Side-by-Side on desktop, stacked on mobile */}
            <div
              className="hero-buttons-row"
              style={{
                display: 'flex',
                flexDirection: 'row',
                flexWrap: 'nowrap',
                gap: '14px',
                alignItems: 'center',
                marginBottom: '20px',
                width: '100%',
              }}
            >
              {/* Orange Action Button */}
              <Link
                to="/claim"
                className="btn-pill btn-orange-pill"
                style={{
                  gap: '10px',
                  padding: '14px 32px',
                  minHeight: '54px',
                  fontSize: 'clamp(1.15rem, 1.3vw, 1.35rem)',
                  fontWeight: 900,
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                }}
              >
                <span>{t('hero.start', 'Start my claim →')}</span>
              </Link>

              {/* Pure Black Bold Outline Button */}
              <Link
                to="/track"
                className="btn-pill btn-outline-pill"
                style={{
                  gap: '10px',
                  padding: '14px 32px',
                  minHeight: '54px',
                  fontSize: 'clamp(1.15rem, 1.3vw, 1.35rem)',
                  fontWeight: 900,
                  color: '#000000 !important',
                  borderColor: '#000000',
                  borderWidth: '2px',
                  backgroundColor: 'rgba(255, 255, 255, 0.94)',
                  backdropFilter: 'blur(8px)',
                  WebkitBackdropFilter: 'blur(8px)',
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                }}
              >
                <Search size={20} aria-hidden="true" style={{ color: '#000000' }} />
                <span style={{ color: '#000000' }}>{t('hero.track', 'Track my claim')}</span>
              </Link>
            </div>

            {/* Free Note: Bold Black Single Line */}
            <div
              style={{
                fontSize: '1.18rem',
                color: '#000000',
                fontWeight: 800,
                display: 'flex',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '8px',
                marginTop: '6px',
                textShadow: '0 1px 4px rgba(255, 255, 255, 0.98)',
              }}
            >
              <span style={{ color: '#000000', fontSize: '1.2rem' }}>●</span>
              <span>{t('hero.note', 'Free for every family. Always.')}</span>
            </div>
          </div>
        </div>

        {/* Listen Button: Perfectly aligned at the Gemini Star Position with prominent touch target */}
        <button
          onClick={handleListenHero}
          className="btn-outline-pill hero-listen-star-btn"
          style={{
            position: 'absolute',
            right: 'clamp(20px, 5vw, 64px)',
            bottom: 'clamp(36px, 6.5vw, 70px)',
            zIndex: 25,
            padding: '12px 26px',
            minHeight: '52px',
            fontSize: '1.1rem',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            cursor: 'pointer',
            color: '#000000',
            fontWeight: 900,
            borderColor: '#000000',
            borderWidth: '2px',
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(8px)',
            WebkitBackdropFilter: 'blur(8px)',
            borderRadius: '999px',
            boxShadow: '0 4px 18px rgba(0, 0, 0, 0.22)',
            whiteSpace: 'nowrap',
          }}
          aria-label={t('hero.listenButton', 'Listen in your language')}
        >
          <Volume2 size={20} style={{ color: '#000000' }} />
          <span>{t('hero.listenButton', 'Listen in your language')}</span>
        </button>
      </section>

      {/* ================= ELEGANT WHITE STAT STRIP PLACED DOWN AT THE WHITE PART ================= */}
      <div
        style={{
          width: '100%',
          backgroundColor: '#FFFFFF',
          borderTop: '1.5px solid rgba(0, 0, 0, 0.12)',
          borderBottom: '1.5px solid rgba(0, 0, 0, 0.08)',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.04)',
          position: 'relative',
          zIndex: 10,
        }}
      >
        <div
          className="stat-strip-inner"
          style={{
            maxWidth: '1440px',
            margin: '0 auto',
            padding: '28px 5vw',
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '24px',
          }}
        >
          {/* 3 Facts: Bold Black Numbers & Labels */}
          <div
            className="stat-strip-facts"
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              gap: '32px',
            }}
          >
            {/* Fact 1 */}
            <div className="stat-fact-item" style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
              <span
                className="stat-fact-num"
                style={{
                  fontSize: '2.8rem',
                  fontWeight: 900,
                  color: '#000000',
                  lineHeight: 1,
                }}
              >
                {t('stats.numLanguages', '6')}
              </span>
              <span className="stat-fact-label" style={{ fontSize: '1.18rem', fontWeight: 800, color: '#000000' }}>
                {t('stats.labelLanguages', 'Indian languages')}
              </span>
            </div>

            <div
              style={{
                width: '1.5px',
                height: '32px',
                backgroundColor: 'rgba(0, 0, 0, 0.25)',
              }}
              className="hidden-mobile"
            />

            {/* Fact 2 */}
            <div className="stat-fact-item" style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
              <span
                className="stat-fact-num"
                style={{
                  fontSize: '2.8rem',
                  fontWeight: 900,
                  color: '#000000',
                  lineHeight: 1,
                }}
              >
                {t('stats.numStates', '5')}
              </span>
              <span className="stat-fact-label" style={{ fontSize: '1.18rem', fontWeight: 800, color: '#000000' }}>
                {t('stats.labelStates', "states' SDRF rules")}
              </span>
            </div>

            <div
              style={{
                width: '1.5px',
                height: '32px',
                backgroundColor: 'rgba(0, 0, 0, 0.25)',
              }}
              className="hidden-mobile"
            />

            {/* Fact 3 */}
            <div className="stat-fact-item" style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
              <span
                className="stat-fact-num"
                style={{
                  fontSize: '2.8rem',
                  fontWeight: 900,
                  color: '#000000',
                  lineHeight: 1,
                }}
              >
                {t('stats.numInternet', '0')}
              </span>
              <span className="stat-fact-label" style={{ fontSize: '1.18rem', fontWeight: 800, color: '#000000' }}>
                {t('stats.labelInternet', 'internet needed to start')}
              </span>
            </div>
          </div>

          {/* Right side info: Gemini-powered claims for disaster-hit families · See how it works */}
          <div
            className="stat-strip-right"
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'flex-start',
              gap: '4px',
            }}
          >
            <span
              style={{
                fontSize: '1.18rem',
                fontWeight: 900,
                color: '#000000',
              }}
            >
              {t('stats.geminiNote', 'Gemini-powered claims for disaster-hit families')}
            </span>
            <a
              href="#how-it-works"
              style={{
                color: '#000000',
                fontWeight: 800,
                fontSize: '1.12rem',
                textDecoration: 'underline',
                textUnderlineOffset: '4px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                minHeight: '44px',
              }}
            >
              <span>{t('stats.seeHow', 'See how it works →')}</span>
            </a>
          </div>
        </div>
      </div>
    </>
  );
};

export default Hero;
