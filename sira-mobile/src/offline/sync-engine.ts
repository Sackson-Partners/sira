/**
 * SIRA Sync Engine — Background connectivity-aware sync manager
 * Triggers batch sync on network reconnection with exponential backoff.
 */
import NetInfo from '@react-native-community/netinfo';
import { OfflineQueue } from './queue';
import { syncBatch } from '../api/sync';

export type SyncStatus = 'idle' | 'syncing' | 'success' | 'error';

type StatusListener = (status: SyncStatus, queueCount: number) => void;

class SyncEngine {
  private isSyncing = false;
  private retryCount = 0;
  private readonly maxRetries = 4;
  private unsubscribeNetInfo: (() => void) | null = null;
  private statusListeners: StatusListener[] = [];
  private deviceId: string = 'unknown';

  // ------------------------------------------------------------------
  // Lifecycle
  // ------------------------------------------------------------------

  start(deviceId: string) {
    this.deviceId = deviceId;
    this.unsubscribeNetInfo = NetInfo.addEventListener(state => {
      if (state.isConnected && !this.isSyncing) {
        this.sync();
      }
    });
  }

  stop() {
    this.unsubscribeNetInfo?.();
    this.unsubscribeNetInfo = null;
  }

  // ------------------------------------------------------------------
  // Sync
  // ------------------------------------------------------------------

  async sync(): Promise<void> {
    const queue = OfflineQueue.getAll();
    if (queue.length === 0) {
      this.notifyListeners('idle', 0);
      return;
    }

    this.isSyncing = true;
    this.notifyListeners('syncing', queue.length);

    try {
      const result = await syncBatch({
        events: queue,
        device_id: this.deviceId,
        last_sync_at: OfflineQueue.getLastSyncAt() ?? undefined,
      });

      // Remove events that were processed successfully
      const succeededIds = result.results
        .filter(r => r.status === 'success' || r.status === 'duplicate')
        .map(r => r.event_id);

      OfflineQueue.remove(succeededIds);
      OfflineQueue.setLastSyncAt(new Date().toISOString());

      this.retryCount = 0;
      this.notifyListeners('success', OfflineQueue.count());
    } catch (error) {
      console.warn('[SyncEngine] Sync failed:', error);
      this.retryCount++;
      this.notifyListeners('error', OfflineQueue.count());

      if (this.retryCount <= this.maxRetries) {
        // Exponential backoff: 2s, 4s, 8s, 16s
        const delay = Math.min(1000 * Math.pow(2, this.retryCount), 30_000);
        setTimeout(() => this.sync(), delay);
      }
    } finally {
      this.isSyncing = false;
    }
  }

  // ------------------------------------------------------------------
  // Status listeners
  // ------------------------------------------------------------------

  addStatusListener(listener: StatusListener): () => void {
    this.statusListeners.push(listener);
    return () => {
      this.statusListeners = this.statusListeners.filter(l => l !== listener);
    };
  }

  private notifyListeners(status: SyncStatus, queueCount: number) {
    this.statusListeners.forEach(l => l(status, queueCount));
  }

  // ------------------------------------------------------------------
  // Manual trigger (e.g. pull-to-refresh)
  // ------------------------------------------------------------------

  async forcSync(): Promise<void> {
    this.retryCount = 0;
    await this.sync();
  }
}

export const syncEngine = new SyncEngine();
