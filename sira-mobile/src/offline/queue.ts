/**
 * SIRA Offline Queue — MMKV-backed persistent event queue
 * Events are stored locally and synced when connectivity is restored.
 */
import { MMKV } from 'react-native-mmkv';
import { SyncEvent } from './event-types';

const storage = new MMKV({ id: 'sira-offline-queue' });

const QUEUE_KEY = 'offline_queue';
const LAST_SYNC_KEY = 'last_sync_at';

function generateEventId(): string {
  return `evt_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
}

export const OfflineQueue = {
  /**
   * Enqueue a new event. Returns the generated event_id.
   */
  push(event: Omit<SyncEvent, 'event_id' | 'client_timestamp'>): string {
    const eventId = generateEventId();
    const fullEvent: SyncEvent = {
      ...event,
      event_id: eventId,
      client_timestamp: new Date().toISOString(),
    };

    const queue = this.getAll();
    queue.push(fullEvent);
    storage.set(QUEUE_KEY, JSON.stringify(queue));
    return eventId;
  },

  /**
   * Return all queued events.
   */
  getAll(): SyncEvent[] {
    const raw = storage.getString(QUEUE_KEY);
    if (!raw) return [];
    try {
      return JSON.parse(raw) as SyncEvent[];
    } catch {
      return [];
    }
  },

  /**
   * Remove events by their event_id (after successful sync).
   */
  remove(eventIds: string[]): void {
    const idSet = new Set(eventIds);
    const queue = this.getAll().filter(e => !idSet.has(e.event_id));
    storage.set(QUEUE_KEY, JSON.stringify(queue));
  },

  /**
   * Count of pending events.
   */
  count(): number {
    return this.getAll().length;
  },

  /**
   * ISO timestamp of last successful sync.
   */
  getLastSyncAt(): string | null {
    return storage.getString(LAST_SYNC_KEY) ?? null;
  },

  setLastSyncAt(timestamp: string): void {
    storage.set(LAST_SYNC_KEY, timestamp);
  },

  /**
   * Wipe the queue (use with care — only after full successful sync).
   */
  clear(): void {
    storage.delete(QUEUE_KEY);
  },
};
