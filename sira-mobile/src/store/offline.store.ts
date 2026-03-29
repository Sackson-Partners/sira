/**
 * Offline Store — Zustand store for sync state
 */
import { create } from 'zustand';
import type { SyncStatus } from '../offline/sync-engine';

interface OfflineState {
  isSyncing: boolean;
  syncStatus: SyncStatus;
  queueCount: number;
  lastSyncAt: string | null;
  isOnline: boolean;
}

interface OfflineActions {
  setOnline: (online: boolean) => void;
  setSyncStatus: (status: SyncStatus, queueCount: number) => void;
  setLastSyncAt: (ts: string) => void;
}

export const useOfflineStore = create<OfflineState & OfflineActions>((set) => ({
  isSyncing: false,
  syncStatus: 'idle',
  queueCount: 0,
  lastSyncAt: null,
  isOnline: true,

  setOnline: (isOnline) => set({ isOnline }),

  setSyncStatus: (syncStatus, queueCount) =>
    set({ syncStatus, queueCount, isSyncing: syncStatus === 'syncing' }),

  setLastSyncAt: (lastSyncAt) => set({ lastSyncAt }),
}));
