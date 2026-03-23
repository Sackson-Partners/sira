// SIRA Offline-First — Event Type Definitions

export type SyncEventType =
  | 'CHECKPOINT_CONFIRMED'
  | 'EVIDENCE_CAPTURED'
  | 'DRIVER_LOCATION'
  | 'SHIPMENT_STATUS_UPDATE'
  | 'PORT_VALIDATION'
  | 'PORT_STATUS_UPDATE';

export interface SyncEvent {
  event_id: string;
  type: SyncEventType;
  client_timestamp: string;  // ISO 8601
  data: Record<string, unknown>;
}

export interface CheckpointEvent extends SyncEvent {
  type: 'CHECKPOINT_CONFIRMED';
  data: {
    shipment_id: number;
    checkpoint_type: string;
    latitude: number;
    longitude: number;
    accuracy_m?: number;
    location_name?: string;
    notes?: string;
    offline_queued: boolean;
    device_id?: string;
    metadata?: Record<string, unknown>;
  };
}

export interface DriverLocationEvent extends SyncEvent {
  type: 'DRIVER_LOCATION';
  data: {
    vehicle_id?: number;
    latitude: number;
    longitude: number;
    speed_kmh?: number;
    accuracy_m?: number;
    timestamp: string;
  };
}

export interface EvidenceEvent extends SyncEvent {
  type: 'EVIDENCE_CAPTURED';
  data: {
    shipment_id: number;
    checkpoint_id?: number;
    local_file_uri: string;   // Local path before upload
    file_type: 'photo' | 'video';
    latitude?: number;
    longitude?: number;
    hash: string;             // SHA-256 for integrity verification
  };
}

export interface ShipmentStatusEvent extends SyncEvent {
  type: 'SHIPMENT_STATUS_UPDATE';
  data: {
    shipment_id: number;
    status: string;
    notes?: string;
  };
}

export interface PortValidationEvent extends SyncEvent {
  type: 'PORT_VALIDATION';
  data: {
    shipment_id: number;
    vessel_name?: string;
    operation_type: string;
    latitude: number;
    longitude: number;
    notes?: string;
    offline_queued: boolean;
  };
}
