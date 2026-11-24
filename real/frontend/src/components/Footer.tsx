// src/components/Footer.tsx
import React from 'react';
import { useTranslation } from 'react-i18next';
import { ShieldCheck, HeartHandshake } from 'lucide-react';

export const Footer: React.FC = () => {
  const { t } = useTranslation();

  return (
    <footer
      style={{
        backgroundColor: 'var(--water-deep)',
        color: '#FFFFFF',
        padding: '48px 6vw 40px 6vw',
        marginTop: 'auto',
        borderTop: '1px solid rgba(255, 255, 255, 0.15)',
      }}
    >
      <div
        style={{
          maxWidth: '1280px',
          margin: '0 auto',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
          gap: '20px',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            color: '#FFFFFF',
            fontWeight: 700,
            fontSize: '1.15rem',
            fontFamily: "'Plus Jakarta Sans', sans-serif",
          }}
        >
          <HeartHandshake size={22} style={{ color: '#F2F6F7' }} />
          <span>{t('footer.team', 'Team OPUS · IEM Kolkata')}</span>
        </div>

        <div
          className="footer-dpdp"
          style={{
            maxWidth: '780px',
            fontSize: '0.98rem',
            color: 'rgba(255, 255, 255, 0.95)',
            lineHeight: 1.6,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '10px',
          }}
        >
          <ShieldCheck size={22} style={{ color: '#D9F0E1', flexShrink: 0 }} />
          <span>
            <strong>{t('footer.dpdpTitle', 'Digital Personal Data Protection (DPDP) Act Note:')}</strong>{' '}
            {t(
              'footer.dpdpBody',
              'Your speech recordings, photos, and personal information are encrypted on-device, handled in accordance with Indian DPDP standards, and used strictly to generate your official government SDRF relief dossier.'
            )}
          </span>
        </div>

        <div style={{ fontSize: '0.92rem', color: 'rgba(255, 255, 255, 0.82)', marginTop: '8px', fontWeight: 600 }}>
          {t(
            'footer.compliance',
            'Free public relief service for every flood-affected family. Compliant with MHA 2022–26 SDRF / NDRF norms.'
          )}
        </div>
      </div>
    </footer>
  );
};

export default Footer;
