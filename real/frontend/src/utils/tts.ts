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

const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
let currentAudio: HTMLAudioElement | null = null;

export function stopSpeaking() {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
}

/**
 * Reads text aloud. In live mode the backend's voice (Member 1, gTTS) is used first, because
 * most Windows PCs and many phones have no Hindi/Bengali/Tamil/Telugu/Marathi voice
 * installed. The browser's own voice is the fallback.
 */
export function speakText(
  text: string,
  lang?: string,
  onEnd?: () => void,
  onError?: (err: any) => void
): boolean {
  const code = (lang || i18n.language || 'en').split('-')[0];
  if (!API_URL) return speakWithBrowser(text, code, onEnd, onError);
  stopSpeaking();
  fetch(`${API_URL}/speech`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: text.slice(0, 600), language: LANG_CODE_MAP[code] ? code : 'en' }),
  })
    .then((res) => {
      if (!res.ok) throw new Error(`speech HTTP ${res.status}`);
      return res.blob();
    })
    .then((blob) => {
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      currentAudio = audio;
      audio.onended = () => {
        URL.revokeObjectURL(url);
        currentAudio = null;
        if (onEnd) onEnd();
      };
      return audio.play();
    })
    .catch((e) => {
      console.warn('Server speech unavailable, using the browser voice', e);
      speakWithBrowser(text, code, onEnd, onError);
    });
  return true;
}

function speakWithBrowser(
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
    window.speechSynthesis.cancel();

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
    // Chrome drops an utterance queued in the same tick as cancel(); wait a moment.
    setTimeout(() => window.speechSynthesis.speak(utterance), 60);
    return true;
  } catch (error) {
    console.warn('Failed to initiate TTS:', error);
    if (onError) onError(error);
    if (onEnd) onEnd();
    return false;
  }
}
