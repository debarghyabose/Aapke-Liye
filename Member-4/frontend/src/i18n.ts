// src/i18n.ts
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import translationEN from './locales/en.json';
import translationHI from './locales/hi.json';
import translationBN from './locales/bn.json';
import translationMR from './locales/mr.json';
import translationTE from './locales/te.json';
import translationTA from './locales/ta.json';

const savedLang = (() => {
  try {
    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      const urlLng = urlParams.get('lng') || urlParams.get('lang');
      if (urlLng && ['en', 'hi', 'bn', 'mr', 'te', 'ta'].includes(urlLng.toLowerCase())) {
        return urlLng.toLowerCase();
      }
    }
    const stored = localStorage.getItem('preferred_lang') || localStorage.getItem('i18nextLng');
    if (stored) {
      const code = stored.split('-')[0];
      if (['en', 'hi', 'bn', 'mr', 'te', 'ta'].includes(code)) {
        return code;
      }
    }
  } catch {
    // ignore
  }
  return 'en';
})();

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: translationEN },
      hi: { translation: translationHI },
      bn: { translation: translationBN },
      mr: { translation: translationMR },
      te: { translation: translationTE },
      ta: { translation: translationTA },
    },
    lng: savedLang,
    fallbackLng: 'en',
    interpolation: { escapeValue: false },
  });

// Automatically sync <html lang="..."> and save to localStorage
if (typeof document !== 'undefined') {
  document.documentElement.lang = i18n.language || savedLang;
}

i18n.on('languageChanged', (lng) => {
  const code = (lng || 'en').split('-')[0];
  if (typeof document !== 'undefined') {
    document.documentElement.lang = code;
  }
  try {
    localStorage.setItem('preferred_lang', code);
    localStorage.setItem('i18nextLng', code);
  } catch {
    // ignore
  }
});

export default i18n;
