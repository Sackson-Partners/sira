"""
SIRA Platform - MarineTraffic AIS Integration Service
Phase 2: Maritime vessel tracking for import/export corridors
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://services.marinetraffic.com/api"


class MarineTrafficService:
      """
          Client for the MarineTraffic REST API.
              Handles vessel tracking, port arrivals, and fleet positions.
                  All methods are async for compatibility with FastAPI.
                      """

    def __init__(self) -> None:
              self.api_key: str = settings.MARINE_TRAFFIC_API_KEY
              self._client: Optional[httpx.AsyncClient] = None

    async def _get(self, endpoint: str, params: dict) -> dict | list:
              """Shared async HTTP GET with error handling."""
              params["protocol"] = "json"
              url = f"{BASE_URL}/{endpoint}"

        async with httpx.AsyncClient(timeout=30) as client:
                      try:
                                        r = await client.get(url, params=params)
                                        r.raise_for_status()
                                        return r.json()
except httpx.HTTPStatusError as exc:
                logger.error("MarineTraffic API error %s: %s", exc.response.status_code, exc)
                return {}
except Exception as exc:
                logger.error("MarineTraffic request failed: %s", exc)
                return {}

    # ------------------------------------------------------------------
    # Vessel position
    # ------------------------------------------------------------------

    async def get_vessel_position(self, mmsi: str) -> dict:
              """Get the latest position for a vessel by MMSI."""
              return await self._get(
                  f"getvessel/v:4/{self.api_key}",
                  {"mmsi": mmsi},
              )

    async def get_fleet_positions(self, fleet_id: str) -> list:
              """Get positions for all vessels in a named fleet (batch endpoint)."""
              result = await self._get(
                  f"getfleet/v:3/{self.api_key}",
                  {"fleet_id": fleet_id},
              )
              return result if isinstance(result, list) else result.get("data", [])

    async def get_vessel_track(self, mmsi: str, period: str = "24") -> list:
              """
                      Get historical position track for a vessel.
                              :param period: Hours of history ('24', '48', '168' etc.)
                                      """
              result = await self._get(
                  f"getvessel/v:4/{self.api_key}",
                  {"mmsi": mmsi, "period": period},
              )
              return result if isinstance(result, list) else []

    # ------------------------------------------------------------------
    # Port & arrivals
    # ------------------------------------------------------------------

    async def get_expected_arrivals(self, port_id: str) -> list:
              """Get vessels expected to arrive at a port within 24 hours."""
              result = await self._get(
                  f"expectedarrivals/v:2/{self.api_key}",
                  {"portid": port_id, "msgtype": "extended"},
              )
              return result if isinstance(result, list) else result.get("data", [])

    async def get_port_calls(
              self,
              port_id: str,
              from_date: Optional[str] = None,
              to_date: Optional[str] = None,
    ) -> list:
              """Get historical port call records for a port."""
              params: dict = {"portid": port_id, "msgtype": "extended"}
              if from_date:
                            params["fromdate"] = from_date
                        if to_date:
                                      params["todate"] = to_date

        result = await self._get(
                      f"portcalls/v:5/{self.api_key}",
                      params,
        )
        return result if isinstance(result, list) else result.get("data", [])

    async def get_anchorages(self, port_id: str) -> list:
              """Get vessels currently at anchorage near a port (congestion indicator)."""
        result = await self._get(
                      f"anchorages/v:1/{self.api_key}",
                      {"portid": port_id},
        )
        return result if isinstance(result, list) else result.get("data", [])

    async def get_voyage_info(self, mmsi: str) -> dict:
              """Get voyage details (destination, ETA, cargo) for a vessel."""
        return await self._get(
                      f"getvessel/v:4/{self.api_key}",
                      {"mmsi": mmsi, "msgtype": "extended"},
        )

    # ------------------------------------------------------------------
    # Port metadata
    # ------------------------------------------------------------------

    async def get_port_info(self, port_id: str) -> dict:
              """Get port metadata (coordinates, country, facilities)."""
        return await self._get(
                      f"portdata/v:2/{self.api_key}",
                      {"portid": port_id},
        )

    async def search_ports(self, query: str) -> list:
              """Search for ports by name."""
        result = await self._get(
                      f"searchport/v:2/{self.api_key}",
                      {"search_term": query},
        )
        return result if isinstance(result, list) else result.get("data", [])

    # ------------------------------------------------------------------
    # GeoJSON helpers (for Mapbox integration)
    # ------------------------------------------------------------------

    async def get_fleet_geojson(self, fleet_id: str) -> dict:
              """Return fleet positions as a GeoJSON FeatureCollection for Mapbox."""
              vessels = await self.get_fleet_positions(fleet_id)
              features = []
              for v in vessels:
                            try:
                                              lon = float(v.get("LONGITUDE", 0))
                                              lat = float(v.get("LATITUDE", 0))
                                              features.append({
                                                  "type": "Feature",
                                                  "geometry": {"type": "Point", "coordinates": [lon, lat]},
                                                  "properties": {
                                                      "mmsi": v.get("MMSI"),
                                                      "name": v.get("SHIPNAME"),
                                                      "speed": v.get("SPEED"),
                                                      "heading": v.get("HEADING"),
                                                      "status": v.get("NAVIGATIONAL_STATUS"),
                                                      "destination": v.get("DESTINATION"),
                                                      "eta": v.get("ETA"),
                                                  },
                                              })
except (ValueError, TypeError):
                continue

        return {"type": "FeatureCollection", "features": features}


# ---------------------------------------------------------------------------
# Polling worker
# ---------------------------------------------------------------------------

async def run_maritime_polling(interval_seconds: int = 300) -> None:
      """
          Background worker: polls MarineTraffic API every `interval_seconds`
              and persists vessel positions to TimescaleDB.
                  """
      import asyncio

    service = MarineTrafficService()
    logger.info("MarineTraffic polling worker started (interval=%ds)", interval_seconds)

    while True:
              try:
                            from app.core.config import settings as cfg
                            # Fetch monitored vessel list from DB or config
                            monitored_mmsis: list[str] = getattr(cfg, "MONITORED_MMSI_LIST", [])

            for mmsi in monitored_mmsis:
                              position = await service.get_vessel_position(mmsi)
                              if position:
                                                    await _persist_vessel_position(mmsi, position)

except Exception as exc:
            logger.error("Maritime polling error: %s", exc)

        await asyncio.sleep(interval_seconds)


async def _persist_vessel_position(mmsi: str, data: dict) -> None:
      """Save a vessel position snapshot to TimescaleDB vessel_positions table."""
    try:
              from app.core.database import async_session_factory
        from app.models.vessel import VesselPosition

        pos = VesselPosition(
                      mmsi=mmsi,
                      lat=float(data.get("LATITUDE", 0)),
                      lon=float(data.get("LONGITUDE", 0)),
                      speed=float(data.get("SPEED", 0)),
                      heading=float(data.get("HEADING", 0)),
                      destination=data.get("DESTINATION"),
                      eta=data.get("ETA"),
                      nav_status=data.get("NAVIGATIONAL_STATUS"),
                      raw_payload=data,
        )
        async with async_session_factory() as db:
                      db.add(pos)
                      await db.commit()
except Exception as exc:
        logger.error("Failed to persist vessel position for %s: %s", mmsi, exc)
