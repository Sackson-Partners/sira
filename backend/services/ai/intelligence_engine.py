"""
SIRA Platform - AI Intelligence Engine
Phase 2: Claude API (primary) + OpenAI (fallback) for predictive analytics,
anomaly detection, maintenance prediction, and market intelligence.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt Library
# ---------------------------------------------------------------------------

DELAY_RISK_SYSTEM = (
      "You are SIRA, an AI logistics intelligence engine. You analyse telematics, "
      "port, and market data to produce concise, actionable risk assessments. "
      "Respond ONLY with valid JSON: "
      "{\"risk_level\": \"LOW|MEDIUM|HIGH|CRITICAL\", "
      "\"delay_hours_estimate\": <float>, "
      "\"root_causes\": [<string>], "
      "\"recommendations\": [<string>]}"
)

DELAY_RISK_USER = """Shipment: {shipment_id}  |  Cargo: {cargo_type}  |  Route: {origin} -> {destination}
Truck telemetry: speed={speed}km/h, fuel={fuel_pct}%, engine_temp={engine_temp}C
Last position: {lat},{lon} at {timestamp}  |  Distance remaining: {distance_km}km
Port congestion index: {port_congestion}/10  |  Weather: {weather_summary}
Market urgency: {market_urgency}  |  Historical delay avg: {avg_delay_mins}min
Assess delay risk and provide actionable recommendations."""

MAINTENANCE_SYSTEM = (
      "You are a predictive maintenance AI for a logistics fleet. Analyse sensor trends. "
      "Respond ONLY with valid JSON: "
      "{\"urgency\": \"LOW|MEDIUM|HIGH|CRITICAL\", "
      "\"predicted_failure_type\": <string>, "
      "\"days_to_failure\": <int>, "
      "\"action_required\": <string>}"
)

MAINTENANCE_USER = """Vehicle: {vehicle_id}  |  Type: {vehicle_type}  |  Mileage: {odometer}km
Last service: {last_service_date} ({service_km}km ago)
Sensor 7-day trend: engine_temp={temp_trend}, fuel_consumption={fuel_trend}
Fault codes: {fault_codes}  |  Idle time: {idle_hours}h/week
Predict maintenance needs and urgency."""

MARKET_INTEL_SYSTEM = (
      "You are a commodity and logistics market analyst. Synthesise market signals into "
      "a strategic recommendation. Respond ONLY with valid JSON: "
      "{\"signal_summary\": <string>, "
      "\"recommendation\": \"DISPATCH_NOW|HOLD|PARTIAL_DISPATCH\", "
      "\"optimal_dispatch_window\": <string>, "
      "\"risk_factors\": [<string>]}"
)

MARKET_INTEL_USER = """Commodity: {commodity_type}  |  Quantity pending: {quantity_tonnes}t
Spot price: {price}/t (7d change: {price_change}%)  |  Fuel index: {fuel_price}
Port congestion (destination): {congestion_index}/10
Buyer demand signal: {demand_signal}  |  Competitor activity: {competitor_intel}
Should we dispatch now or hold? Provide strategic recommendation."""

ROUTE_OPT_SYSTEM = (
      "You are a logistics route optimisation AI. Given vehicle telemetry and route constraints, "
      "recommend the optimal route. Respond ONLY with valid JSON: "
      "{\"recommended_route\": <string>, "
      "\"estimated_saving_km\": <float>, "
      "\"estimated_saving_minutes\": <float>, "
      "\"waypoints\": [<string>], "
      "\"warnings\": [<string>]}"
)

DRIVER_COACHING_SYSTEM = (
      "You are a driver performance coach for a commercial fleet. Analyse driving data "
      "and provide concise, constructive coaching. Respond ONLY with valid JSON: "
      "{\"performance_score\": <int 0-100>, "
      "\"strengths\": [<string>], "
      "\"improvement_areas\": [<string>], "
      "\"coaching_tips\": [<string>]}"
)


# ---------------------------------------------------------------------------
# Claude API client
# ---------------------------------------------------------------------------

async def _call_claude(system: str, user: str, max_tokens: int = 1024) -> Optional[dict]:
      """Call Claude claude-3-5-sonnet and return parsed JSON response."""
      try:
                import anthropic
                client = anthropic.AsyncAnthropic(api_key=settings.CLAUDE_API_KEY)
                message = await client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                text = message.content[0].text.strip()
                # Strip markdown code blocks if present
                if text.startswith("```"):
                              text = text.split("```")[1]
                              if text.startswith("json"):
                                                text = text[4:]
                                        return json.loads(text)
      except json.JSONDecodeError as exc:
                logger.error("Claude returned non-JSON response: %s", exc)
                return None
except Exception as exc:
        logger.warning("Claude API error: %s — trying OpenAI fallback", exc)
        return None


async def _call_openai(system: str, user: str, max_tokens: int = 1024) -> Optional[dict]:
      """Fallback: call OpenAI gpt-4o and return parsed JSON response."""
      try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                text = response.choices[0].message.content or "{}"
                return json.loads(text)
except Exception as exc:
        logger.error("OpenAI fallback also failed: %s", exc)
        return None


async def _ai_query(system: str, user: str, max_tokens: int = 1024) -> Optional[dict]:
      """
          Try Claude first; fall back to OpenAI if Claude fails.
              """
      result = await _call_claude(system, user, max_tokens)
      if result is None:
                result = await _call_openai(system, user, max_tokens)
            return result


# ---------------------------------------------------------------------------
# Public AI capabilities
# ---------------------------------------------------------------------------

async def assess_delay_risk(shipment_context: dict) -> Optional[dict]:
      """
          Predict shipment delay risk and recommendations.

              :param shipment_context: Dict matching DELAY_RISK_USER template fields.
                  :returns: {risk_level, delay_hours_estimate, root_causes, recommendations}
                      """
    try:
              user_prompt = DELAY_RISK_USER.format(**{
                            "shipment_id": shipment_context.get("shipment_id", "UNKNOWN"),
                            "cargo_type": shipment_context.get("cargo_type", "General"),
                            "origin": shipment_context.get("origin", "N/A"),
                            "destination": shipment_context.get("destination", "N/A"),
                            "speed": shipment_context.get("speed", 0),
                            "fuel_pct": shipment_context.get("fuel_pct", 100),
                            "engine_temp": shipment_context.get("engine_temp", 80),
                            "lat": shipment_context.get("lat", 0),
                            "lon": shipment_context.get("lon", 0),
                            "timestamp": shipment_context.get("timestamp", "N/A"),
                            "distance_km": shipment_context.get("distance_km", 0),
                            "port_congestion": shipment_context.get("port_congestion", 5),
                            "weather_summary": shipment_context.get("weather_summary", "Clear"),
                            "market_urgency": shipment_context.get("market_urgency", "Normal"),
                            "avg_delay_mins": shipment_context.get("avg_delay_mins", 0),
              })
              return await _ai_query(DELAY_RISK_SYSTEM, user_prompt)
except Exception as exc:
        logger.error("assess_delay_risk failed: %s", exc)
        return None


async def predict_maintenance(vehicle_context: dict) -> Optional[dict]:
      """
          Predict vehicle maintenance needs from sensor trend data.

              :param vehicle_context: Dict matching MAINTENANCE_USER template fields.
                  :returns: {urgency, predicted_failure_type, days_to_failure, action_required}
                      """
    try:
              user_prompt = MAINTENANCE_USER.format(**{
                            "vehicle_id": vehicle_context.get("vehicle_id", "UNKNOWN"),
                            "vehicle_type": vehicle_context.get("vehicle_type", "Truck"),
                            "odometer": vehicle_context.get("odometer", 0),
                            "last_service_date": vehicle_context.get("last_service_date", "Unknown"),
                            "service_km": vehicle_context.get("service_km", 0),
                            "temp_trend": vehicle_context.get("temp_trend", "Stable"),
                            "fuel_trend": vehicle_context.get("fuel_trend", "Stable"),
                            "fault_codes": vehicle_context.get("fault_codes", "None"),
                            "idle_hours": vehicle_context.get("idle_hours", 0),
              })
              return await _ai_query(MAINTENANCE_SYSTEM, user_prompt)
except Exception as exc:
        logger.error("predict_maintenance failed: %s", exc)
        return None


async def market_intelligence(market_context: dict) -> Optional[dict]:
      """
          Synthesise commodity market signals into dispatch recommendation.

              :param market_context: Dict matching MARKET_INTEL_USER template fields.
                  :returns: {signal_summary, recommendation, optimal_dispatch_window, risk_factors}
                      """
    try:
              user_prompt = MARKET_INTEL_USER.format(**{
                            "commodity_type": market_context.get("commodity_type", "Oil"),
                            "quantity_tonnes": market_context.get("quantity_tonnes", 0),
                            "price": market_context.get("price", 0),
                            "price_change": market_context.get("price_change", 0),
                            "fuel_price": market_context.get("fuel_price", 0),
                            "congestion_index": market_context.get("congestion_index", 5),
                            "demand_signal": market_context.get("demand_signal", "Neutral"),
                            "competitor_intel": market_context.get("competitor_intel", "No data"),
              })
              return await _ai_query(MARKET_INTEL_SYSTEM, user_prompt, max_tokens=2048)
except Exception as exc:
        logger.error("market_intelligence failed: %s", exc)
        return None


async def flag_anomalies(telemetry: dict) -> list[dict]:
      """
          Rule-based anomaly detection with AI interpretation for edge cases.
              Returns a list of anomaly dicts to be persisted as alerts.
                  """
    anomalies = []

    fuel = telemetry.get("can.fuel.level") or telemetry.get("fuel_level")
    temp = telemetry.get("can.engine.temperature") or telemetry.get("engine_temp")
    speed = telemetry.get("position.speed") or telemetry.get("speed", 0)

    if fuel is not None and fuel < 10:
              anomalies.append({"type": "LOW_FUEL", "severity": "HIGH", "value": fuel})

    if temp is not None and temp > 105:
              anomalies.append({"type": "ENGINE_OVERHEAT", "severity": "CRITICAL", "value": temp})

    if speed > 120:
              anomalies.append({"type": "OVERSPEED", "severity": "HIGH", "value": speed})

    return anomalies


async def generate_fleet_report(fleet_summary: dict) -> Optional[str]:
      """
          Generate a natural-language daily fleet performance report.
              Returns a Markdown-formatted string.
                  """
    system = (
              "You are a fleet operations analyst for SIRA. Generate a concise daily fleet "
              "performance report in Markdown format based on the provided summary data. "
              "Include: Executive Summary, Key Metrics, Alerts & Issues, Recommendations."
    )
    user = f"Fleet summary data:\n{json.dumps(fleet_summary, indent=2)}"
    try:
              import anthropic
              client = anthropic.AsyncAnthropic(api_key=settings.CLAUDE_API_KEY)
              message = await client.messages.create(
                  model="claude-3-5-sonnet-20241022",
                  max_tokens=2048,
                  system=system,
                  messages=[{"role": "user", "content": user}],
              )
              return message.content[0].text
except Exception as exc:
        logger.error("generate_fleet_report failed: %s", exc)
        return None


async def coach_driver(driver_data: dict) -> Optional[dict]:
      """
          Analyse a driver's performance data and generate coaching tips.
              """
    user = (
              f"Driver ID: {driver_data.get('driver_id')}\n"
              f"Trip data (7 days):\n{json.dumps(driver_data, indent=2)}"
    )
    return await _ai_query(DRIVER_COACHING_SYSTEM, user)
