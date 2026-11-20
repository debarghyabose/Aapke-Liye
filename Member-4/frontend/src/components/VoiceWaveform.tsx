// src/components/VoiceWaveform.tsx
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

export const VoiceWaveform: React.FC<{ isRecording: boolean }> = ({ isRecording }) => {
  const { t } = useTranslation();
  const [bars, setBars] = useState<number[]>([15, 25, 40, 20, 50, 30, 60, 25, 45, 15]);

  useEffect(() => {
    if (!isRecording) return;
    const interval = setInterval(() => {
      setBars(Array.from({ length: 12 }, () => Math.floor(Math.random() * 50) + 15));
    }, 120);
    return () => clearInterval(interval);
  }, [isRecording]);

  if (!isRecording) return null;

  return (
    <div
      aria-label={t('waveform.aria', 'Sound recording active waveform')}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '6px',
        height: '60px',
        margin: '16px 0',
      }}
    >
      {bars.map((height, idx) => (
        <div
          key={idx}
          style={{
            width: '6px',
            height: `${height}px`,
            backgroundColor: '#C0582F',
            borderRadius: '4px',
            transition: 'height 0.12s ease-in-out',
          }}
        />
      ))}
    </div>
  );
};
