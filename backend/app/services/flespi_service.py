"""
Flespi Telematics Integration Service
Handles MQTT ingestion of GPS/telematics data from Flespi platform.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class FlespiService:
    """Service for Flespi telematics platform integration."""

    def __init__(self):
        self.token = settings.FLESPI_TOKEN
        self.rest_url = settings.FLESPI_REST_URL
        self.headers = {
            "Authorization": f"FlespiToken {self.token}",
            "Content-Type": "application/json",
        }

    @property
    def is_configured(self) -> bool:
        return bool(self.token)

    async def get_devices(self) -> List[Dict[str, Any]]:
        """Fetch all devices from Flespi."""
        if not self.is_configured:
            return []
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.rest_url}/gw/devices/all",
                headers=self.headers,
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("result", [])

    async def get_device_telemetry(self, device_id: int) -> Dict[str, Any]:
        """Get latest telemetry for a specific device."""
        if not self.is_configured:
            return {}
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.rest_url}/gw/devices/{device_id}/telemetry/all",
                headers=self.headers,
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            result = data.get("result", [])
            return result[0] if result else {}

    async def get_device_messages(
        self, device_id: int, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent messages (telemetry readings) from a device."""
        if not self.is_configured:
            return []
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.rest_url}/gw/devices/{device_id}/messages",
                headers=self.headers,
                params={"count": limit},
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("result", [])

    def parse_telemetry_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a Flespi telemetry message into our internal format."""
        return {
            "device_id": message.get("ident"),
            "timestamp": datetime.fromtimestamp(
                message.get("timestamp", 0), tz=timezone.utc
            ),
            "latitude": message.get("position.latitude"),
            "longitude": message.get("position.longitude"),
            "altitude": message.get("position.altitude"),
            "speed": message.get("position.speed"),
            "heading": message.get("position.direction"),
            "battery_level": message.get("battery.level"),
            "fuel_level": message.get("fuel.level"),
            "temperature": message.get("temperature"),
            "ignition": message.get("engine.ignition.status"),
            "raw_payload": json.dumps(message),
        }

    async def sync_devices_to_db(self, db_session) -> int:
        """Sync Flespi devices into the IoTDevice table. Returns count of synced devices."""
        from app.models.iot_device import IoTDevice

        if not self.is_configured:
            logger.warning("Flespi not configured, skipping device sync")
            return 0

        devices = await self.get_devices()
        count = 0
        for dev in devices:
            device_id = str(dev.get("id"))
            existing = (
                db_session.query(IoTDevice)
                .filter(IoTDevice.device_id == device_id)
                .first()
            )
            if not existing:
                iot = IoTDevice(
                    device_id=device_id,
                    device_type="gps_tracker",
                    manufacturer=dev.get("device_type", {}).get("title", "Flespi"),
                    model=dev.get("device_type", {}).get("name", "unknown"),
                    status="active",
                )
                db_session.add(iot)
                count += 1
            else:
                existing.status = "active"

        db_session.commit()
        logger.info(f"Synced {count} new Flespi devices")
        return count


# Singleton instance
flespi_service = FlespiService()
