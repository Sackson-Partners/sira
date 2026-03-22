"""
SIRA Platform - AI Prompt Library
Phase 2: Structured prompt templates for Claude API (primary) and OpenAI (fallback).
All prompts are versioned and auditable.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Prompt 1 — Delay Risk Assessment
# ---------------------------------------------------------------------------

DELAY_RISK_SYSTEM = (
    "You are SIRA, an AI logistics intelligence engine for Energie Partners. "
    "You analyse telematics, port, and market data to produce concise, actionable "
    "risk assessments. Respond ONLY with valid JSON matching this schema: "
    '{"risk_level": "LOW|MEDIUM|HIGH|CRITICAL", '
    '"delay_hours_estimate": <float>, '
    '"root_causes": [<string>], '
    '"recommendations": [<string>]}'
)

DELAY_RISK_USER = """Shipment: {shipment_id}  |  Cargo: {cargo_type}  |  Route: {origin} -> {destination}
Truck telemetry: speed={speed} km/h, fuel={fuel_pct}%, engine_temp={engine_temp}C
Last position: {lat},{lon} at {timestamp}  |  Distance remaining: {distance_km}km
Port congestion index: {port_congestion}/10  |  Weather: {weather_summary}
Market urgency: {market_urgency}  |  Historical delay avg: {avg_delay_mins}min
Assess delay risk and provide actionable recommendations."""


# ---------------------------------------------------------------------------
# Prompt 2 — Predictive Maintenance Alert
# ---------------------------------------------------------------------------

MAINTENANCE_SYSTEM = (
    "You are a predictive maintenance AI for a logistics fleet managed by Energie Partners. "
    "Analyse sensor trends and produce a maintenance forecast. "
    "Respond ONLY with valid JSON matching this schema: "
    '{"urgency": "LOW|MEDIUM|HIGH|CRITICAL", '
    '"predicted_failure_type": <string>, '
    '"days_to_failure": <int>, '
    '"action_required": <string>}'
)

MAINTENANCE_USER = """Vehicle: {vehicle_id}  |  Type: {vehicle_type}  |  Mileage: {odometer}km
Last service: {last_service_date} ({service_km}km ago)
Sensor 7-day trend: engine_temp={temp_trend}, fuel_consumption={fuel_trend}
Fault codes: {fault_codes}  |  Idle time: {idle_hours}h/week
Predict maintenance needs and urgency."""


# ---------------------------------------------------------------------------
# Prompt 3 — Market Intelligence Synthesis
# ---------------------------------------------------------------------------

MARKET_INTEL_SYSTEM = (
    "You are a commodity and logistics market analyst for Energie Partners. "
    "Synthesise market signals into a strategic dispatch recommendation. "
    "Respond ONLY with valid JSON matching this schema: "
    '{"signal_summary": <string>, '
    '"recommendation": "DISPATCH_NOW|HOLD|PARTIAL_DISPATCH", '
    '"optimal_dispatch_window": <string>, '
    '"risk_factors": [<string>]}'
)

MARKET_INTEL_USER = """Commodity: {commodity_type}  |  Quantity pending: {quantity_tonnes}t
Spot price: {price}/t (7d change: {price_change}%)  |  Fuel index: {fuel_price}
Port congestion (destination): {congestion_index}/10
Buyer demand signal: {demand_signal}  |  Competitor activity: {competitor_intel}
Should we dispatch now or hold? Provide strategic recommendation."""


# ---------------------------------------------------------------------------
# Prompt 4 — Anomaly Explanation
# ---------------------------------------------------------------------------

ANOMALY_SYSTEM = (
    "You are a logistics security and safety AI for Energie Partners. "
    "Analyse the anomaly detected in vehicle telemetry and explain its likely cause. "
    "Respond ONLY with valid JSON: "
    '{"anomaly_type": <string>, "likely_cause": <string>, '
    '"risk_assessment": "LOW|MEDIUM|HIGH|CRITICAL", "recommended_action": <string>}'
)

ANOMALY_USER = """Vehicle: {vehicle_id}  |  Alert type: {alert_type}
Telemetry at anomaly: lat={lat}, lon={lon}, speed={speed}km/h
Fuel drop: {fuel_drop}%  |  Engine temp: {engine_temp}C
Expected route: {expected_route}  |  Actual position: {actual_position}
Context: {context}
Analyse and explain this anomaly."""


# ---------------------------------------------------------------------------
# Prompt 5 — Driver Coaching
# ---------------------------------------------------------------------------

DRIVER_COACHING_SYSTEM = (
    "You are a fleet safety coach for Energie Partners. "
    "Generate concise, constructive driving improvement tips. "
    "Respond with a JSON object: "
    '{"score": <int 0-100>, "strengths": [<string>], "improvements": [<string>], '
    '"coaching_message": <string>}'
)

DRIVER_COACHING_USER = """Driver: {driver_id}  |  Period: last {days} days
Harsh braking events: {harsh_braking}  |  Harsh acceleration: {harsh_accel}
Speeding events: {speeding_events}  |  Idle time: {idle_pct}%
Fuel efficiency: {fuel_efficiency} L/100km  |  On-time delivery: {on_time_pct}%
Generate personalised coaching feedback."""


# ---------------------------------------------------------------------------
# Convenience mapping
# ---------------------------------------------------------------------------

PROMPTS = {
    "delay_risk": {"system": DELAY_RISK_SYSTEM, "user": DELAY_RISK_USER},
    "maintenance": {"system": MAINTENANCE_SYSTEM, "user": MAINTENANCE_USER},
    "market_intel": {"system": MARKET_INTEL_SYSTEM, "user": MARKET_INTEL_USER},
    "anomaly": {"system": ANOMALY_SYSTEM, "user": ANOMALY_USER},
    "driver_coaching": {"system": DRIVER_COACHING_SYSTEM, "user": DRIVER_COACHING_USER},
}

__all__ = [
    "DELAY_RISK_SYSTEM", "DELAY_RISK_USER",
    "MAINTENANCE_SYSTEM", "MAINTENANCE_USER",
    "MARKET_INTEL_SYSTEM", "MARKET_INTEL_USER",
    "ANOMALY_SYSTEM", "ANOMALY_USER",
    "DRIVER_COACHING_SYSTEM", "DRIVER_COACHING_USER",
    "PROMPTS",
]
