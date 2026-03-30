"""
AI Intelligence Engine Service
Provides AI-powered analytics using Claude (Anthropic) or OpenAI.
Capabilities: ETA prediction, risk scoring, anomaly detection, natural language queries.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIEngine:
    """AI Intelligence Engine for SIRA Platform."""

    SYSTEM_PROMPT = """You are SIRA AI, the intelligence engine for the SIRA Platform
(Shipping Intelligence & Risk Analytics). You help logistics operators with:
- ETA predictions and delay analysis
- Demurrage risk scoring and cost estimation
- Anomaly detection in vessel/fleet telemetry
- Supply chain optimization recommendations
- Natural language queries about shipments, vessels, ports, and fleet

Always provide concise, actionable insights. Use data-driven reasoning.
When uncertain, state your confidence level. Format responses with clear sections."""

    def __init__(self):
        self._anthropic_client = None
        self._openai_client = None

    @property
    def is_configured(self) -> bool:
        return bool(settings.ANTHROPIC_API_KEY or settings.OPENAI_API_KEY)

    def _get_anthropic_client(self):
        if self._anthropic_client is None and settings.ANTHROPIC_API_KEY:
            import anthropic
            self._anthropic_client = anthropic.Anthropic(
                api_key=settings.ANTHROPIC_API_KEY
            )
        return self._anthropic_client

    def _get_openai_client(self):
        if self._openai_client is None and settings.OPENAI_API_KEY:
            import openai
            self._openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai_client

    async def chat(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Send a message to the AI engine and get a response."""
        if not self.is_configured:
            return "AI Engine is not configured. Please set ANTHROPIC_API_KEY or OPENAI_API_KEY."

        system = self.SYSTEM_PROMPT
        if context:
            system += f"\n\nCurrent context:\n{json.dumps(context, default=str, indent=2)}"

        messages = []
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})

        # Prefer Anthropic (Claude)
        if settings.ANTHROPIC_API_KEY:
            return await self._chat_anthropic(system, messages)
        elif settings.OPENAI_API_KEY:
            return await self._chat_openai(system, messages)
        return "No AI provider configured."

    async def _chat_anthropic(
        self, system: str, messages: List[Dict[str, str]]
    ) -> str:
        """Chat using Anthropic Claude API."""
        try:
            client = self._get_anthropic_client()
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.messages.create(
                    model=settings.AI_MODEL,
                    max_tokens=settings.AI_MAX_TOKENS,
                    system=system,
                    messages=messages,
                ),
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return f"AI Engine error: {str(e)}"

    async def _chat_openai(self, system: str, messages: List[Dict[str, str]]) -> str:
        """Chat using OpenAI API."""
        try:
            client = self._get_openai_client()
            oai_messages = [{"role": "system", "content": system}] + messages
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model="gpt-4o",
                    max_tokens=settings.AI_MAX_TOKENS,
                    messages=oai_messages,
                ),
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return f"AI Engine error: {str(e)}"

    async def analyze_shipment_risk(
        self, shipment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze risk for a specific shipment."""
        prompt = f"""Analyze the following shipment and provide:
1. Risk score (0-100)
2. Key risk factors
3. Recommended actions
4. Estimated delay probability

Shipment data:
{json.dumps(shipment_data, default=str, indent=2)}"""

        response = await self.chat(prompt)
        return {
            "shipment_id": shipment_data.get("id"),
            "analysis": response,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def predict_eta(
        self,
        origin: str,
        destination: str,
        departure_time: str,
        vessel_speed: Optional[float] = None,
        weather_conditions: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Predict ETA for a voyage."""
        prompt = f"""Predict the ETA for this voyage:
- Origin: {origin}
- Destination: {destination}
- Departure: {departure_time}
- Vessel speed: {vessel_speed or 'unknown'} knots
- Weather: {weather_conditions or 'normal'}

Provide:
1. Estimated arrival time
2. Confidence level (%)
3. Key factors affecting the estimate
4. Potential delay scenarios"""

        response = await self.chat(prompt)
        return {
            "origin": origin,
            "destination": destination,
            "prediction": response,
            "predicted_at": datetime.now(timezone.utc).isoformat(),
        }

    async def analyze_demurrage_risk(
        self, vessel_data: Dict[str, Any], port_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze demurrage risk for a vessel at a port."""
        prompt = f"""Analyze demurrage risk:

Vessel: {json.dumps(vessel_data, default=str)}
Port: {json.dumps(port_data, default=str)}

Provide:
1. Demurrage risk score (0-100)
2. Estimated wait time
3. Cost exposure estimate
4. Recommendations to minimize demurrage"""

        response = await self.chat(prompt)
        return {
            "vessel": vessel_data.get("name"),
            "port": port_data.get("name"),
            "analysis": response,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def detect_anomalies(
        self, telemetry_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Detect anomalies in telemetry data."""
        prompt = f"""Analyze this telemetry data for anomalies:

{json.dumps(telemetry_data[:50], default=str, indent=2)}

Identify:
1. Any unusual patterns (speed, route deviations, stops)
2. Potential security concerns
3. Equipment issues suggested by the data
4. Confidence level for each finding"""

        response = await self.chat(prompt)
        return {
            "data_points": len(telemetry_data),
            "analysis": response,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }


# Singleton instance
ai_engine = AIEngine()
