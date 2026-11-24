// src/components/OfflineBanner.tsx
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { WifiOff, CheckCircle2, RefreshCw } from 'lucide-react';
import {
  getOfflineQueue,
  removeQueueItem,
  updateQueueClaimId,
  QueueItem,
} from '../utils/indexedDB';
import {
  createClaimOnServer,
  uploadAudio,
  uploadPhoto,
  sendText,
  submitMeshEnvelope,
  linkHouseholdToClaim,
  updateFields,
  submitClaim,
  saveToken,
  DEMO_MODE,
} from '../api/client';

export const OfflineBanner: React.FC = () => {
  const { t } = useTranslation();
  const [isOnline, setIsOnline] = useState<boolean>(navigator.onLine);
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [synced, setSynced] = useState<boolean>(false);

  const checkQueue = async () => {
    try {
      const queue = await getOfflineQueue();
      setPendingCount(queue.length);
    } catch {
      // ignore
    }
  };

  const syncQueue = async () => {
    if (!navigator.onLine) return;
    setIsSyncing(true);
    try {
      const queue = await getOfflineQueue();
      if (queue.length === 0) {
        setIsSyncing(false);
        return;
      }

      // Sort by creation time so claim_create runs first
      const sorted = [...queue].sort((x, y) => {
        if (x.type === 'claim_create' && y.type !== 'claim_create') return -1;
        if (y.type === 'claim_create' && x.type !== 'claim_create') return 1;
        return x.createdAt - y.createdAt;
      });

      let remaining = sorted.length;
      const idMapping: Record<string, string> = {};
      const blocked = new Set<string>(); // a claim whose earlier step failed waits (keeps the order)

      for (const item of sorted) {
        const targetClaimId = idMapping[item.claimId] || item.claimId;
        if (blocked.has(item.claimId)) continue;
        try {
          if (!DEMO_MODE) {
            if (item.type === 'claim_create') {
              const res = await createClaimOnServer(item.payload);
              if (res && res.id) {
                idMapping[item.claimId] = res.id;
                saveToken(res.id, res.claim_token);
                await updateQueueClaimId(item.claimId, res.id);
                // "Use my household" chosen while offline: link the vault now
                if (item.payload?.household_id) {
                  try {
                    await linkHouseholdToClaim(res.id, item.payload.household_id);
                  } catch (linkErr) {
                    console.warn('Synced claim could not use the family vault', linkErr);
                  }
                }
              }
            } else if (item.type === 'fields' && item.payload) {
              await updateFields(targetClaimId, item.payload);
            } else if (item.type === 'submit') {
              await submitClaim(targetClaimId);
            } else if (item.type === 'text' && item.text) {
              await sendText(targetClaimId, item.text);
            } else if (item.type === 'audio' && item.blob) {
              await uploadAudio(targetClaimId, item.blob);
            } else if (item.type === 'photo' && item.blob) {
              const m = item.metadata || {};
              const file = new File([item.blob], m.name || 'photo.jpg', {
                type: item.blob.type || 'image/jpeg',
              });
              await uploadPhoto(targetClaimId, file, m.lat, m.lon, m.taken_at);
            } else if (item.type === 'mesh_relay' && item.payload) {
              const res = await submitMeshEnvelope(item.payload);
              if (!res.delivered) throw new Error(res.error || 'mesh delivery failed');
            }
          }
          await removeQueueItem(item.id);
          remaining -= 1;
        } catch (e) {
          blocked.add(item.claimId);
          console.warn(`Could not sync queued ${item.type}; will retry on next check`, e);
        }
      }

      setPendingCount(remaining);
      if (remaining === 0) {
        setSynced(true);
        setTimeout(() => setSynced(false), 6000);
      }
    } finally {
      setIsSyncing(false);
    }
  };

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      syncQueue();
    };

    const handleOffline = () => {
      setIsOnline(false);
      checkQueue();
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Initial queue check
    checkQueue();

    // Check periodically for changes
    const interval = setInterval(checkQueue, 5000);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      clearInterval(interval);
    };
  }, []);

  if (isOnline && !synced && pendingCount === 0) return null;

  return (
    <div
      role="alert"
      aria-live="assertive"
      style={{
        backgroundColor: isOnline ? '#3E6B48' : '#C0582F',
        color: '#FFFFFF',
        padding: '10px 16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '12px',
        fontSize: '0.92rem',
        fontWeight: 600,
        zIndex: 100,
        boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
      }}
    >
      {isOnline ? (
        <>
          <CheckCircle2 size={20} aria-hidden="true" />
          <span>
            {t(
              'offline.onlineSync',
              'Connected back online. All offline claims, recordings, and photos have been synced.'
            )}
          </span>
        </>
      ) : (
        <>
          <WifiOff size={20} aria-hidden="true" />
          <span>
            {t(
              'offline.offlineAlert',
              'You are offline. Your claim, recordings and photos are saved locally on this phone and will upload automatically when Wi-Fi/signal returns.'
            )}
            {pendingCount > 0 && (
              <strong style={{ marginLeft: '8px', textDecoration: 'underline' }}>
                {t('offline.savedOnPhone', 'Saved on this phone, {{count}} item waiting', {
                  count: pendingCount,
                  defaultValue: `Saved on this phone, ${pendingCount} item${pendingCount > 1 ? 's' : ''} waiting`,
                })}
              </strong>
            )}
          </span>
          {isSyncing && <RefreshCw size={18} className="animate-spin" />}
        </>
      )}
    </div>
  );
};
