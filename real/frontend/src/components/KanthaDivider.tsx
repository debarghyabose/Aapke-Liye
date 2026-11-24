// src/components/KanthaDivider.tsx
import React from 'react';

export const KanthaDivider: React.FC = () => {
  return (
    <div
      style={{
        width: '100%',
        height: '1px',
        backgroundColor: 'var(--border)',
        opacity: 0.6,
        margin: '0',
      }}
      aria-hidden="true"
    />
  );
};
