import { useEffect } from 'react';
import { syncEngine } from '../offline/sync-engine';
import { useOfflineStore } from '../store/offline.store';
import { OfflineQueue } from '../offline/queue';

export function useOfflineSync(deviceId: string) {
  const { setSyncStatus, setLastSyncAt } = useOfflineStore();

  useEffect(() => {
    syncEngine.start(deviceId);

    const removeListener = syncEngine.addStatusListener((status, queueCount) => {
      setSyncStatus(status, queueCount);
      if (status === 'success') {
        setLastSyncAt(new Date().toISOString());
      }
    });

    return () => {
      removeListener();
      syncEngine.stop();
    };
  }, [deviceId, setSyncStatus, setLastSyncAt]);

  return {
    forceSync: () => syncEngine.forcSync(),
    queueCount: OfflineQueue.count(),
  };
}
