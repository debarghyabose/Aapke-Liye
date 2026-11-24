// src/components/TopNav.tsx
import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Languages, Eye, Type, Menu, X, ShieldCheck, Radio } from 'lucide-react';
import { useA11y } from '../utils/accessibility';

const LANGUAGES = [
  { code: 'en', label: 'English', native: 'English' },
  { code: 'hi', label: 'Hindi', native: 'हिंदी' },
  { code: 'bn', label: 'Bengali', native: 'বাংলা' },
  { code: 'mr', label: 'Marathi', native: 'मराठी' },
  { code: 'te', label: 'Telugu', native: 'తెలుగు' },
  { code: 'ta', label: 'Tamil', native: 'தமிழ்' },
];

export const TopNav: React.FC = () => {
  const { i18n, t } = useTranslation();
  const location = useLocation();
  const { highContrast, toggleHighContrast, largerText, toggleLargerText } = useA11y();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const changeLanguage = (code: string) => {
    i18n.changeLanguage(code);
  };

  const currentLangCode = (i18n.language || 'en').split('-')[0];

  return (
    <header
      style={{
        position: 'sticky',
        top: 0,
        left: 0,
        width: '100%',
        zIndex: 50,
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        backdropFilter: 'blur(14px)',
        WebkitBackdropFilter: 'blur(14px)',
        borderBottom: '1.5px solid rgba(0, 0, 0, 0.1)',
        boxShadow: '0 2px 14px rgba(0, 0, 0, 0.05)',
        transition: 'all 0.2s ease',
      }}
    >
      <div
        className="topnav-inner"
        style={{
          maxWidth: '1440px',
          margin: '0 auto',
          padding: '8px clamp(10px, 2.2vw, 30px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 'clamp(6px, 1.2vw, 16px)',
          width: '100%',
          boxSizing: 'border-box',
        }}
      >
        {/* Left: Prominent Brand Logo */}
        <Link
          to="/"
          style={{
            textDecoration: 'none',
            display: 'flex',
            flexDirection: 'column',
            whiteSpace: 'nowrap',
            flexShrink: 1,
            minWidth: 0,
          }}
          aria-label={t('nav.logoEnglish', 'Aapke Liye')}
        >
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px', flexWrap: 'nowrap' }}>
            <span
              style={{
                fontSize: 'clamp(1.12rem, 4.2vw, 1.7rem)',
                fontWeight: 900,
                color: '#000000',
                lineHeight: 1.1,
                letterSpacing: '-0.02em',
              }}
            >
              {t('nav.logoHindi', 'आपके लिए')}
            </span>
            <span
              style={{
                fontSize: 'clamp(1.12rem, 4.2vw, 1.7rem)',
                fontWeight: 900,
                color: '#F46036',
                lineHeight: 1.1,
                letterSpacing: '-0.02em',
              }}
            >
              {t('nav.logoEnglish', 'Aapke Liye')}
            </span>
          </div>
          <span
            style={{
              fontSize: 'clamp(0.68rem, 2.2vw, 0.74rem)',
              color: '#10B981',
              fontWeight: 800,
              letterSpacing: '0.5px',
              textTransform: 'uppercase',
              marginTop: '1px',
            }}
          >
            {t('nav.tagline', 'Disaster Relief Claims')}
          </span>
        </Link>

        {/* Center: Frosted Navigation Pill with Proportional Spaced Links */}
        <nav
          style={{
            alignItems: 'center',
            backgroundColor: 'rgba(255, 255, 255, 0.96)',
            border: '2px solid #000000',
            padding: '5px clamp(10px, 1.2vw, 18px)',
            borderRadius: '999px',
            boxShadow: '0 2px 10px rgba(0, 0, 0, 0.06)',
            gap: 'clamp(8px, 1.1vw, 16px)',
            flexShrink: 0,
          }}
          className="desktop-nav desktop-nav-pill"
        >
          <a
            href="/#how-it-works"
            style={{
              color: '#000000',
              textDecoration: 'none',
              fontWeight: 800,
              fontSize: 'clamp(0.82rem, 0.9vw, 0.92rem)',
              whiteSpace: 'nowrap',
            }}
          >
            {t('nav.howItWorks', 'How it works')}
          </a>

          <Link
            to="/prepare"
            style={{
              color: '#000000',
              textDecoration: 'none',
              fontWeight: 800,
              fontSize: 'clamp(0.82rem, 0.9vw, 0.92rem)',
              whiteSpace: 'nowrap',
              borderBottom: location.pathname === '/prepare' ? '2.5px solid #F46036' : 'none',
              paddingBottom: '2px',
            }}
          >
            {t('nav.prepare', 'Prepare')}
          </Link>

          <Link
            to="/mesh"
            style={{
              color: '#000000',
              textDecoration: 'none',
              fontWeight: 800,
              fontSize: 'clamp(0.82rem, 0.9vw, 0.92rem)',
              whiteSpace: 'nowrap',
              borderBottom: location.pathname === '/mesh' ? '2.5px solid #F46036' : 'none',
              paddingBottom: '2px',
            }}
          >
            {t('nav.mesh', 'Mesh')}
          </Link>

          <Link
            to="/official"
            style={{
              color: '#000000',
              textDecoration: 'none',
              fontWeight: 800,
              fontSize: 'clamp(0.82rem, 0.9vw, 0.92rem)',
              whiteSpace: 'nowrap',
              borderBottom: location.pathname === '/official' ? '2.5px solid #F46036' : 'none',
              paddingBottom: '2px',
            }}
          >
            {t('nav.forOfficials', 'For officials')}
          </Link>

          <Link
            to="/track"
            style={{
              color: '#000000',
              textDecoration: 'none',
              fontWeight: 800,
              fontSize: 'clamp(0.82rem, 0.9vw, 0.92rem)',
              whiteSpace: 'nowrap',
              borderBottom: location.pathname === '/track' ? '2.5px solid #F46036' : 'none',
              paddingBottom: '2px',
            }}
          >
            {t('nav.trackClaim', 'Track claim')}
          </Link>
        </nav>

        {/* Right: Language Selector + A11y Toggles */}
        <div style={{ alignItems: 'center', gap: '6px', flexShrink: 0 }} className="desktop-nav desktop-nav-right">
          {/* Language Selector Pill */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              backgroundColor: '#FFFFFF',
              border: '2px solid #000000',
              borderRadius: '999px',
              padding: '5px 8px',
              boxShadow: '0 2px 6px rgba(0, 0, 0, 0.05)',
            }}
          >
            <Languages size={15} style={{ color: '#000000' }} aria-hidden="true" />
            <select
              value={currentLangCode}
              onChange={(e) => changeLanguage(e.target.value)}
              aria-label={t('nav.selectLanguageAria', 'Select Interface Language')}
              style={{
                backgroundColor: 'transparent',
                border: 'none',
                outline: 'none',
                fontSize: '0.82rem',
                fontWeight: 800,
                color: '#000000',
                cursor: 'pointer',
              }}
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.native}
                </option>
              ))}
            </select>
          </div>

          {/* High Contrast Toggle Pill */}
          <button
            onClick={toggleHighContrast}
            title={t('nav.contrastTitle', 'Toggle High Contrast Mode')}
            aria-pressed={highContrast}
            aria-label={t('nav.contrastAria', 'Toggle High Contrast')}
            style={{
              background: highContrast ? '#000000' : '#FFFFFF',
              color: highContrast ? '#FFFFFF' : '#000000',
              border: '2px solid #000000',
              borderRadius: '999px',
              padding: '5px 10px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              cursor: 'pointer',
              fontSize: '0.82rem',
              fontWeight: 800,
              boxShadow: '0 2px 6px rgba(0, 0, 0, 0.05)',
            }}
          >
            <Eye size={15} aria-hidden="true" />
            <span>{t('nav.contrast', 'Contrast')}</span>
          </button>

          {/* Larger Text Toggle Pill */}
          <button
            onClick={toggleLargerText}
            title={t('nav.largerTextTitle', 'Toggle Larger Text Mode')}
            aria-pressed={largerText}
            aria-label={t('nav.largerTextAria', 'Toggle Larger Text')}
            style={{
              background: largerText ? '#000000' : '#FFFFFF',
              color: largerText ? '#FFFFFF' : '#000000',
              border: '2px solid #000000',
              borderRadius: '999px',
              padding: '5px 8px',
              display: 'flex',
              alignItems: 'center',
              gap: '3px',
              cursor: 'pointer',
              fontSize: '0.82rem',
              fontWeight: 800,
              boxShadow: '0 2px 6px rgba(0, 0, 0, 0.05)',
            }}
          >
            <Type size={15} aria-hidden="true" />
            <span>{t('nav.largerText', 'A+')}</span>
          </button>
        </div>

        {/* Mobile menu toggle (Visible only on smaller screens) */}
        <button
          className="mobile-menu-btn"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label={
            mobileMenuOpen
              ? t('nav.closeMenuAria', 'Close navigation menu')
              : t('nav.openMenuAria', 'Open navigation menu')
          }
          style={{
            background: '#FFFFFF',
            borderRadius: '999px',
            border: '2px solid #000000',
            cursor: 'pointer',
            padding: '10px 14px',
            minHeight: '48px',
            minWidth: '48px',
            color: '#000000',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
          }}
        >
          {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div
          style={{
            padding: '24px 6vw',
            backgroundColor: '#FFFFFF',
            borderTop: '2px solid #000000',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
          }}
        >
          {/* Mobile Language Switcher */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 18px',
              minHeight: '48px',
              backgroundColor: '#F8FBFC',
              borderRadius: '999px',
              border: '2px solid #000000',
            }}
          >
            <Languages size={20} style={{ color: '#000000' }} />
            <select
              value={currentLangCode}
              onChange={(e) => changeLanguage(e.target.value)}
              aria-label={t('nav.selectLanguageAria', 'Select Interface Language')}
              style={{
                width: '100%',
                backgroundColor: 'transparent',
                border: 'none',
                outline: 'none',
                fontWeight: 800,
                fontSize: '1.05rem',
                color: '#000000',
                cursor: 'pointer',
              }}
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.native} ({l.label})
                </option>
              ))}
            </select>
          </div>

          <a
            href="/#how-it-works"
            onClick={() => setMobileMenuOpen(false)}
            style={{ color: '#000000', textDecoration: 'none', fontWeight: 800, fontSize: '1.25rem', minHeight: '48px', display: 'flex', alignItems: 'center' }}
          >
            {t('nav.howItWorks', 'How it works')}
          </a>
          <Link
            to="/prepare"
            onClick={() => setMobileMenuOpen(false)}
            style={{ color: '#000000', textDecoration: 'none', fontWeight: 800, fontSize: '1.25rem', minHeight: '48px', display: 'flex', alignItems: 'center' }}
          >
            {t('nav.prepare', 'Prepare (Vault)')}
          </Link>
          <Link
            to="/mesh"
            onClick={() => setMobileMenuOpen(false)}
            style={{ color: '#000000', textDecoration: 'none', fontWeight: 800, fontSize: '1.25rem', minHeight: '48px', display: 'flex', alignItems: 'center' }}
          >
            {t('nav.mesh', 'Mesh Relay')}
          </Link>
          <Link
            to="/official"
            onClick={() => setMobileMenuOpen(false)}
            style={{ color: '#000000', textDecoration: 'none', fontWeight: 800, fontSize: '1.25rem', minHeight: '48px', display: 'flex', alignItems: 'center' }}
          >
            {t('nav.forOfficials', 'For officials')}
          </Link>
          <Link
            to="/track"
            onClick={() => setMobileMenuOpen(false)}
            style={{ color: '#000000', textDecoration: 'none', fontWeight: 800, fontSize: '1.25rem', minHeight: '48px', display: 'flex', alignItems: 'center' }}
          >
            {t('nav.trackClaim', 'Track claim')}
          </Link>

          <div style={{ display: 'flex', gap: '10px', paddingTop: '8px' }}>
            <button
              onClick={toggleHighContrast}
              style={{
                flex: 1,
                padding: '12px',
                minHeight: '48px',
                borderRadius: '999px',
                border: '2px solid #000000',
                background: highContrast ? '#000000' : '#FFFFFF',
                color: highContrast ? '#FFFFFF' : '#000000',
                fontWeight: 800,
                fontSize: '1rem',
                cursor: 'pointer',
              }}
            >
              {t('nav.contrast', 'Contrast')}
            </button>
            <button
              onClick={toggleLargerText}
              style={{
                flex: 1,
                padding: '12px',
                minHeight: '48px',
                borderRadius: '999px',
                border: '2px solid #000000',
                background: largerText ? '#000000' : '#FFFFFF',
                color: largerText ? '#FFFFFF' : '#000000',
                fontWeight: 800,
                fontSize: '1rem',
                cursor: 'pointer',
              }}
            >
              {t('nav.largerText', 'A+')}
            </button>
          </div>
        </div>
      )}
    </header>
  );
};

export default TopNav;
