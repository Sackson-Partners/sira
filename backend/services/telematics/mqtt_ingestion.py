"""
SIRA Platform - Flespi MQTT Telematics Ingestion Worker
Phase 2: Real-time GPS & IoT telemetry for trucks and trains via Flespi MQTT broker
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

FLESPI_MQTT_HOST = "mqtt.flespi.io"
FLESPI_MQTT_PORT = 8883  # TLS
TOPIC = "flespi/message/gw/devices/+/+"


async def persist_telemetry(payload: dict) -> None:
      """Normalise a Flespi message and persist it to the database."""
      from app.core.database import async_session_factory
      from app.models.telemetry import TelemetryEvent

    event = TelemetryEvent(
              device_id=payload.get("ident", "unknown"),
              lat=payload.get("position.latitude"),
              lon=payload.get("position.longitude"),
              speed=payload.get("position.speed", 0),
              direction=payload.get("position.direction"),
              fuel_level=payload.get("can.fuel.level"),
              engine_temp=payload.get("can.engine.temperature"),
              odometer=payload.get("can.odometer"),
              ignition=payload.get("can.engine.ignition"),
              ext_power=payload.get("io.pwr.ext"),
              alarm_event_id=payload.get("alarm.event.id"),
              raw_payload=payload,
              timestamp=payload.get("timestamp"),
    )

    try:
              async with async_session_factory() as db:
                            db.add(event)
                            await db.commit()
                        logger.debug("Persisted telemetry for device %s", event.device_id)
except Exception as exc:
        logger.error("Failed to persist telemetry: %s", exc)


async def process_anomalies(payload: dict) -> None:
      """Rule-based anomaly pre-filter before AI analysis."""
    device_id = payload.get("ident", "unknown")

    fuel = payload.get("can.fuel.level")
    engine_temp = payload.get("can.engine.temperature")
    alarm = payload.get("alarm.event.id")
    speed = payload.get("position.speed", 0)

    alerts = []

    if fuel is not None and fuel < 10:
              alerts.append({"type": "LOW_FUEL", "severity": "HIGH", "value": fuel})

    if engine_temp is not None and engine_temp > 105:
              alerts.append({"type": "ENGINE_OVERHEAT", "severity": "CRITICAL", "value": engine_temp})

    if speed > 120:
              alerts.append({"type": "OVERSPEED", "severity": "HIGH", "value": speed})

    if alarm is not None and alarm != 0:
              alerts.append({"type": "DEVICE_ALARM", "severity": "HIGH", "alarm_code": alarm})

    for alert_data in alerts:
              logger.warning("Anomaly detected on device %s: %s", device_id, alert_data)
        # Persist alert to DB asynchronously
        await _create_alert(device_id, alert_data)


async def _create_alert(device_id: str, alert_data: dict) -> None:
      """Persist an anomaly alert to the alerts table."""
    try:
              from app.core.database import async_session_factory
        from app.models.alert import Alert

        alert = Alert(
                      device_id=device_id,
                      alert_type=alert_data.get("type", "UNKNOWN"),
                      severity=alert_data.get("severity", "MEDIUM"),
                      details=alert_data,
                      resolved=False,
        )
        async with async_session_factory() as db:
                      db.add(alert)
                      await db.commit()
except Exception as exc:
        logger.error("Failed to create alert: %s", exc)


async def run_ingestion() -> None:
      """
          Main MQTT ingestion loop.
              Subscribes to Flespi broker and processes incoming device messages.
                  Reconnects automatically on disconnect.
                      """
    try:
        from aiomqtt import Client as MQTTClient, MqttError
except ImportError:
        logger.error("aiomqtt not installed. Run: pip install aiomqtt")
        return

    while True:
              try:
                            logger.info("Connecting to Flespi MQTT broker at %s:%s", FLESPI_MQTT_HOST, FLESPI_MQTT_PORT)
                            async with MQTTClient(
                                              hostname=FLESPI_MQTT_HOST,
                                              port=FLESPI_MQTT_PORT,
                                              username=settings.FLESPI_TOKEN,
                                              password="",
                                              tls_context=None,   # aiomqtt auto-uses TLS on port 8883
                            ) as client:
                                              await client.subscribe(TOPIC)
                                              logger.info("Subscribed to topic: %s", TOPIC)

                                async for message in client.messages:
                                                      try:
                                                                                payload = json.loads(message.payload.decode("utf-8"))
                                                                                # Handle both single message and array of messages
                                                                                if isinstance(payload, list):
                                                                                                              for msg in payload:
                                                                                                                                                await asyncio.gather(
                                                                                                                                                                                      persist_telemetry(msg),
                                                                                                                                                                                      process_anomalies(msg),
                                                                                                                                                                                      return_exceptions=True,
                                                                                                                                                  )
                                                                                  else:
                            await asyncio.gather(
                                                              persist_telemetry(payload),
                                                              process_anomalies(payload),
                                                              return_exceptions=True,
                            )
except json.JSONDecodeError as exc:
                        logger.warning("Invalid JSON from MQTT: %s", exc)
except Exception as exc:
                        logger.error("Error processing MQTT message: %s", exc)

except Exception as exc:
            logger.error("MQTT connection error: %s. Reconnecting in 10s...", exc)
            await asyncio.sleep(10)


async def get_device_history(device_id: str, from_ts: int, to_ts: int) -> list:
      """
          Fetch historical device messages from Flespi REST API.
              Used for replay and gap-filling.
                  """
    import httpx

    url = f"https://flespi.io/gw/devices/{device_id}/messages"
    headers = {"Authorization": f"FlespiToken {settings.FLESPI_TOKEN}"}
    params = {"from": from_ts, "to": to_ts, "count": 1000}

    async with httpx.AsyncClient() as http:
              try:
                            r = await http.get(url, headers=headers, params=params, timeout=30)
                            r.raise_for_status()
                            data = r.json()
                            return data.get("result", [])
except Exception as exc:
            logger.error("Flespi REST API error: %s", exc)
            return []


if __name__ == "__main__":
      logging.basicConfig(level=logging.INFO)
    asyncio.run(run_ingestion())
