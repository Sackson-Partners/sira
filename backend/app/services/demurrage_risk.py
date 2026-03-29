"""
Demurrage Risk Scoring Service

Predicts demurrage risk for shipments based on multiple factors.
Phase 1: Rule-based scoring
Phase 2+: ML-powered with historical training data
"""

from datetime import datetime
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DemurrageRiskService:
    """Scores demurrage risk on a 0-100 scale with financial exposure estimates."""

    # Risk weights for each factor (sum to 1.0)
    FACTOR_WEIGHTS = {
        "eta_variance": 0.25,
        "port_congestion": 0.20,
        "document_readiness": 0.15,
        "berth_availability": 0.15,
        "weather_risk": 0.10,
        "counterparty_history": 0.10,
        "laycan_proximity": 0.05,
    }

    def calculate_risk_score(
        self,
        eta_confidence: Optional[float] = None,
        eta_variance_hours: Optional[float] = None,
        port_congestion_level: str = "low",
        documents_complete_pct: float = 100.0,
        berth_available: bool = True,
        weather_severity: str = "good",
        counterparty_delay_history_pct: float = 0.0,
        laycan_end: Optional[datetime] = None,
        eta_destination: Optional[datetime] = None,
        demurrage_rate_usd: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculate demurrage risk score and financial exposure.

        Returns:
            dict with risk_score (0-100), exposure_usd, factors, and recommendations
        """
        factors = {}
        recommendations = []

        # 1. ETA Variance risk (higher variance = higher risk)
        if eta_variance_hours is not None:
            if eta_variance_hours <= 4:
                factors["eta_variance"] = 10
            elif eta_variance_hours <= 8:
                factors["eta_variance"] = 30
            elif eta_variance_hours <= 24:
                factors["eta_variance"] = 60
            elif eta_variance_hours <= 48:
                factors["eta_variance"] = 80
            else:
                factors["eta_variance"] = 95
                recommendations.append("ETA highly uncertain - consider laycan extension negotiation")
        else:
            factors["eta_variance"] = 50  # Unknown = moderate risk

        # 2. Port congestion
        congestion_scores = {"low": 10, "medium": 50, "high": 85}
        factors["port_congestion"] = congestion_scores.get(port_congestion_level, 50)
        if port_congestion_level == "high":
            recommendations.append("Port heavily congested - evaluate alternative berths or anchorage")

        # 3. Document readiness
        if documents_complete_pct >= 95:
            factors["document_readiness"] = 5
        elif documents_complete_pct >= 80:
            factors["document_readiness"] = 30
        elif documents_complete_pct >= 60:
            factors["document_readiness"] = 60
            recommendations.append("Expedite document completion to avoid clearance delays")
        else:
            factors["document_readiness"] = 90
            recommendations.append("URGENT: Documents significantly incomplete - risk of clearance hold")

        # 4. Berth availability
        factors["berth_availability"] = 10 if berth_available else 75
        if not berth_available:
            recommendations.append("No berth currently available - pre-book or negotiate priority")

        # 5. Weather risk
        weather_scores = {"good": 5, "moderate": 35, "severe": 80}
        factors["weather_risk"] = weather_scores.get(weather_severity, 35)
        if weather_severity == "severe":
            recommendations.append("Severe weather expected - factor delays into planning")

        # 6. Counterparty delay history
        if counterparty_delay_history_pct <= 10:
            factors["counterparty_history"] = 10
        elif counterparty_delay_history_pct <= 30:
            factors["counterparty_history"] = 40
        else:
            factors["counterparty_history"] = 70
            recommendations.append("Counterparty has history of delays - add buffer time")

        # 7. Laycan proximity
        if laycan_end and eta_destination:
            hours_to_laycan = (laycan_end - eta_destination).total_seconds() / 3600
            if hours_to_laycan > 72:
                factors["laycan_proximity"] = 5
            elif hours_to_laycan > 24:
                factors["laycan_proximity"] = 30
            elif hours_to_laycan > 0:
                factors["laycan_proximity"] = 65
                recommendations.append("Approaching laycan deadline - monitor closely")
            else:
                factors["laycan_proximity"] = 95
                recommendations.append("PAST LAYCAN - demurrage may already be accruing")
        else:
            factors["laycan_proximity"] = 40

        # Calculate weighted risk score
        risk_score = 0
        for factor, weight in self.FACTOR_WEIGHTS.items():
            risk_score += factors.get(factor, 50) * weight

        risk_score = round(min(100, max(0, risk_score)), 1)

        # Calculate financial exposure
        exposure_usd = 0.0
        expected_delay_days = 0.0
        if risk_score >= 30 and demurrage_rate_usd:
            # Estimate expected delay based on risk
            if risk_score >= 80:
                expected_delay_days = 5.0
            elif risk_score >= 60:
                expected_delay_days = 3.0
            elif risk_score >= 40:
                expected_delay_days = 1.5
            else:
                expected_delay_days = 0.5

            exposure_usd = round(expected_delay_days * demurrage_rate_usd, 2)

        # Risk level label
        if risk_score >= 80:
            risk_level = "critical"
        elif risk_score >= 60:
            risk_level = "high"
        elif risk_score >= 40:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "exposure_usd": exposure_usd,
            "expected_delay_days": expected_delay_days,
            "factors": factors,
            "recommendations": recommendations,
        }


# Singleton instance
demurrage_risk_service = DemurrageRiskService()
