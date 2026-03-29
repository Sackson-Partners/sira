"""
ETA Prediction Service - Rule-based (Phase 1) with ML-ready architecture

Phase 1: Rule-based ETA prediction using historical averages, speed, distance, and port congestion
Phase 2+: Will integrate ML models (TensorFlow/PyTorch) for improved accuracy
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging
import math

logger = logging.getLogger(__name__)


class ETAPredictionService:
    """Predicts ETAs for multimodal shipments using rule-based heuristics (Phase 1)."""

    # Average speeds by mode (km/h or knots for vessels)
    DEFAULT_SPEEDS = {
        "vessel": 12.0,       # knots
        "truck": 40.0,        # km/h (African corridors average)
        "rail": 25.0,         # km/h
        "barge": 8.0,         # knots
    }

    # Average delays by factor (hours)
    DELAY_FACTORS = {
        "port_congestion_low": 0,
        "port_congestion_medium": 24,
        "port_congestion_high": 72,
        "weather_good": 0,
        "weather_moderate": 12,
        "weather_severe": 48,
        "document_complete": 0,
        "document_incomplete": 24,
        "customs_normal": 8,
        "customs_delayed": 48,
    }

    def predict_eta(
        self,
        current_lat: Optional[float],
        current_lng: Optional[float],
        dest_lat: float,
        dest_lng: float,
        mode: str = "vessel",
        current_speed: Optional[float] = None,
        port_congestion: str = "low",
        weather: str = "good",
        document_status: str = "complete",
        historical_avg_hours: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Predict ETA based on current position and conditions.

        Returns:
            dict with eta, confidence, factors, and variance_hours
        """
        now = datetime.now(timezone.utc)

        # Calculate distance
        if current_lat is not None and current_lng is not None:
            distance = self._haversine(current_lat, current_lng, dest_lat, dest_lng)
        else:
            # No current position - use historical average or default
            if historical_avg_hours:
                eta = now + timedelta(hours=historical_avg_hours)
                return {
                    "eta": eta,
                    "confidence": 0.4,
                    "variance_hours": historical_avg_hours * 0.3,
                    "factors": ["No position data, using historical average"],
                }
            return {
                "eta": None,
                "confidence": 0.0,
                "variance_hours": None,
                "factors": ["Insufficient data for prediction"],
            }

        # Calculate base transit time
        speed = current_speed or self.DEFAULT_SPEEDS.get(mode, 12.0)

        if mode in ("vessel", "barge"):
            # Convert nautical miles to hours
            distance_nm = distance * 0.539957  # km to nautical miles
            transit_hours = distance_nm / speed
        else:
            transit_hours = distance / speed

        # Apply delay factors
        factors = []
        total_delay = 0

        congestion_key = f"port_congestion_{port_congestion}"
        if congestion_key in self.DELAY_FACTORS:
            delay = self.DELAY_FACTORS[congestion_key]
            total_delay += delay
            if delay > 0:
                factors.append(f"Port congestion ({port_congestion}): +{delay}h")

        weather_key = f"weather_{weather}"
        if weather_key in self.DELAY_FACTORS:
            delay = self.DELAY_FACTORS[weather_key]
            total_delay += delay
            if delay > 0:
                factors.append(f"Weather ({weather}): +{delay}h")

        doc_key = f"document_{document_status}"
        if doc_key in self.DELAY_FACTORS:
            delay = self.DELAY_FACTORS[doc_key]
            total_delay += delay
            if delay > 0:
                factors.append(f"Documents ({document_status}): +{delay}h")

        total_hours = transit_hours + total_delay

        # Blend with historical average if available
        if historical_avg_hours:
            total_hours = total_hours * 0.6 + historical_avg_hours * 0.4
            factors.append("Blended with historical average")

        eta = now + timedelta(hours=total_hours)

        # Calculate confidence (higher when position is known and delays are low)
        confidence = 0.7
        if current_speed:
            confidence += 0.1  # Better confidence with actual speed
        if total_delay > 48:
            confidence -= 0.2  # Lower confidence with high delays
        if historical_avg_hours:
            confidence += 0.05

        confidence = max(0.1, min(1.0, confidence))

        # Variance increases with distance and delays
        variance_hours = transit_hours * 0.15 + total_delay * 0.3

        factors.insert(0, f"Distance: {distance:.0f}km, Speed: {speed:.1f}, Transit: {transit_hours:.1f}h")

        return {
            "eta": eta,
            "confidence": round(confidence, 2),
            "variance_hours": round(variance_hours, 1),
            "factors": factors,
        }

    def _haversine(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two points in km using haversine formula."""
        R = 6371  # Earth's radius in km

        lat1_r = math.radians(lat1)
        lat2_r = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c


# Singleton instance
eta_service = ETAPredictionService()
