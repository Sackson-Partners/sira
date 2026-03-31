"""
MarineTraffic AIS Integration Service
Provides vessel tracking via the MarineTraffic API.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class MarineTrafficService:
    """Service for MarineTraffic AIS vessel tracking."""

    def __init__(self):
        self.api_key = settings.MARINETRAFFIC_API_KEY
        self.api_url = settings.MARINETRAFFIC_API_URL

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key not in ("", "test-key"))

    async def get_vessel_position(self, mmsi: str) -> Optional[Dict[str, Any]]:
        """Get current position for a vessel by MMSI."""
        if not self.is_configured:
            return None
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.api_url}/exportvessel/v:5/{self.api_key}",
                params={
                    "mmsi": mmsi,
                    "protocol": "jsono",
                    "msgtype": "simple",
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                return self._parse_position(data[0])
            return None

    async def get_fleet_positions(
        self, mmsi_list: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get positions for multiple vessels. If no MMSI list, gets all from DB."""
        if not self.is_configured:
            return []

        # Use fleet tracking endpoint if available
        async with httpx.AsyncClient() as client:
            params: Dict[str, Any] = {
                "protocol": "jsono",
                "msgtype": "simple",
            }
            if mmsi_list:
                params["mmsi"] = ",".join(mmsi_list)

            resp = await client.get(
                f"{self.api_url}/exportvessels/v:8/{self.api_key}",
                params=params,
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return [self._parse_position(v) for v in data]
            return []

    async def get_vessel_details(self, imo: str) -> Optional[Dict[str, Any]]:
        """Get detailed vessel information by IMO number."""
        if not self.is_configured:
            return None
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.api_url}/vesseldetails/v:1/{self.api_key}",
                params={"imo": imo, "protocol": "jsono"},
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                return data[0]
            return None

    async def get_port_calls(
        self, port_id: str, timespan: int = 60
    ) -> List[Dict[str, Any]]:
        """Get recent port calls for a specific port."""
        if not self.is_configured:
            return []
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.api_url}/expectedarrivals/v:3/{self.api_key}",
                params={
                    "portid": port_id,
                    "protocol": "jsono",
                    "timespan": timespan,
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []

    def _parse_position(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Parse MarineTraffic position response into internal format."""
        return {
            "mmsi": raw.get("MMSI"),
            "imo": raw.get("IMO"),
            "ship_name": raw.get("SHIPNAME"),
            "latitude": float(raw.get("LAT", 0)),
            "longitude": float(raw.get("LON", 0)),
            "speed": float(raw.get("SPEED", 0)) / 10.0,  # MT returns speed * 10
            "heading": float(raw.get("HEADING", 0)),
            "course": float(raw.get("COURSE", 0)),
            "status": raw.get("STATUS"),
            "destination": raw.get("DESTINATION"),
            "eta": raw.get("ETA"),
            "timestamp": raw.get("TIMESTAMP"),
        }

    async def sync_vessel_positions(self, db_session) -> int:
        """Update vessel positions in the database from MarineTraffic."""
        from app.models.vessel import Vessel

        if not self.is_configured:
            logger.warning("MarineTraffic not configured, skipping sync")
            return 0

        vessels = db_session.query(Vessel).filter(Vessel.mmsi.isnot(None)).all()
        if not vessels:
            return 0

        mmsi_list = [v.mmsi for v in vessels if v.mmsi]
        positions = await self.get_fleet_positions(mmsi_list)

        count = 0
        mmsi_map = {v.mmsi: v for v in vessels}
        for pos in positions:
            vessel = mmsi_map.get(pos.get("mmsi"))
            if vessel:
                vessel.current_lat = pos.get("latitude")
                vessel.current_lng = pos.get("longitude")
                vessel.current_speed = pos.get("speed")
                vessel.current_heading = pos.get("heading")
                vessel.current_destination = pos.get("destination")
                vessel.position_updated_at = datetime.now(timezone.utc)
                vessel.ais_status = pos.get("status")
                count += 1

        db_session.commit()
        logger.info(f"Updated {count} vessel positions from MarineTraffic")
        return count


# Singleton instance
marinetraffic_service = MarineTrafficService()
