// src/components/OfflineBanner.tsx
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { WifiOff, CheckCircle2 } from 'lucide-react';
import { getOfflineQueue, clearOfflineQueue } from '../utils/indexedDB';

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
      if (queue.length > 0) {
        setSynced(true);
        await clearOfflineQueue();
        setPendingCount(0);
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
