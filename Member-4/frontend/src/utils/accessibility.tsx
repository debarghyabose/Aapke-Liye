// src/utils/accessibility.tsx
import React, { createContext, useContext, useEffect, useState } from 'react';

interface A11yContextType {
  highContrast: boolean;
  toggleHighContrast: () => void;
  largerText: boolean;
  toggleLargerText: () => void;
  announce: (message: string) => void;
}

export const A11yContext = createContext<A11yContextType>({
  highContrast: false,
  toggleHighContrast: () => {},
  largerText: false,
  toggleLargerText: () => {},
  announce: () => {},
});

export const useA11y = () => useContext(A11yContext);

export const A11yProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [highContrast, setHighContrast] = useState<boolean>(() => {
    try {
      return localStorage.getItem('a11y_high_contrast') === 'true';
    } catch {
      return false;
    }
  });

  const [largerText, setLargerText] = useState<boolean>(() => {
    try {
      return localStorage.getItem('a11y_larger_text') === 'true';
    } catch {
      return false;
    }
  });

  const [liveAnnouncement, setLiveAnnouncement] = useState<string>('');

  useEffect(() => {
    if (highContrast) {
      document.documentElement.classList.add('high-contrast');
    } else {
      document.documentElement.classList.remove('high-contrast');
    }
    try {
      localStorage.setItem('a11y_high_contrast', String(highContrast));
    } catch {
      // ignore
    }
  }, [highContrast]);

  useEffect(() => {
    if (largerText) {
      document.documentElement.classList.add('larger-text');
    } else {
      document.documentElement.classList.remove('larger-text');
    }
    try {
      localStorage.setItem('a11y_larger_text', String(largerText));
    } catch {
      // ignore
    }
  }, [largerText]);

  const toggleHighContrast = () => setHighContrast((prev) => !prev);
  const toggleLargerText = () => setLargerText((prev) => !prev);

  const announce = (message: string) => {
    setLiveAnnouncement(message);
    setTimeout(() => setLiveAnnouncement(''), 4000);
  };

  return (
    <A11yContext.Provider
      value={{
        highContrast,
        toggleHighContrast,
        largerText,
        toggleLargerText,
        announce,
      }}
    >
      {children}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
        style={{
          position: 'absolute',
          width: '1px',
          height: '1px',
          margin: '-1px',
          padding: 0,
          overflow: 'hidden',
          clip: 'rect(0, 0, 0, 0)',
          border: 0,
        }}
      >
        {liveAnnouncement}
      </div>
    </A11yContext.Provider>
  );
};
