// src/pages/ForOfficialsTeaser.tsx
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { ShieldCheck, CopyCheck, ArrowRight, FileSpreadsheet, Building2, Users } from 'lucide-react';

export const ForOfficialsTeaser: React.FC = () => {
  const { t } = useTranslation();

  return (
    <section
      className="section-mobile-pad"
      style={{
        padding: 'clamp(50px, 6vw, 80px) clamp(16px, 4vw, 4vw)',
      }}
      aria-labelledby="for-officials-heading"
    >
      <div
        style={{
          maxWidth: '1380px',
          margin: '0 auto',
        }}
      >
        <div
          className="officials-grid-wrap"
          style={{
            backgroundColor: '#FFFFFF',
            borderRadius: '24px',
            border: '1.5px solid var(--border)',
            boxShadow: '0 8px 30px rgba(14, 42, 56, 0.07)',
            overflow: 'hidden',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            alignItems: 'center',
          }}
        >
          {/* Left Column: Info & Action */}
          <div
            className="officials-left-col"
            style={{
              padding: '44px 40px',
              borderRight: '1px solid #EDF3F6',
            }}
          >
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '4px 14px',
                borderRadius: '999px',
                backgroundColor: '#EFF6FF',
                border: '1px solid #BFDBFE',
                color: '#1D4ED8',
                fontSize: '0.8rem',
                fontWeight: 800,
                letterSpacing: '0.5px',
                textTransform: 'uppercase',
                marginBottom: '14px',
              }}
            >
              <Building2 size={15} style={{ color: '#2563EB' }} />
              <span>{t('forOfficials.badge', 'Government Administration')}</span>
            </div>

            <h2
              id="for-officials-heading"
              style={{
                fontSize: 'clamp(1.9rem, 2.9vw, 2.5rem)',
                margin: '0 0 16px 0',
                color: '#000000',
                fontWeight: 800,
                lineHeight: 1.18,
              }}
            >
              {t('forOfficials.title', 'For District Magistrates, BDOs, and Revenue Officers')}
            </h2>

            <p
              style={{
                color: '#111111',
                lineHeight: 1.6,
                marginBottom: '28px',
                fontSize: 'clamp(1.05rem, 1.2vw, 1.15rem)',
                fontWeight: 600,
              }}
            >
              {t(
                'forOfficials.desc',
                'Eliminate paper backlogs after inundation. Inspect GPS geotags, timestamp watermarks, AI damage scores, and cross-claim duplicate photo flags in one consolidated portal.'
              )}
            </p>

            <Link
              to="/official"
              className="btn-pill btn-dark-teal"
              style={{
                display: 'inline-flex',
                gap: '10px',
                fontSize: '1.08rem',
                fontWeight: 800,
                backgroundColor: '#1A4B75',
                color: '#FFFFFF',
                boxShadow: '0 4px 14px rgba(26, 75, 117, 0.3)',
                minHeight: '48px',
                padding: '12px 28px',
              }}
            >
              <span>{t('forOfficials.openPortal', 'Open Official Verification Portal')}</span>
              <ArrowRight size={18} aria-hidden="true" style={{ color: '#FCD34D' }} />
            </Link>
          </div>

          {/* Right Column: 4 Tool Cards with Vibrant Colorful Accents */}
          <div
            className="officials-right-col officials-tools-grid"
            style={{
              padding: '36px 32px',
              backgroundColor: '#F8FBFC',
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: '16px',
            }}
          >
            {/* 1. GPS & EXIF Checks (Emerald Green) */}
            <div
              className="card-hover"
              style={{
                backgroundColor: '#FFFFFF',
                padding: '20px',
                borderRadius: '16px',
                border: '1.5px solid #A7F3D0',
                boxShadow: '0 2px 8px rgba(16, 185, 129, 0.08)',
              }}
            >
              <div
                style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '10px',
                  backgroundColor: '#D1FAE5',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#059669',
                  marginBottom: '10px',
                }}
              >
                <ShieldCheck size={22} />
              </div>
              <div style={{ fontWeight: 800, fontSize: '1rem', color: '#000000' }}>
                {t('forOfficials.card1Title', 'GPS & EXIF Checks')}
              </div>
              <div style={{ fontSize: '0.84rem', color: '#1A1A1A', marginTop: '6px', lineHeight: 1.5, fontWeight: 600 }}>
                {t('forOfficials.card1Desc', 'Lat/lon geofencing matches flood inundation boundaries')}
              </div>
            </div>

            {/* 2. Duplicate Detection (Warm Golden Yellow) */}
            <div
              className="card-hover"
              style={{
                backgroundColor: '#FFFFFF',
                padding: '20px',
                borderRadius: '16px',
                border: '1.5px solid #FDE68A',
                boxShadow: '0 2px 8px rgba(245, 158, 11, 0.08)',
              }}
            >
              <div
                style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '10px',
                  backgroundColor: '#FEF3C7',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#D97706',
                  marginBottom: '10px',
                }}
              >
                <CopyCheck size={22} />
              </div>
              <div style={{ fontWeight: 800, fontSize: '1rem', color: '#000000' }}>
                {t('forOfficials.card2Title', 'Duplicate Detection')}
              </div>
              <div style={{ fontSize: '0.84rem', color: '#1A1A1A', marginTop: '6px', lineHeight: 1.5, fontWeight: 600 }}>
                {t('forOfficials.card2Desc', 'Cross-checks photos to prevent double claiming across wards')}
              </div>
            </div>

            {/* 3. Prioritise Vulnerable (Royal Blue) */}
            <div
              className="card-hover"
              style={{
                backgroundColor: '#FFFFFF',
                padding: '20px',
                borderRadius: '16px',
                border: '1.5px solid #BFDBFE',
                boxShadow: '0 2px 8px rgba(37, 99, 235, 0.08)',
              }}
            >
              <div
                style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '10px',
                  backgroundColor: '#DBEAFE',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#2563EB',
                  marginBottom: '10px',
                }}
              >
                <Users size={22} />
              </div>
              <div style={{ fontWeight: 800, fontSize: '1rem', color: '#000000' }}>
                {t('forOfficials.card3Title', 'Prioritise Vulnerable')}
              </div>
              <div style={{ fontSize: '0.84rem', color: '#1A1A1A', marginTop: '6px', lineHeight: 1.5, fontWeight: 600 }}>
                {t('forOfficials.card3Desc', 'Single mothers, elderly, & disabled flagged to top of queue')}
              </div>
            </div>

            {/* 4. One-Click Export (Terracotta Orange) */}
            <div
              className="card-hover"
              style={{
                backgroundColor: '#FFFFFF',
                padding: '20px',
                borderRadius: '16px',
                border: '1.5px solid #FED7AA',
                boxShadow: '0 2px 8px rgba(234, 88, 12, 0.08)',
              }}
            >
              <div
                style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '10px',
                  backgroundColor: '#FFEDD5',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#EA580C',
                  marginBottom: '10px',
                }}
              >
                <FileSpreadsheet size={22} />
              </div>
              <div style={{ fontWeight: 800, fontSize: '1rem', color: '#000000' }}>
                {t('forOfficials.card4Title', 'One-Click Export')}
              </div>
              <div style={{ fontSize: '0.84rem', color: '#1A1A1A', marginTop: '6px', lineHeight: 1.5, fontWeight: 600 }}>
                {t('forOfficials.card4Desc', 'Standard Excel / CSV export matching State Disaster Relief formats')}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default ForOfficialsTeaser;
