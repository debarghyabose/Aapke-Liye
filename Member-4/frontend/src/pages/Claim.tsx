// src/pages/Claim.tsx
import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Volume2,
  Mic,
  Square,
  RefreshCw,
  Camera,
  MapPin,
  Clock,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Download,
  Share2,
  Copy,
  ChevronRight,
  ChevronLeft,
  Edit2,
  Sparkles,
  ShieldCheck,
  Check,
} from 'lucide-react';
import { speakText } from '../utils/tts';
import {
  createClaim,
  uploadAudio,
  retryAudio,
  uploadPhoto,
  reverifyPhoto,
  updateFields,
  submitClaim,
  getClaimPdf,
  sendText,
  DEMO_MODE,
  errorText,
  draftDocument,
  saveTextFile,
} from '../api/client';
import { ClaimOut } from '../types/api';
import { getLocalizedSampleClaim } from '../mocks/sampleData';
import { VoiceWaveform } from '../components/VoiceWaveform';
import { queueOfflineItem } from '../utils/indexedDB';

const LANGUAGES = [
  { code: 'bn', label: 'বাংলা', sub: 'Bengali', sample: 'বাংলা ভাষায় কথা বলুন' },
  { code: 'hi', label: 'हिंदी', sub: 'Hindi', sample: 'हिंदी में बात करें' },
  { code: 'en', label: 'English', sub: 'Indian English', sample: 'Speak in English' },
  { code: 'mr', label: 'मराठी', sub: 'Marathi', sample: 'मराठीत बोला' },
  { code: 'te', label: 'తెలుగు', sub: 'Telugu', sample: 'తెలుగులో మాట్లాడండి' },
  { code: 'ta', label: 'தமிழ்', sub: 'Tamil', sample: 'தமிழில் பேசுங்கள்' },
];

function emptyClaim(): ClaimOut {
  const now = new Date().toISOString();
  return {
    id: '',
    language: 'en',
    disaster_type: null,
    transcript: null,
    fields: {},
    missing_fields: [],
    follow_up_questions: [],
    relief: null,
    proof_suggestions: [],
    status: 'Draft',
    photos: [],
    recordings: [],
    history: [],
    consent_text_version: 'v1',
    consent_given_at: now,
    submitted_at: null,
    created_at: now,
    updated_at: now,
  };
}

export const Claim: React.FC = () => {
  const { i18n, t } = useTranslation();
  const [step, setStep] = useState<number>(1);
  const [selectedLang, setSelectedLang] = useState<string>((i18n.language || 'bn').split('-')[0]);
  const [claim, setClaim] = useState<ClaimOut>(() => (DEMO_MODE ? getLocalizedSampleClaim(t) : emptyClaim()));
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Update claim when language changes if still using sample
  useEffect(() => {
    if (DEMO_MODE && step === 1) setClaim(getLocalizedSampleClaim(t));
  }, [i18n.language, t]);

  // Live mode never shows sample data: an error is shown instead.
  const fail = (e: unknown, demoFallback?: () => void) => {
    if (DEMO_MODE && demoFallback) demoFallback();
    else setErrorMsg(errorText(e));
  };
  const show = (value: string | null | undefined, demoValue: string) =>
    value || (DEMO_MODE ? demoValue : t('claim.notGiven', 'Not given yet'));

  // Audio Recording State
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [recordingSeconds, setRecordingSeconds] = useState<number>(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerIntervalRef = useRef<any>(null);

  // Photo State
  const [photoUploading, setPhotoUploading] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Field Edit State
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>('');

  // Follow-up answer state
  const [answeredQuestions, setAnsweredQuestions] = useState<Record<string, string>>({});

  // Copied state
  const [copied, setCopied] = useState<boolean>(false);

  // Step 1: Language selection speech
  const playLanguageName = (l: (typeof LANGUAGES)[0]) => {
    speakText(l.label, l.code);
  };

  const handleSelectLanguage = (code: string) => {
    setSelectedLang(code);
    i18n.changeLanguage(code);
  };

  const confirmLanguageAndStart = async () => {
    setLoading(true);
    setErrorMsg(null);
    i18n.changeLanguage(selectedLang);
    try {
      const created = await createClaim({
        language: selectedLang,
        disaster_type: 'flood',
        consent: true,
        consent_text_version: 'v1',
      });
      setClaim(created);
      setStep(2);
    } catch (e) {
      fail(e, () => {
        setClaim(getLocalizedSampleClaim(t));
        setStep(2);
      });
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Speech instructions & Recording
  const listenAudioInstructions = () => {
    const text = `${t('claim.step2Title', 'Speak What You Lost')}. ${t(
      'claim.step2Subtitle',
      'Press the button below and speak in your language. Tell us about your house damage, lost crops, dead cattle, or washed-away identity papers.'
    )}`;
    speakText(text, i18n.language);
  };

  const startRecording = async () => {
    setErrorMsg(null);
    audioChunksRef.current = [];
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await processAudioSubmission(audioBlob);
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start(250);
      setIsRecording(true);
      setRecordingSeconds(0);

      timerIntervalRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch {
      if (!DEMO_MODE) {
        setErrorMsg(t('claim.micUnavailable', 'Microphone not available. Allow microphone access, or type your answer below.'));
        return;
      }
      setIsRecording(true);
      setRecordingSeconds(0);
      timerIntervalRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    }
  };

  const stopRecording = () => {
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
    setIsRecording(false);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    } else if (DEMO_MODE) {
      setTimeout(() => {
        setClaim(getLocalizedSampleClaim(t));
      }, 600);
    }
  };

  const processAudioSubmission = async (audioBlob: Blob) => {
    setLoading(true);
    try {
      if (!navigator.onLine) {
        await queueOfflineItem({ type: 'audio', claimId: claim.id, blob: audioBlob });
        if (DEMO_MODE) setClaim(getLocalizedSampleClaim(t));
        else setErrorMsg(t('claim.savedOffline', 'No network. Your recording is saved on this phone and will be sent when the signal returns.'));
        return;
      }
      setErrorMsg(null);
      const updated = await uploadAudio(claim.id, audioBlob);
      setClaim(updated);
    } catch (e) {
      fail(e, () => setClaim(getLocalizedSampleClaim(t)));
    } finally {
      setLoading(false);
    }
  };

  const handleRetryAudio = async () => {
    setLoading(true);
    try {
      setErrorMsg(null);
      const updated = await retryAudio(claim.id);
      setClaim(updated);
    } catch (e) {
      fail(e, () => setClaim(getLocalizedSampleClaim(t)));
    } finally {
      setLoading(false);
    }
  };

  // Step 3: Question Handling
  const [typedAnswer, setTypedAnswer] = useState<string>('');

  const handleAnswerQuestion = async (field: string, answer: string) => {
    setAnsweredQuestions((prev) => ({ ...prev, [field]: answer }));
    if (DEMO_MODE || !answer.trim()) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      setClaim(await sendText(claim.id, answer.trim()));
      setTypedAnswer('');
    } catch (e) {
      fail(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSpeakQuestion = (q: string) => {
    speakText(q, i18n.language);
  };

  // Step 4: Photo Capture & Upload
  const triggerCamera = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handlePhotoCaptured = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setPhotoUploading(true);
    setErrorMsg(null);

    // Live mode never invents a location: without the phone's GPS, Member 3 uses the photo's
    // own EXIF location (or reports that none is available). Demo mode keeps a sample point.
    let lat: number | undefined = DEMO_MODE ? 22.6683 : undefined;
    let lon: number | undefined = DEMO_MODE ? 87.7214 : undefined;
    try {
      const pos: any = await new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 4000 });
      });
      lat = pos.coords.latitude;
      lon = pos.coords.longitude;
    } catch {
      // no phone location: see above
    }

    try {
      if (!navigator.onLine) {
        await queueOfflineItem({
          type: 'photo',
          claimId: claim.id,
          blob: file,
          metadata: { lat, lon, taken_at: new Date().toISOString(), name: file.name },
        });
        setClaim((prev) => ({
          ...prev,
          photos: [
            ...prev.photos,
            {
              id: Date.now(),
              sha256: 'offline-cached',
              lat: lat ?? null,
              lon: lon ?? null,
              taken_at: new Date().toISOString(),
              url: URL.createObjectURL(file),
              verification: {
                status: 'complete',
                damage_level: 'total',
                gemini_reason: t('mock.geminiDamageReason1', 'Mud and tin roof structure completely collapsed into standing floodwater.'),
                gps_valid: true,
                time_valid: true,
                exif_valid: true,
                duplicate: false,
              },
            },
          ],
        }));
        return;
      }

      const updated = await uploadPhoto(claim.id, file, lat, lon);
      setClaim(updated);
    } catch (e) {
      if (!DEMO_MODE) {
        setErrorMsg(errorText(e));
        return;
      }
      setClaim((prev) => ({
        ...prev,
        photos: [
          ...prev.photos,
          {
            id: Date.now(),
            sha256: 'mock-sha',
            lat: lat ?? null,
            lon: lon ?? null,
            taken_at: new Date().toISOString(),
            url: URL.createObjectURL(file),
            verification: {
              status: 'complete',
              damage_level: 'severe',
              gemini_reason: t('mock.geminiDamageReason2', 'Paddy crop submerged under standing flood water.'),
              gps_valid: true,
              time_valid: true,
              exif_valid: true,
              duplicate: false,
            },
          },
        ],
      }));
    } finally {
      setPhotoUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleReverify = async (photoId: number) => {
    try {
      const updated = await reverifyPhoto(claim.id, photoId);
      setClaim(updated);
    } catch (e) {
      fail(e);
    }
  };

  // Step 5: Save Field Edits & Final Submit
  const saveFieldEdit = async (fieldName: string) => {
    if (!editValue) return;
    try {
      const updated = await updateFields(claim.id, { [fieldName]: editValue });
      setClaim(updated);
      setErrorMsg(null);
    } catch (e) {
      if (!DEMO_MODE) {
        setErrorMsg(errorText(e));
        return;
      }
      setClaim({
        ...claim,
        fields: {
          ...claim.fields,
          [fieldName]: editValue,
        },
      });
    } finally {
      setEditingField(null);
      setEditValue('');
    }
  };

  const handleFinalSubmit = async () => {
    setLoading(true);
    try {
      setErrorMsg(null);
      const updated = await submitClaim(claim.id);
      setClaim(updated);
      setStep(6);
    } catch (e) {
      fail(e, () => setStep(6));
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPdf = async () => {
    try {
      await getClaimPdf(claim.id);
    } catch (e) {
      fail(e, () => window.open('/sample-claim.pdf', '_blank'));
    }
  };

  // Review-screen answers that go straight to the claim (and recalculate relief).
  const saveFields = async (fields: Record<string, any>) => {
    try {
      setErrorMsg(null);
      setClaim(await updateFields(claim.id, fields));
    } catch (e) {
      fail(e);
    }
  };
  const toggleVulnerability = (code: string) => {
    const now = new Set(claim.fields.vulnerability || []);
    if (now.has(code)) now.delete(code);
    else now.add(code);
    saveFields({ vulnerability: Array.from(now) });
  };
  const setCropInsured = (value: boolean) => saveFields({ crop_insured: value });

  const [draftBusy, setDraftBusy] = useState<string | null>(null);
  const handleDownloadDraft = async (docType: string) => {
    if (DEMO_MODE) return handleDownloadPdf();
    setDraftBusy(docType);
    setErrorMsg(null);
    try {
      const d = await draftDocument(claim.id, docType);
      saveTextFile(d.text, `${docType}-${claim.id}.txt`);
    } catch (e) {
      setErrorMsg(errorText(e));
    } finally {
      setDraftBusy(null);
    }
  };
  const hasCropLoss = (claim.fields.losses || []).some((l) => l.category === 'crop');

  const copyClaimId = () => {
    navigator.clipboard.writeText(claim.id);
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  };

  const handleShareWhatsApp = () => {
    const text = encodeURIComponent(
      `Aapke Liye relief claim ${claim.id} has been submitted. Track it here: ${window.location.origin}/track?id=${claim.id}`
    );
    window.open(`https://api.whatsapp.com/send?text=${text}`, '_blank');
  };

  // The AI's reply to the last voice note or typed answer: what it understood and what it
  // asks next. Shown right under the transcript so the person sees an answer immediately.
  const understood = [
    claim.fields.name,
    claim.fields.village,
    claim.fields.district,
    claim.fields.state,
    claim.fields.disaster_type,
    claim.fields.date_of_incident,
    claim.fields.phone,
  ].filter(Boolean) as string[];
  const nextQuestion = claim.follow_up_questions[0]?.question;
  const aiReply =
    DEMO_MODE || (!loading && !claim.transcript) ? null : (
      <div
        aria-live="polite"
        style={{
          marginTop: '16px',
          textAlign: 'left',
          backgroundColor: '#FFFFFF',
          padding: '18px 20px',
          borderRadius: '14px',
          border: '1.5px solid var(--primary)',
        }}
      >
        {loading ? (
          <strong>{t('claim.thinking', 'Understanding what you said…')}</strong>
        ) : (
          <>
            {understood.length > 0 && (
              <p style={{ margin: '0 0 8px 0', fontWeight: 700, color: 'var(--text)' }}>
                {t('claim.understood', 'Understood:')} {understood.join(' · ')}
                {claim.relief?.total
                  ? ` · ${t('claim.sdrfShort', 'SDRF relief')} ₹${claim.relief.total.toLocaleString('en-IN')}`
                  : ''}
                {claim.relief?.claimed_total
                  ? ` · ${t('claim.youReported', 'you reported')} ₹${claim.relief.claimed_total.toLocaleString('en-IN')}`
                  : ''}
              </p>
            )}
            {nextQuestion ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--primary)' }}>{nextQuestion}</span>
                <button
                  onClick={() => handleSpeakQuestion(nextQuestion)}
                  className="btn-outline-pill"
                  style={{ padding: '6px 14px', minHeight: '40px', fontWeight: 700 }}
                >
                  <Volume2 size={16} /> {t('common.listen', 'Listen')}
                </button>
              </div>
            ) : (
              <span style={{ fontWeight: 800, color: 'var(--leaf)' }}>
                {t('claim.allFilled', 'Everything needed is filled. You can add photos now.')}
              </span>
            )}
            <p style={{ margin: '8px 0 0 0', fontSize: '0.9rem', color: 'var(--text-muted)', fontWeight: 600 }}>
              {t('claim.answerHint', 'Answer by speaking again, or type below.')}
            </p>
          </>
        )}
      </div>
    );

  // Typed answers go through the same claim AI as voice (live mode only).
  const typeBox = DEMO_MODE ? null : (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        handleAnswerQuestion(claim.missing_fields[0] || 'text', typedAnswer);
      }}
      style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginTop: '20px' }}
    >
      <input
        value={typedAnswer}
        onChange={(e) => setTypedAnswer(e.target.value)}
        placeholder={t('claim.typeAnswer', 'Or type here, in your language…')}
        aria-label={t('claim.typeAnswer', 'Or type here, in your language…')}
        maxLength={2000}
        style={{
          flex: '1 1 240px',
          minHeight: '48px',
          padding: '10px 16px',
          borderRadius: '14px',
          border: '1.5px solid var(--border)',
          fontSize: '1rem',
        }}
      />
      <button
        type="submit"
        disabled={loading || !typedAnswer.trim()}
        className="btn-pill btn-outline-pill"
        style={{ minHeight: '48px', padding: '12px 22px', fontWeight: 800 }}
      >
        {loading ? t('common.loading', 'Sending…') : t('claim.send', 'Send')}
      </button>
    </form>
  );

  const selectedLangObj = LANGUAGES.find((l) => l.code === selectedLang) || LANGUAGES[0];

  return (
    <div
      style={{
        maxWidth: '920px',
        margin: '20px auto 60px auto',
        padding: '0 clamp(12px, 3.5vw, 24px)',
      }}
    >
      {/* Progress Bar "Step x of 6" */}
      <div
        style={{
          marginBottom: '20px',
          backgroundColor: '#FFFFFF',
          borderRadius: '16px',
          border: '1.5px solid var(--border)',
          padding: '14px 20px',
          boxShadow: '0 2px 10px rgba(26, 75, 117, 0.04)',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '10px',
          }}
        >
          <span style={{ fontWeight: 700, color: 'var(--text)', fontSize: '1.1rem' }}>
            <span
              style={{
                backgroundColor: 'var(--accent)',
                color: '#FFFFFF',
                padding: '4px 12px',
                borderRadius: '999px',
                fontSize: '0.82rem',
                marginRight: '10px',
                fontWeight: 700,
              }}
            >
              {t('howItWorks.stepOf', { num: step, defaultValue: `Step ${step} of 6` })}
            </span>
            {step === 1 && t('claim.step1Name', 'Select Language')}
            {step === 2 && t('claim.step2Name', 'Speak Your Losses')}
            {step === 3 && t('claim.step3Name', 'Answer Questions')}
            {step === 4 && t('claim.step4Name', 'Damage Photos')}
            {step === 5 && t('claim.step5Name', 'Review & Schemes')}
            {step === 6 && t('claim.step6Name', 'Submitted & Documents')}
          </span>
          <span style={{ fontSize: '0.88rem', color: 'var(--leaf)', fontWeight: 700 }}>
            {Math.round((step / 6) * 100)}% {t('howItWorks.complete', 'Complete! ✓')}
          </span>
        </div>

        {/* Progress bar visual */}
        <div
          style={{
            height: '8px',
            backgroundColor: 'var(--bg-alt)',
            borderRadius: '999px',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              height: '100%',
              width: `${(step / 6) * 100}%`,
              backgroundColor: 'var(--accent)',
              transition: 'width 0.3s ease',
              borderRadius: '999px',
            }}
          />
        </div>
      </div>

      {errorMsg && (
        <div
          role="alert"
          style={{
            backgroundColor: '#FDEAE8',
            color: 'var(--accent)',
            border: '1px solid #F5C2BE',
            padding: '14px 20px',
            borderRadius: '14px',
            marginBottom: '24px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
          }}
        >
          <AlertTriangle size={20} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* ================= STEP 1: LANGUAGE ================= */}
      {step === 1 && (
        <div className="card-soft" style={{ textAlign: 'center', padding: 'clamp(24px, 4vw, 40px) clamp(16px, 3vw, 28px)' }}>
          <h2 style={{ fontSize: 'clamp(1.7rem, 2.8vw, 2.2rem)', marginBottom: '6px', color: 'var(--text)', fontWeight: 800 }}>
            {t('claim.step1Title', 'Choose Your Language')}
          </h2>
          <p style={{ color: 'var(--text-muted)', marginBottom: '22px', fontSize: 'clamp(0.96rem, 1.1vw, 1.05rem)', fontWeight: 600 }}>
            {t(
              'claim.step1Subtitle',
              'Tap a language to listen. You will be able to speak freely in your mother tongue without typing.'
            )}
          </p>

          <div
            className="claim-lang-grid"
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: '12px',
              marginBottom: '24px',
            }}
          >
            {LANGUAGES.map((lang) => {
              const isSelected = selectedLang === lang.code;
              return (
                <div
                  key={lang.code}
                  onClick={() => handleSelectLanguage(lang.code)}
                  style={{
                    backgroundColor: isSelected ? 'rgba(26, 75, 117, 0.08)' : '#FFFFFF',
                    border: isSelected ? '2.5px solid var(--primary)' : '1.5px solid var(--border)',
                    borderRadius: '14px',
                    padding: '14px 16px',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '4px',
                    minHeight: '84px',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      width: '100%',
                    }}
                  >
                    <span
                      style={{
                        fontSize: '1.45rem',
                        fontWeight: 800,
                        color: isSelected ? 'var(--primary)' : 'var(--text)',
                      }}
                    >
                      {lang.label}
                    </span>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        playLanguageName(lang);
                      }}
                      className="btn-outline-pill"
                      style={{
                        padding: '6px 10px',
                        minHeight: '40px',
                        minWidth: '40px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                      aria-label={`${t('claim.btnPlayAudio', 'Listen')} ${lang.sub}`}
                    >
                      <Volume2 size={18} style={{ color: 'var(--accent)' }} />
                    </button>
                  </div>
                  <div style={{ fontSize: '0.88rem', color: 'var(--leaf)', fontWeight: 800 }}>
                    {lang.sub}
                  </div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontStyle: 'italic', fontWeight: 600 }}>
                    "{lang.sample}"
                  </div>
                </div>
              );
            })}
          </div>

          <button
            onClick={confirmLanguageAndStart}
            disabled={loading}
            className="btn-pill btn-orange-pill"
            style={{ width: '100%', maxWidth: '420px', minHeight: '48px', fontSize: '1.08rem', fontWeight: 800 }}
          >
            <span>
              {t('claim.btnConfirmLanguage', {
                lang: selectedLangObj.label,
                defaultValue: `Start In ${selectedLangObj.label} →`,
              })}
            </span>
            <ChevronRight size={20} />
          </button>
        </div>
      )}

      {/* ================= STEP 2: SPEAK ================= */}
      {step === 2 && (
        <div className="card-soft" style={{ textAlign: 'center', padding: 'clamp(24px, 4vw, 40px) clamp(16px, 3vw, 28px)' }}>
          <h2 style={{ fontSize: 'clamp(1.7rem, 2.8vw, 2.2rem)', marginBottom: '8px', color: 'var(--text)', fontWeight: 800 }}>
            {t('claim.step2Title', 'Speak What You Lost')}
          </h2>
          <p style={{ color: 'var(--text-muted)', maxWidth: '620px', margin: '0 auto 20px auto', fontSize: 'clamp(0.96rem, 1.1vw, 1.05rem)', fontWeight: 600 }}>
            {t(
              'claim.step2Subtitle',
              'Press the button below and speak in your language. Tell us about your house damage, lost crops, dead cattle, or washed-away identity papers.'
            )}
          </p>

          <button
            onClick={listenAudioInstructions}
            className="btn-outline-pill"
            style={{
              padding: '10px 22px',
              minHeight: '48px',
              fontSize: '0.96rem',
              fontWeight: 800,
              marginBottom: '24px',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <Volume2 size={18} style={{ color: 'var(--accent)' }} />
            <span>🔊 {t('claim.listenInstructions', 'Listen to spoken instructions')}</span>
          </button>

          {/* Huge Round ORANGE Record Button */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '16px',
            }}
          >
            <button
              onClick={isRecording ? stopRecording : startRecording}
              aria-label={
                isRecording
                  ? t('claim.tapToStop', 'Tap to Stop Recording')
                  : t('claim.tapToRecord', 'Tap to Speak (Voice Claim)')
              }
              style={{
                width: '128px',
                height: '128px',
                borderRadius: '50%',
                backgroundColor: 'var(--accent)',
                color: '#FFFFFF',
                border: isRecording ? '8px solid rgba(244, 96, 54, 0.4)' : '8px solid rgba(244, 96, 54, 0.2)',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                boxShadow: '0 8px 30px rgba(244, 96, 54, 0.38)',
                transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
              }}
            >
              {isRecording ? <Square size={42} /> : <Mic size={46} />}
              <span style={{ fontSize: '0.85rem', fontWeight: 800, marginTop: '6px', letterSpacing: '0.5px' }}>
                {isRecording ? t('claim.tapToStop', 'STOP') : t('claim.tapToRecord', 'TAP TO SPEAK')}
              </span>
            </button>

            {/* Live Timer */}
            {isRecording && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  color: 'var(--accent)',
                  fontWeight: 800,
                  fontSize: '1.25rem',
                }}
              >
                <div
                  style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--accent)',
                  }}
                />
                <span>
                  {t('claim.recordingActive', 'Recording')}:{' '}
                  {Math.floor(recordingSeconds / 60)
                    .toString()
                    .padStart(2, '0')}
                  :{(recordingSeconds % 60).toString().padStart(2, '0')}
                </span>
              </div>
            )}

            <VoiceWaveform isRecording={isRecording} />
          </div>

          {/* Transcript / Result */}
          {claim.transcript && (
            <div
              style={{
                marginTop: '24px',
                textAlign: 'left',
                backgroundColor: 'var(--bg)',
                padding: '18px 20px',
                borderRadius: '14px',
                border: '1.5px solid var(--border)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <Sparkles size={18} style={{ color: 'var(--accent)' }} />
                <strong style={{ color: 'var(--text)', fontSize: '1rem', fontWeight: 800 }}>
                  {t('claim.transcriptHeader', 'What Gemini Heard (Transcribed):')}
                </strong>
              </div>
              <p style={{ margin: 0, fontStyle: 'italic', color: 'var(--text-muted)', fontSize: '0.98rem', fontWeight: 600 }}>
                "{claim.transcript}"
              </p>
            </div>
          )}

          {aiReply}

          {typeBox}

          <div
            className="claim-nav-buttons"
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              gap: '14px',
              marginTop: '32px',
            }}
          >
            <button
              onClick={() => setStep(1)}
              className="btn-pill btn-outline-pill"
              style={{ minHeight: '48px', padding: '12px 24px', fontSize: '1rem', fontWeight: 800 }}
            >
              <ChevronLeft size={18} />
              <span>{t('claim.back', 'Back')}</span>
            </button>

            <div className="claim-nav-right" style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={
                  DEMO_MODE || claim.recordings.some((r) => r.status === 'pending') ? handleRetryAudio : startRecording
                }
                title={t('claim.reRecord', 'Record Again')}
                className="btn-pill btn-outline-pill"
                style={{ minHeight: '48px', padding: '12px 20px', fontSize: '0.98rem', fontWeight: 800 }}
              >
                <RefreshCw size={16} />
                <span>{t('claim.reRecord', 'Record Again')}</span>
              </button>

              <button
                onClick={() => setStep(3)}
                className="btn-pill btn-orange-pill"
                style={{ minHeight: '48px', padding: '12px 24px', fontSize: '1rem', fontWeight: 800 }}
              >
                <span>{t('claim.nextQuestions', 'Next: Answer Question')}</span>
                <ChevronRight size={18} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ================= STEP 3: FOLLOW-UP QUESTIONS ================= */}
      {step === 3 && (
        <div className="card-soft" style={{ padding: 'clamp(24px, 4vw, 40px) clamp(16px, 3vw, 32px)' }}>
          <h2 style={{ fontSize: 'clamp(1.7rem, 2.8vw, 2.2rem)', marginBottom: '8px', color: 'var(--text)', fontWeight: 800 }}>
            {t('claim.step3Title', 'Just One Clarification')}
          </h2>
          <p style={{ color: 'var(--text-muted)', marginBottom: '24px', fontSize: 'clamp(0.96rem, 1.1vw, 1.05rem)', fontWeight: 600 }}>
            {t(
              'claim.step3Subtitle',
              'Gemini identified all your losses. To ensure direct transfer to your bank, please answer this quick question:'
            )}
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '28px' }}>
            {claim.follow_up_questions.map((q, idx) => (
              <div
                key={idx}
                style={{
                  padding: '20px',
                  backgroundColor: '#FFFFFF',
                  borderRadius: '16px',
                  border: '1.5px solid var(--border)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px', marginBottom: '14px' }}>
                  <span style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text)' }}>
                    {q.question}
                  </span>
                  <button
                    onClick={() => handleSpeakQuestion(q.question)}
                    className="btn-outline-pill"
                    style={{ padding: '8px 16px', minHeight: '44px', fontSize: '0.92rem', fontWeight: 700 }}
                    aria-label={t('common.listen', 'Listen')}
                  >
                    <Volume2 size={16} style={{ color: 'var(--accent)' }} />
                    <span>{t('common.listen', 'Listen')}</span>
                  </button>
                </div>

                {/* Suggested answers pills */}
                {q.suggested_answers && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                    {q.suggested_answers.map((ans, aIdx) => {
                      const isChosen = answeredQuestions[q.field] === ans;
                      return (
                        <button
                          key={aIdx}
                          onClick={() => handleAnswerQuestion(q.field, ans)}
                          style={{
                            padding: '12px 22px',
                            minHeight: '48px',
                            borderRadius: '999px',
                            border: isChosen ? '2.5px solid var(--primary)' : '1.5px solid var(--border)',
                            backgroundColor: isChosen ? 'rgba(26, 75, 117, 0.1)' : 'var(--bg-alt)',
                            color: isChosen ? 'var(--primary)' : 'var(--text)',
                            fontWeight: isChosen ? 800 : 700,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            fontSize: '1rem',
                          }}
                        >
                          {isChosen && <Check size={18} />}
                          <span>{ans}</span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}
            {!DEMO_MODE && claim.follow_up_questions.length === 0 && (
              <p style={{ fontWeight: 700, color: 'var(--leaf)' }}>
                {t('claim.nothingMissing', 'Nothing more is needed. You can add photos now.')}
              </p>
            )}
            {typeBox}
          </div>

          <div className="claim-nav-buttons" style={{ display: 'flex', justifyContent: 'space-between', gap: '14px' }}>
            <button onClick={() => setStep(2)} className="btn-pill btn-outline-pill" style={{ minHeight: '48px', padding: '12px 24px', fontSize: '1rem', fontWeight: 800 }}>
              <ChevronLeft size={18} />
              <span>{t('claim.back', 'Back')}</span>
            </button>
            <button onClick={() => setStep(4)} className="btn-pill btn-orange-pill" style={{ minHeight: '48px', padding: '12px 24px', fontSize: '1rem', fontWeight: 800 }}>
              <span>{t('claim.nextPhotos', 'Next: Add Damage Photos')}</span>
              <ChevronRight size={18} />
            </button>
          </div>
        </div>
      )}

      {/* ================= STEP 4: PHOTOS ================= */}
      {step === 4 && (
        <div className="card-soft" style={{ padding: 'clamp(24px, 4vw, 40px) clamp(16px, 3vw, 32px)' }}>
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '16px',
              marginBottom: '24px',
            }}
          >
            <div>
              <h2 style={{ fontSize: 'clamp(1.7rem, 2.8vw, 2.2rem)', margin: 0, color: 'var(--text)', fontWeight: 800 }}>
                {t('claim.step4Title', 'Add Damage Photos')}
              </h2>
              <p style={{ color: 'var(--text-muted)', margin: '6px 0 0 0', fontSize: 'clamp(0.96rem, 1.1vw, 1.05rem)', fontWeight: 600 }}>
                {t(
                  'claim.step4Subtitle',
                  'Photos are automatically tagged with GPS location and timestamp for official SDRF clearance.'
                )}
              </p>
            </div>

            <input
              type="file"
              ref={fileInputRef}
              accept="image/*"
              capture="environment"
              onChange={handlePhotoCaptured}
              style={{ display: 'none' }}
            />

            <button
              onClick={triggerCamera}
              disabled={photoUploading}
              className="btn-pill btn-orange-pill"
              style={{ gap: '8px', minHeight: '48px', padding: '12px 26px', fontSize: '1.02rem', fontWeight: 800 }}
            >
              <Camera size={20} />
              <span>
                {photoUploading
                  ? t('claim.uploadingVerifying', 'Uploading & Verifying…')
                  : t('claim.takePhoto', 'Take or Upload Photo')}
              </span>
            </button>
          </div>

          {/* Photo list */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '18px', marginBottom: '28px' }}>
            {claim.photos.map((photo) => (
              <div
                key={photo.id}
                className="claim-photo-grid"
                style={{
                  border: '1.5px solid var(--border)',
                  borderRadius: '16px',
                  padding: '18px',
                  backgroundColor: '#FFFFFF',
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                  gap: '18px',
                }}
              >
                <div>
                  <div
                    style={{
                      height: '170px',
                      backgroundColor: 'var(--bg-alt)',
                      borderRadius: '12px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      overflow: 'hidden',
                      position: 'relative',
                    }}
                  >
                    {photo.url ? (
                      <img
                        src={photo.url}
                        alt={t('claim.photoAlt', 'Damage evidence')}
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      />
                    ) : (
                      <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '10px' }}>
                        <Camera size={36} style={{ color: 'var(--primary)', marginBottom: '6px' }} />
                        <div style={{ fontSize: '0.88rem', fontWeight: 700 }}>
                          {t('claim.photoEvidenceLabel', { id: photo.id, defaultValue: `Damage Evidence Photo #${photo.id}` })}
                        </div>
                      </div>
                    )}
                    <span
                      style={{
                        position: 'absolute',
                        top: '8px',
                        right: '8px',
                        backgroundColor:
                          photo.verification.damage_level === 'total' || photo.verification.damage_level === 'severe'
                            ? 'var(--accent)'
                            : 'var(--leaf)',
                        color: '#FFF',
                        padding: '4px 14px',
                        borderRadius: '999px',
                        fontSize: '0.82rem',
                        fontWeight: 800,
                        textTransform: 'uppercase',
                      }}
                    >
                      {photo.verification.damage_level === 'total'
                        ? t('claim.totalDamage', 'Total Damage')
                        : photo.verification.damage_level === 'severe'
                        ? t('claim.severeDamage', 'Severe Damage')
                        : t('claim.evaluatedDamage', 'Evaluated Damage')}
                    </span>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '12px' }}>
                  <div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          backgroundColor: 'rgba(42, 123, 76, 0.12)',
                          color: 'var(--leaf)',
                          padding: '5px 12px',
                          borderRadius: '999px',
                          fontSize: '0.84rem',
                          fontWeight: 800,
                        }}
                      >
                        <MapPin size={14} />{' '}
                        {t('claim.gpsVerified', {
                          lat: photo.lat?.toFixed(4),
                          lon: photo.lon?.toFixed(4),
                          defaultValue: `GPS Verified (${photo.lat?.toFixed(4)}, ${photo.lon?.toFixed(4)})`,
                        })}
                      </span>

                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          backgroundColor: 'rgba(26, 75, 117, 0.1)',
                          color: 'var(--primary)',
                          padding: '5px 12px',
                          borderRadius: '999px',
                          fontSize: '0.84rem',
                          fontWeight: 800,
                        }}
                      >
                        <Clock size={14} /> {t('claim.timeVerified', 'Time Verified')}
                      </span>

                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          backgroundColor: 'rgba(42, 123, 76, 0.12)',
                          color: 'var(--leaf)',
                          padding: '5px 12px',
                          borderRadius: '999px',
                          fontSize: '0.84rem',
                          fontWeight: 800,
                        }}
                      >
                        <ShieldCheck size={14} /> {t('claim.exifOriginal', 'EXIF Original')}
                      </span>
                    </div>

                    <div style={{ fontSize: '0.98rem', color: 'var(--text)', lineHeight: 1.55, fontWeight: 600 }}>
                      <strong>{t('claim.geminiAssessment', 'Gemini Assessment:')}</strong>{' '}
                      {photo.verification.gemini_reason}
                    </div>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <button
                      onClick={() => handleReverify(photo.id)}
                      className="btn-outline-pill"
                      style={{ padding: '8px 18px', minHeight: '44px', fontSize: '0.9rem', fontWeight: 800 }}
                    >
                      <RefreshCw size={15} /> {t('claim.reverify', 'Reverify Photo')}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="claim-nav-buttons" style={{ display: 'flex', justifyContent: 'space-between', gap: '14px' }}>
            <button onClick={() => setStep(3)} className="btn-pill btn-outline-pill" style={{ minHeight: '48px', padding: '12px 24px', fontSize: '1rem', fontWeight: 800 }}>
              <ChevronLeft size={18} />
              <span>{t('claim.back', 'Back')}</span>
            </button>
            <button onClick={() => setStep(5)} className="btn-pill btn-orange-pill" style={{ minHeight: '48px', padding: '12px 24px', fontSize: '1rem', fontWeight: 800 }}>
              <span>{t('claim.nextReview', 'Next: Review & Relief Amount')}</span>
              <ChevronRight size={18} />
            </button>
          </div>
        </div>
      )}

      {/* ================= STEP 5: REVIEW & SCHEMES ================= */}
      {step === 5 && (
        <div className="card-soft" style={{ padding: 'clamp(24px, 4vw, 40px) clamp(16px, 3vw, 32px)' }}>
          <h2 style={{ fontSize: 'clamp(1.7rem, 2.8vw, 2.2rem)', marginBottom: '8px', color: 'var(--text)', fontWeight: 800 }}>
            {t('claim.step5Title', 'Review Your Extracted Claim Details')}
          </h2>
          <p style={{ color: 'var(--text-muted)', marginBottom: '24px', fontSize: 'clamp(0.96rem, 1.1vw, 1.05rem)', fontWeight: 600 }}>
            {t(
              'claim.step5Subtitle',
              'Check the extracted information below. Tap "Edit" if anything needs to be changed.'
            )}
          </p>

          {/* SDRF Relief Estimated Amount Banner (Royal River Blue) */}
          <div
            className="sdrf-banner"
            style={{
              backgroundColor: 'var(--primary)',
              color: '#FFFFFF',
              borderRadius: '20px',
              padding: '24px 30px',
              marginBottom: '28px',
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '20px',
              boxShadow: '0 8px 24px rgba(26, 75, 117, 0.25)',
            }}
          >
            <div>
              <span style={{ fontSize: '0.88rem', color: '#D2E3EE', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 700 }}>
                {t('claim.sdrfBannerTitle', 'Estimated Government Compensation (SDRF Norms)')}
              </span>
              <div className="sdrf-banner-amount" style={{ fontSize: '2.6rem', fontWeight: 800 }}>
                ₹{claim.relief?.total ? claim.relief.total.toLocaleString('en-IN') : DEMO_MODE ? '2,06,300' : '0'}
              </div>
              {!DEMO_MODE && (
                <div style={{ fontSize: '0.88rem', color: '#D2E3EE', marginTop: '4px', fontWeight: 600, maxWidth: '560px' }}>
                  {claim.relief?.claimed_total
                    ? `${t('claim.youReportedLoss', 'Loss you reported')}: ₹${claim.relief.claimed_total.toLocaleString('en-IN')}. `
                    : ''}
                  {t(
                    'claim.sdrfFixedNote',
                    'SDRF relief is a fixed government amount per item (e.g. ₹1,20,000 for a fully destroyed house), not the full value of the loss. Insurance and PMAY-G can add more.'
                  )}
                </div>
              )}
              <div style={{ fontSize: '0.92rem', color: '#FFE082', marginTop: '4px', fontWeight: 700 }}>
                {t('claim.matchedSchemes', {
                  schemes: claim.relief?.matched_schemes.join(' · ') || (DEMO_MODE ? 'SDRF, PMFBY, PMAY-G' : 'SDRF'),
                  defaultValue: `Matched Schemes: ${claim.relief?.matched_schemes.join(' · ') || (DEMO_MODE ? 'SDRF, PMFBY, PMAY-G' : 'SDRF')}`,
                })}
              </div>
            </div>

            <div style={{ backgroundColor: 'rgba(255,255,255,0.15)', padding: '14px 22px', borderRadius: '14px' }}>
              <div style={{ fontSize: '0.85rem', color: '#E1EBF2', fontWeight: 600 }}>{t('claim.dbtTitle', 'Direct Benefit Transfer (DBT)')}</div>
              <div style={{ fontWeight: 800, color: '#A3E635', fontSize: '1rem' }}>{t('claim.dbtStatus', 'Ready for District Sanction')}</div>
            </div>
          </div>

          {/* Breakdown cards */}
          <div style={{ marginBottom: '28px' }}>
            <h3 style={{ fontSize: '1.3rem', marginBottom: '14px', color: 'var(--text)', fontWeight: 800 }}>
              {t('claim.lossBreakdown', 'Loss Breakdown')}
            </h3>
            <div className="claim-breakdown-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
              {claim.relief?.breakdown.map((item, idx) => (
                <div
                  key={idx}
                  style={{
                    backgroundColor: '#FFFFFF',
                    borderRadius: '14px',
                    padding: '16px 18px',
                    border: '1.5px solid var(--border)',
                  }}
                >
                  <div style={{ fontWeight: 800, color: 'var(--text)', fontSize: '1.05rem' }}>{item.item}</div>
                  <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                    {t('claim.qtyRate', {
                      qty: item.quantity,
                      rate: item.rate.toLocaleString('en-IN'),
                      defaultValue: `Qty: ${item.quantity} · Rate: ₹${item.rate.toLocaleString('en-IN')}`,
                    })}
                  </div>
                  <div style={{ fontWeight: 800, color: 'var(--accent)', marginTop: '4px', fontSize: '1.18rem' }}>
                    ₹{item.amount.toLocaleString('en-IN')}
                  </div>
                  {item.description && (
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '4px', fontWeight: 600 }}>
                      {item.description}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Extracted Details Cards with "Correct / Edit" */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '28px' }}>
            <h3 style={{ fontSize: '1.3rem', margin: '0 0 4px 0', color: 'var(--text)', fontWeight: 800 }}>
              {t('claim.applicantDetails', 'Applicant Details')}
            </h3>

            {[
              { label: t('claim.claimantName', 'Claimant Name'), key: 'name', value: show(claim.fields.name, 'Sunita Mondal') },
              { label: t('claim.mobileNumber', 'Mobile Number'), key: 'phone', value: show(claim.fields.phone, '+91 98301 23456') },
              { label: t('claim.villageBlock', 'Village / Block'), key: 'village', value: show(claim.fields.village, 'Ghatal Block-II') },
              {
                label: t('claim.districtState', 'District / State'),
                key: 'district',
                value: `${show(claim.fields.district, 'Paschim Medinipur')}, ${show(claim.fields.state, 'West Bengal')}`,
              },
              { label: t('claim.disasterType', 'Disaster Type'), key: 'disaster_type', value: DEMO_MODE ? t('claim.floodVal', 'Flood') : show(claim.fields.disaster_type, '') },
              { label: t('claim.dateOfFlood', 'Date of Flood'), key: 'date_of_incident', value: show(claim.fields.date_of_incident, '2026-10-14') },
            ].map((f) => (
              <div
                key={f.key}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '8px',
                  padding: '14px 18px',
                  backgroundColor: '#FFFFFF',
                  border: '1.5px solid var(--border)',
                  borderRadius: '14px',
                }}
              >
                <div>
                  <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)', display: 'block', fontWeight: 600 }}>{f.label}</span>
                  {editingField === f.key ? (
                    <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
                      <input
                        type="text"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        style={{ padding: '8px 14px', borderRadius: '999px', border: '1px solid var(--border)', fontSize: '1rem' }}
                      />
                      <button
                        onClick={() => saveFieldEdit(f.key)}
                        className="btn-pill btn-orange-pill"
                        style={{ minHeight: '44px', padding: '8px 18px', fontSize: '0.92rem', fontWeight: 800 }}
                      >
                        {t('claim.saveBtn', 'Save')}
                      </button>
                    </div>
                  ) : (
                    <span style={{ fontWeight: 800, fontSize: '1.08rem', color: 'var(--text)' }}>{f.value}</span>
                  )}
                </div>

                {editingField !== f.key && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ color: 'var(--leaf)', fontSize: '0.92rem', fontWeight: 800 }}>
                      {t('claim.correctBadge', 'Correct ✓')}
                    </span>
                    <button
                      onClick={() => {
                        setEditingField(f.key);
                        setEditValue(f.value);
                      }}
                      className="btn-outline-pill"
                      style={{ padding: '8px 16px', minHeight: '44px', fontSize: '0.9rem', fontWeight: 700 }}
                    >
                      <Edit2 size={14} /> {t('claim.editBtn', 'Edit')}
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Household needs + crop insurance (live mode) */}
          {!DEMO_MODE && (
            <div
              style={{
                backgroundColor: '#FFFFFF',
                border: '1.5px solid var(--border)',
                borderRadius: '16px',
                padding: '20px',
                marginBottom: '28px',
              }}
            >
              <h4 style={{ margin: '0 0 6px 0', fontSize: '1.12rem', fontWeight: 800 }}>
                {t('claim.vulnerableTitle', 'Does anyone in your family need help first?')}
              </h4>
              <p style={{ margin: '0 0 12px 0', fontSize: '0.92rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                {t('claim.vulnerableHint', 'Officials visit these families first. Tap all that apply.')}
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                {[
                  ['elderly', t('claim.vElderly', 'Elderly person (60+)')],
                  ['disabled', t('claim.vDisabled', 'Person with a disability')],
                  ['single_mother', t('claim.vSingleMother', 'Single mother / woman-headed home')],
                  ['child_under_5', t('claim.vChild', 'Child under 5')],
                ].map(([code, text]) => {
                  const on = (claim.fields.vulnerability || []).includes(code);
                  return (
                    <button
                      key={code}
                      aria-pressed={on}
                      onClick={() => toggleVulnerability(code)}
                      style={{
                        padding: '10px 18px',
                        minHeight: '48px',
                        borderRadius: '999px',
                        border: on ? '2.5px solid var(--primary)' : '1.5px solid var(--border)',
                        backgroundColor: on ? 'rgba(26, 75, 117, 0.1)' : 'var(--bg-alt)',
                        fontWeight: on ? 800 : 700,
                        cursor: 'pointer',
                      }}
                    >
                      {on ? '✓ ' : ''}
                      {text}
                    </button>
                  );
                })}
              </div>

              {(claim.fields.losses || []).some((l) => l.category === 'crop') && (
                <div style={{ marginTop: '18px' }}>
                  <h4 style={{ margin: '0 0 10px 0', fontSize: '1.05rem', fontWeight: 800 }}>
                    {t('claim.cropInsuredQ', 'Was your crop insured under PMFBY (crop insurance)?')}
                  </h4>
                  <div style={{ display: 'flex', gap: '10px' }}>
                    {[
                      [true, t('common.yes', 'Yes')],
                      [false, t('common.no', 'No / not sure')],
                    ].map(([val, text]) => (
                      <button
                        key={String(val)}
                        aria-pressed={claim.fields.crop_insured === val}
                        onClick={() => setCropInsured(val as boolean)}
                        className="btn-outline-pill"
                        style={{
                          minHeight: '48px',
                          padding: '10px 22px',
                          fontWeight: 800,
                          border: claim.fields.crop_insured === val ? '2.5px solid var(--primary)' : undefined,
                        }}
                      >
                        {text as string}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {(claim.relief?.may_also_qualify || []).length > 0 && (
                <div style={{ marginTop: '18px' }}>
                  <h4 style={{ margin: '0 0 8px 0', fontSize: '1.05rem', fontWeight: 800 }}>
                    {t('claim.alsoQualify', 'You may also qualify for (separate applications):')}
                  </h4>
                  <ul style={{ margin: 0, paddingLeft: '20px', fontWeight: 600 }}>
                    {(claim.relief?.may_also_qualify || []).map((s) => (
                      <li key={s.scheme_code} style={{ marginBottom: '6px' }}>
                        <strong>{s.scheme_name || s.scheme_code}</strong>
                        {s.estimated_amount ? ` · about ₹${s.estimated_amount.toLocaleString('en-IN')}` : ''}
                        {s.conditions?.length ? (
                          <div style={{ fontSize: '0.86rem', color: 'var(--text-muted)' }}>{s.conditions.join(' · ')}</div>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Proof Substitution Suggestions */}
          {claim.proof_suggestions && claim.proof_suggestions.length > 0 && (
            <div
              style={{
                backgroundColor: 'rgba(42, 123, 76, 0.08)',
                border: '1.5px solid var(--border)',
                borderRadius: '16px',
                padding: '20px',
                marginBottom: '28px',
              }}
            >
              <h4 style={{ margin: '0 0 10px 0', color: 'var(--leaf)', fontSize: '1.12rem', fontWeight: 800 }}>
                {t('claim.acceptedProof', 'Accepted Proof Substitutions for Lost Papers:')}
              </h4>
              <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.98rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                {claim.proof_suggestions.map((p, pIdx) => (
                  <li key={pIdx} style={{ marginBottom: '8px' }}>
                    <strong style={{ color: 'var(--text)', fontWeight: 800 }}>{p.document}:</strong> {p.suggestions.join(' · ')}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="claim-nav-buttons" style={{ display: 'flex', justifyContent: 'space-between', gap: '14px' }}>
            <button onClick={() => setStep(4)} className="btn-pill btn-outline-pill" style={{ minHeight: '48px', padding: '12px 24px', fontSize: '1rem', fontWeight: 800 }}>
              <ChevronLeft size={18} />
              <span>{t('claim.back', 'Back')}</span>
            </button>
            <button onClick={handleFinalSubmit} className="btn-pill btn-orange-pill" style={{ minHeight: '48px', padding: '12px 24px', fontSize: '1.05rem', fontWeight: 800 }}>
              <span>{t('claim.submitClaim', 'Submit Official Claim Package')}</span>
              <ChevronRight size={18} />
            </button>
          </div>
        </div>
      )}

      {/* ================= STEP 6: DONE ================= */}
      {step === 6 && (
        <div className="card-soft" style={{ textAlign: 'center', padding: 'clamp(28px, 4vw, 48px) clamp(16px, 3vw, 36px)' }}>
          <div
            style={{
              width: '74px',
              height: '74px',
              borderRadius: '50%',
              backgroundColor: 'rgba(42, 123, 76, 0.14)',
              color: 'var(--leaf)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px auto',
            }}
          >
            <CheckCircle2 size={46} />
          </div>

          <h2 style={{ fontSize: 'clamp(1.85rem, 3vw, 2.3rem)', marginBottom: '8px', color: 'var(--text)', fontWeight: 800 }}>
            {t('claim.step6Title', 'Claim Submitted Successfully!')}
          </h2>
          <p style={{ color: 'var(--text-muted)', marginBottom: '26px', fontSize: 'clamp(1rem, 1.2vw, 1.1rem)', fontWeight: 600 }}>
            {t(
              'claim.step6Subtitle',
              'Your official disaster relief application has been cryptographically signed and submitted to the Block Development Office (BDO).'
            )}
          </p>

          {/* Claim ID Box */}
          <div
            style={{
              backgroundColor: 'var(--bg-alt)',
              border: '2px dashed var(--accent)',
              borderRadius: '18px',
              padding: '20px',
              maxWidth: '520px',
              margin: '0 auto 30px auto',
            }}
          >
            <span style={{ fontSize: '0.88rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 700 }}>
              {t('claim.claimRefLabel', 'Your Official Claim Reference Number:')}
            </span>
            <div
              style={{
                fontSize: 'clamp(1.6rem, 2.5vw, 2.1rem)',
                fontWeight: 800,
                color: 'var(--primary)',
                letterSpacing: '0.5px',
                margin: '8px 0',
              }}
            >
              {claim.id}
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '10px', marginTop: '16px' }}>
              <button
                onClick={copyClaimId}
                className="btn-pill btn-outline-pill"
                style={{ padding: '10px 22px', minHeight: '48px', fontSize: '0.96rem', fontWeight: 800, flex: 1, minWidth: '130px' }}
              >
                <Copy size={16} />
                <span>{copied ? t('claim.copied', 'Copied ✓') : t('claim.copyId', 'Copy ID')}</span>
              </button>

              <button
                onClick={handleShareWhatsApp}
                className="btn-pill"
                style={{
                  backgroundColor: '#25D366',
                  color: '#FFFFFF',
                  padding: '10px 22px',
                  minHeight: '48px',
                  fontSize: '0.96rem',
                  fontWeight: 800,
                  flex: 1,
                  minWidth: '160px',
                }}
              >
                <Share2 size={16} />
                <span>{t('claim.shareWhatsApp', 'WhatsApp to Family')}</span>
              </button>
            </div>
          </div>

          {/* Download Official PDF */}
          <div style={{ marginBottom: '32px' }}>
            <button
              onClick={handleDownloadPdf}
              className="btn-pill btn-blue-pill"
              style={{
                maxWidth: '440px',
                width: '100%',
                fontSize: '1.18rem',
                minHeight: '48px',
                fontWeight: 800,
                margin: '0 auto',
                gap: '10px',
              }}
            >
              <Download size={22} />
              <span>{t('claim.downloadPdf', 'Download Relief Form (PDF)')}</span>
            </button>
          </div>

          {/* "Also prepare:" Cards for document re-issuance & insurance */}
          <div style={{ textAlign: 'left', marginTop: '36px', borderTop: '1.5px solid var(--border)', paddingTop: '28px' }}>
            <h3 style={{ fontSize: '1.38rem', marginBottom: '6px', color: 'var(--text)', fontWeight: 800 }}>
              {t('claim.alsoPreparedTitle', 'Also Prepared For You (One-Click Application Drafts)')}
            </h3>
            <p style={{ fontSize: '1rem', color: 'var(--text-muted)', marginBottom: '20px', fontWeight: 600 }}>
              {t(
                'claim.alsoPreparedSubtitle',
                'Since flood waters swept away your papers, we generated ready-to-sign formal draft letters for state agencies:'
              )}
            </p>

            <div
              className="claim-drafts-grid"
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                gap: '16px',
              }}
            >
              {[
                {
                  docType: 'aadhaar_reissue',
                  title: t('claim.draft1Title', 'Aadhaar Re-print Request'),
                  dept: t('claim.draft1Dept', 'UIDAI / Aadhaar Seva Kendra'),
                  desc: t(
                    'claim.draft1Desc',
                    'Letter with Panchayat attestation requesting emergency biometric reprint without fee.'
                  ),
                },
                {
                  docType: 'ration_card_reissue',
                  title: t('claim.draft2Title', 'Ration Card Duplicate Application'),
                  dept: t('claim.draft2Dept', 'Dept. of Food & Supplies'),
                  desc: t(
                    'claim.draft2Desc',
                    'Family member endorsement requesting emergency duplicate ration booklet.'
                  ),
                },
                {
                  docType: 'land_record_reissue',
                  title: t('claim.draft3Title', 'Land Record (RoR) Certificate'),
                  dept: t('claim.draft3Dept', 'Block Land Reforms Office (BL&LRO)'),
                  desc: t(
                    'claim.draft3Desc',
                    'Plot verification request supported by geo-tagged photos and neighbours’ statements.'
                  ),
                },
                {
                  docType: hasCropLoss ? 'insurance_crop' : 'insurance_home',
                  title: t('claim.draft4Title', 'Crop & House Insurance Notice'),
                  dept: t('claim.draft4Dept', 'PMFBY / General Insurance'),
                  desc: t(
                    'claim.draft4Desc',
                    'Formal 72-hour disaster intimation notice for crop inundation & building loss.'
                  ),
                },
              ].map((draft, dIdx) => (
                <div
                  key={dIdx}
                  style={{
                    backgroundColor: '#FFFFFF',
                    border: '1.5px solid var(--border)',
                    borderRadius: '16px',
                    padding: '20px',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <div style={{ fontSize: '0.84rem', color: 'var(--accent)', fontWeight: 800 }}>
                      {draft.dept}
                    </div>
                    <div style={{ fontWeight: 800, fontSize: '1.08rem', color: 'var(--text)', margin: '4px 0 8px 0' }}>
                      {draft.title}
                    </div>
                    <p style={{ fontSize: '0.92rem', color: 'var(--text-muted)', margin: 0, lineHeight: 1.5, fontWeight: 600 }}>
                      {draft.desc}
                    </p>
                  </div>
                  <button
                    onClick={() => handleDownloadDraft(draft.docType)}
                    disabled={draftBusy !== null}
                    className="btn-outline-pill"
                    style={{
                      marginTop: '16px',
                      padding: '10px 18px',
                      fontSize: '0.9rem',
                      fontWeight: 800,
                      minHeight: '44px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                    }}
                  >
                    <FileText size={16} />{' '}
                    {draftBusy === draft.docType
                      ? t('claim.drafting', 'Preparing letter…')
                      : t('claim.downloadDraft', 'Download Ready Draft')}
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Claim;
