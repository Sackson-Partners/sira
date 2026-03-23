import { useEffect, useState } from 'react';
import NetInfo from '@react-native-community/netinfo';
import { useOfflineStore } from '../store/offline.store';

export function useNetworkStatus() {
  const [isOnline, setIsOnline] = useState(true);
  const setOnline = useOfflineStore(s => s.setOnline);

  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener(state => {
      const online = state.isConnected === true;
      setIsOnline(online);
      setOnline(online);
    });
    return () => unsubscribe();
  }, [setOnline]);

  return { isOnline };
}
