// src/components/OfflineBanner.tsx
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { WifiOff, CheckCircle2 } from 'lucide-react';
import { getOfflineQueue, removeQueueItem } from '../utils/indexedDB';
import { uploadAudio, uploadPhoto, DEMO_MODE } from '../api/client';

export const OfflineBanner: React.FC = () => {
  const { t } = useTranslation();
  const [isOnline, setIsOnline] = useState<boolean>(navigator.onLine);
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [synced, setSynced] = useState<boolean>(false);

  const checkQueue = async () => {
    try {
      const queue = await getOfflineQueue();
      setPendingCount(queue.length);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    const handleOnline = async () => {
      setIsOnline(true);
      const queue = await getOfflineQueue();
      if (queue.length === 0) return;
      // Upload each saved item; only delete it once the server has it. Anything that
      // fails stays queued for the next time the signal returns.
      let left = queue.length;
      for (const item of queue.sort((x, y) => x.createdAt - y.createdAt)) {
        try {
          if (!DEMO_MODE) {
            if (item.type === 'audio') await uploadAudio(item.claimId, item.blob);
            else {
              const m = item.metadata || {};
              const file = new File([item.blob], m.name || 'photo.jpg', { type: item.blob.type || 'image/jpeg' });
              await uploadPhoto(item.claimId, file, m.lat, m.lon, m.taken_at);
            }
          }
          await removeQueueItem(item.id);
          left -= 1;
        } catch (e) {
          console.warn('Offline item not sent yet; will retry', e);
        }
      }
      setPendingCount(left);
      if (left === 0) {
        setSynced(true);
        setTimeout(() => setSynced(false), 5000);
      }
    };

    const handleOffline = () => {
      setIsOnline(false);
      checkQueue();
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    checkQueue();

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  if (isOnline && !synced) return null;

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
        fontSize: '0.95rem',
        fontWeight: 500,
        zIndex: 50,
      }}
    >
      {isOnline ? (
        <>
          <CheckCircle2 size={20} aria-hidden="true" />
          <span>{t('offline.onlineSync', 'Connected back online. Offline recordings and photos have been synced.')}</span>
        </>
      ) : (
        <>
          <WifiOff size={20} aria-hidden="true" />
          <span>
            {t(
              'offline.offlineAlert',
              'You are currently offline. Any recordings or photos will be saved locally on your phone and sent automatically when internet returns.'
            )}
            {pendingCount > 0 &&
              ` ${t('offline.queuedItems', {
                count: pendingCount,
                plural: pendingCount > 1 ? 's' : '',
                defaultValue: `(${pendingCount} item${pendingCount > 1 ? 's' : ''} queued)`,
              })}`}
          </span>
        </>
      )}
    </div>
  );
};
