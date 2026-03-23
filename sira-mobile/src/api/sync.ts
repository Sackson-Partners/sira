/**
 * Sync API — Batch sync endpoint calls
 */
import apiClient from './client';
import { SyncEvent } from '../offline/event-types';

export interface BatchSyncRequest {
  device_id: string;
  events: SyncEvent[];
  last_sync_at?: string;
}

export interface EventResult {
  event_id: string;
  status: 'success' | 'failed' | 'duplicate' | 'conflict';
  server_id?: number;
  error?: string;
}

export interface BatchSyncResponse {
  processed: number;
  success_count: number;
  failed_count: number;
  conflict_count: number;
  results: EventResult[];
  server_updates: ServerUpdate[];
  sync_timestamp: string;
}

export interface ServerUpdate {
  resource_type: string;
  resource_id: number;
  action: 'created' | 'updated' | 'deleted';
  data: Record<string, unknown>;
  updated_at: string;
}

export async function syncBatch(request: BatchSyncRequest): Promise<BatchSyncResponse> {
  const { data } = await apiClient.post<BatchSyncResponse>('/sync/batch', request);
  return data;
}

export async function getSyncStatus(): Promise<unknown> {
  const { data } = await apiClient.get('/sync/status');
  return data;
}
