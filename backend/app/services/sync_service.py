"""
SyncService — Core offline-first batch sync engine
Handles deduplication, ordering, and conflict resolution for mobile client events.
"""

import logging
import time
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.checkpoint import Checkpoint
from app.models.sync_log import SyncLog
from app.models.shipment import Shipment
from app.schemas.sync import SyncEvent, BatchSyncRequest, BatchSyncResponse, EventResult, ServerUpdate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event type constants
# ---------------------------------------------------------------------------

EVENT_CHECKPOINT_CONFIRMED = "CHECKPOINT_CONFIRMED"
EVENT_EVIDENCE_CAPTURED = "EVIDENCE_CAPTURED"
EVENT_DRIVER_LOCATION = "DRIVER_LOCATION"
EVENT_SHIPMENT_STATUS_UPDATE = "SHIPMENT_STATUS_UPDATE"
EVENT_PORT_VALIDATION = "PORT_VALIDATION"
EVENT_PORT_STATUS_UPDATE = "PORT_STATUS_UPDATE"

VALID_CHECKPOINT_TYPES = {
    "departure", "waypoint", "border", "port_entry", "port_exit",
    "delivery", "inspection", "fuel_stop", "emergency_stop", "driver_change",
}


class SyncService:
    """
    Core batch sync engine.

    Processing order:
    1. Sort events by client_timestamp (critical for correctness)
    2. Deduplicate using event_id / client_event_id
    3. Route each event to its handler
    4. Return per-event results + any server-side delta updates
    """

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_batch(
        self,
        request: BatchSyncRequest,
        user_id: int,
        organization_id: int,
    ) -> BatchSyncResponse:
        start_ms = int(time.time() * 1000)

        # Sort by client timestamp so causal ordering is preserved
        sorted_events = sorted(request.events, key=lambda e: e.client_timestamp)

        results: List[EventResult] = []
        for event in sorted_events:
            result = self._process_single_event(event, user_id, organization_id)
            results.append(result)

        success_count = sum(1 for r in results if r.status == "success")
        failed_count = sum(1 for r in results if r.status == "failed")
        conflict_count = sum(1 for r in results if r.status == "conflict")

        server_updates = self._get_delta_updates(
            user_id=user_id,
            organization_id=organization_id,
            last_sync_at=request.last_sync_at,
        )

        duration_ms = int(time.time() * 1000) - start_ms

        # Persist sync audit log
        self._log_sync(
            user_id=user_id,
            organization_id=organization_id,
            device_id=request.device_id,
            events_count=len(sorted_events),
            success_count=success_count,
            failed_count=failed_count,
            conflicts_count=conflict_count,
            status="completed" if failed_count == 0 else "partial",
            duration_ms=duration_ms,
        )

        return BatchSyncResponse(
            processed=len(results),
            success_count=success_count,
            failed_count=failed_count,
            conflict_count=conflict_count,
            results=results,
            server_updates=server_updates,
        )

    # ------------------------------------------------------------------
    # Event dispatch
    # ------------------------------------------------------------------

    def _process_single_event(
        self,
        event: SyncEvent,
        user_id: int,
        organization_id: int,
    ) -> EventResult:
        try:
            handlers = {
                EVENT_CHECKPOINT_CONFIRMED: self._handle_checkpoint,
                EVENT_DRIVER_LOCATION: self._handle_driver_location,
                EVENT_SHIPMENT_STATUS_UPDATE: self._handle_shipment_status,
                EVENT_PORT_VALIDATION: self._handle_port_validation,
                EVENT_PORT_STATUS_UPDATE: self._handle_port_validation,
                EVENT_EVIDENCE_CAPTURED: self._handle_evidence_captured,
            }

            handler = handlers.get(event.type)
            if not handler:
                return EventResult(
                    event_id=event.event_id,
                    status="failed",
                    error=f"Unknown event type: {event.type}",
                )

            server_id = handler(event, user_id, organization_id)
            return EventResult(
                event_id=event.event_id,
                status="success",
                server_id=server_id,
            )

        except DuplicateEventError:
            return EventResult(
                event_id=event.event_id,
                status="duplicate",
                error="Event already processed",
            )
        except Exception as exc:
            logger.error(f"Failed to process event {event.event_id} ({event.type}): {exc}")
            return EventResult(
                event_id=event.event_id,
                status="failed",
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _handle_checkpoint(
        self,
        event: SyncEvent,
        user_id: int,
        organization_id: int,
    ) -> int:
        data = event.data
        client_event_id = event.event_id

        # Deduplication: if we've already stored this event_id, skip
        existing = (
            self.db.query(Checkpoint)
            .filter(Checkpoint.client_event_id == client_event_id)
            .first()
        )
        if existing:
            raise DuplicateEventError(client_event_id)

        checkpoint_type = data.get("checkpoint_type", "waypoint")
        if checkpoint_type not in VALID_CHECKPOINT_TYPES:
            checkpoint_type = "waypoint"

        # Parse client timestamp
        try:
            ts = datetime.fromisoformat(event.client_timestamp.replace("Z", "+00:00"))
        except ValueError:
            ts = datetime.now(timezone.utc)

        cp = Checkpoint(
            shipment_id=int(data["shipment_id"]),
            organization_id=organization_id,
            user_id=user_id,
            role=data.get("role", "driver"),
            checkpoint_type=checkpoint_type,
            latitude=float(data["latitude"]),
            longitude=float(data["longitude"]),
            accuracy_meters=data.get("accuracy_m"),
            altitude_m=data.get("altitude_m"),
            location_name=data.get("location_name"),
            notes=data.get("notes"),
            offline_queued=bool(data.get("offline_queued", False)),
            device_id=data.get("device_id"),
            client_event_id=client_event_id,
            timestamp=ts,
            synced_at=datetime.now(timezone.utc),
            extra_metadata=data.get("metadata", {}),
        )
        self.db.add(cp)
        self.db.commit()
        self.db.refresh(cp)
        return cp.id

    def _handle_driver_location(
        self,
        event: SyncEvent,
        user_id: int,
        organization_id: int,
    ) -> Optional[int]:
        """
        Driver location pings. We store only the latest per device to avoid bloat.
        In production, these would go to a time-series store (e.g. iot_data table).
        Here we update the vehicle's last_known_lat/lng as a lightweight approach.
        """
        data = event.data
        lat = data.get("latitude")
        lng = data.get("longitude")

        if not lat or not lng:
            raise ValueError("Driver location event missing latitude/longitude")

        # Optionally update vehicle last_known_lat/lng
        vehicle_id = data.get("vehicle_id")
        if vehicle_id:
            from app.models.vehicle import Vehicle
            vehicle = self.db.query(Vehicle).filter(Vehicle.id == int(vehicle_id)).first()
            if vehicle:
                vehicle.last_known_lat = float(lat)
                vehicle.last_known_lng = float(lng)
                vehicle.last_seen_at = datetime.now(timezone.utc)
                self.db.commit()

        return None  # No new record created

    def _handle_shipment_status(
        self,
        event: SyncEvent,
        user_id: int,
        organization_id: int,
    ) -> int:
        data = event.data
        shipment_id = int(data["shipment_id"])
        new_status = data.get("status")

        shipment = self.db.query(Shipment).filter(Shipment.id == shipment_id).first()
        if not shipment:
            raise ValueError(f"Shipment {shipment_id} not found")

        # Conflict resolution: server wins if server state is more advanced
        terminal_states = {"completed", "cancelled"}
        if shipment.status in terminal_states:
            logger.warning(
                f"Ignoring status update for shipment {shipment_id}: "
                f"already in terminal state '{shipment.status}'"
            )
            return shipment_id

        if new_status:
            shipment.status = new_status
            self.db.commit()

        return shipment_id

    def _handle_port_validation(
        self,
        event: SyncEvent,
        user_id: int,
        organization_id: int,
    ) -> int:
        """Port officer validation — stored as a checkpoint with port_entry type."""
        data = dict(event.data)
        data["checkpoint_type"] = data.get("checkpoint_type", "port_entry")
        modified_event = SyncEvent(
            event_id=event.event_id,
            type=EVENT_CHECKPOINT_CONFIRMED,
            client_timestamp=event.client_timestamp,
            data=data,
        )
        return self._handle_checkpoint(modified_event, user_id, organization_id)

    def _handle_evidence_captured(
        self,
        event: SyncEvent,
        user_id: int,
        organization_id: int,
    ) -> Optional[int]:
        """
        Evidence metadata sync. The actual file is uploaded separately via
        POST /evidence/upload. Here we just acknowledge receipt.
        """
        data = event.data
        logger.info(
            f"Evidence event received: shipment={data.get('shipment_id')}, "
            f"type={data.get('file_type')}, hash={data.get('hash', 'N/A')}"
        )
        return None

    # ------------------------------------------------------------------
    # Delta updates
    # ------------------------------------------------------------------

    def _get_delta_updates(
        self,
        user_id: int,
        organization_id: int,
        last_sync_at: Optional[str],
    ) -> List[ServerUpdate]:
        """
        Fetch server-side changes since last_sync_at to push back to client.
        Returns recent checkpoints created by others on the same shipments.
        """
        updates: List[ServerUpdate] = []

        if not last_sync_at:
            return updates

        try:
            since = datetime.fromisoformat(last_sync_at.replace("Z", "+00:00"))
        except ValueError:
            return updates

        # Return checkpoints created after last sync (by other users)
        recent_checkpoints = (
            self.db.query(Checkpoint)
            .filter(
                Checkpoint.organization_id == organization_id,
                Checkpoint.created_at >= since,
                Checkpoint.user_id != user_id,
            )
            .limit(50)
            .all()
        )

        for cp in recent_checkpoints:
            updates.append(
                ServerUpdate(
                    resource_type="checkpoint",
                    resource_id=cp.id,
                    action="created",
                    data={
                        "shipment_id": cp.shipment_id,
                        "checkpoint_type": cp.checkpoint_type,
                        "latitude": cp.latitude,
                        "longitude": cp.longitude,
                        "timestamp": cp.timestamp.isoformat(),
                    },
                    updated_at=cp.created_at.isoformat(),
                )
            )

        return updates

    # ------------------------------------------------------------------
    # Audit logging
    # ------------------------------------------------------------------

    def _log_sync(
        self,
        user_id: int,
        organization_id: int,
        device_id: str,
        events_count: int,
        success_count: int,
        failed_count: int,
        conflicts_count: int,
        status: str,
        duration_ms: int,
    ):
        try:
            log = SyncLog(
                organization_id=organization_id,
                user_id=user_id,
                device_id=device_id,
                sync_type="batch",
                events_count=events_count,
                success_count=success_count,
                failed_count=failed_count,
                conflicts_count=conflicts_count,
                status=status,
                duration_ms=duration_ms,
            )
            self.db.add(log)
            self.db.commit()
        except Exception as exc:
            logger.error(f"Failed to write sync log: {exc}")


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class DuplicateEventError(Exception):
    """Raised when an event_id has already been processed (idempotency)."""

    def __init__(self, event_id: str):
        self.event_id = event_id
        super().__init__(f"Duplicate event: {event_id}")
