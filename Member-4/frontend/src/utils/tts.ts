// src/utils/tts.ts
// Web Speech API wrapper for multi-lingual TTS with automatic language alignment
import i18n from '../i18n';

const LANG_CODE_MAP: Record<string, string> = {
  en: 'en-IN',
  hi: 'hi-IN',
  bn: 'bn-IN',
  mr: 'mr-IN',
  te: 'te-IN',
  ta: 'ta-IN',
};

let currentUtterance: SpeechSynthesisUtterance | null = null;

export function stopSpeaking() {
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
}

export function speakText(
  text: string,
  lang?: string,
  onEnd?: () => void,
  onError?: (err: any) => void
): boolean {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
    console.warn('Speech synthesis is not supported on this browser.');
    if (onEnd) onEnd();
    return false;
  }

  try {
    stopSpeaking();

    const selectedCode = (lang || i18n.language || 'en').split('-')[0];
    const targetLang = LANG_CODE_MAP[selectedCode] || 'en-IN';

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = targetLang;
    utterance.rate = 0.92; // Clear pacing for rural disaster response
    utterance.pitch = 1.0;

    // Pick a matching voice if available
    const voices = window.speechSynthesis.getVoices();
    const matchedVoice = voices.find(
      (v) =>
        v.lang.toLowerCase().startsWith(selectedCode.toLowerCase()) ||
        v.lang.toLowerCase().includes(targetLang.toLowerCase())
    );
    if (matchedVoice) {
      utterance.voice = matchedVoice;
    }

    utterance.onend = () => {
      currentUtterance = null;
      if (onEnd) onEnd();
    };

    utterance.onerror = (e) => {
      console.warn('SpeechSynthesis error:', e);
      currentUtterance = null;
      if (onError) onError(e);
      if (onEnd) onEnd();
    };

    currentUtterance = utterance;
    window.speechSynthesis.speak(utterance);
    return true;
  } catch (error) {
    console.warn('Failed to initiate TTS:', error);
    if (onError) onError(error);
    if (onEnd) onEnd();
    return false;
  }
}
