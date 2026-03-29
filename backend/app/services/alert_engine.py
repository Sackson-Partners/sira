"""
Automated Alert Derivation Engine
Rule-based system for generating alerts from events
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.alert import Alert
from app.models.movement import Movement

logger = logging.getLogger(__name__)


class AlertRule:
    """Base class for alert rules"""

    def __init__(
        self,
        rule_id: str,
        name: str,
        severity: str,
        domain: str,
        confidence: float = 0.8,
        sla_minutes: int = 60
    ):
        self.rule_id = rule_id
        self.name = name
        self.severity = severity
        self.domain = domain
        self.confidence = confidence
        self.sla_minutes = sla_minutes

    def evaluate(self, event: Event, context: Dict[str, Any]) -> bool:
        """Evaluate if rule should trigger. Override in subclasses."""
        raise NotImplementedError

    def generate_description(self, event: Event, context: Dict[str, Any]) -> str:
        """Generate alert description. Override in subclasses."""
        raise NotImplementedError


class SecurityEventRule(AlertRule):
    """Rule for security-type events"""

    def __init__(self):
        super().__init__(
            rule_id="RULE_SEC_001",
            name="Security Event Detection",
            severity="High",
            domain="Security",
            confidence=0.85,
            sla_minutes=30
        )

    def evaluate(self, event: Event, context: Dict[str, Any]) -> bool:
        return event.event_type == "security"

    def generate_description(self, event: Event, context: Dict[str, Any]) -> str:
        return f"Security event detected: {event.description or 'No description'} at {event.location or 'Unknown location'}"


class CriticalSeverityRule(AlertRule):
    """Rule for critical severity events"""

    def __init__(self):
        super().__init__(
            rule_id="RULE_SEV_001",
            name="Critical Severity Event",
            severity="Critical",
            domain="Operations",
            confidence=0.95,
            sla_minutes=15
        )

    def evaluate(self, event: Event, context: Dict[str, Any]) -> bool:
        return event.severity == "critical"

    def generate_description(self, event: Event, context: Dict[str, Any]) -> str:
        return f"Critical event: {event.description or 'Critical severity event detected'}"


class HighRiskZoneRule(AlertRule):
    """Rule for events in high-risk zones"""

    HIGH_RISK_ZONES = [
        "Red Sea", "Gulf of Aden", "Strait of Hormuz",
        "Gulf of Guinea", "Singapore Strait", "Malacca Strait"
    ]

    def __init__(self):
        super().__init__(
            rule_id="RULE_ZONE_001",
            name="High Risk Zone Alert",
            severity="High",
            domain="Maritime Security",
            confidence=0.8,
            sla_minutes=45
        )

    def evaluate(self, event: Event, context: Dict[str, Any]) -> bool:
        if not event.location:
            return False
        return any(
            zone.lower() in event.location.lower()
            for zone in self.HIGH_RISK_ZONES
        )

    def generate_description(self, event: Event, context: Dict[str, Any]) -> str:
        return f"Event in high-risk zone: {event.location}"


class DelayDetectionRule(AlertRule):
    """Rule for detecting delays"""

    def __init__(self):
        super().__init__(
            rule_id="RULE_DELAY_001",
            name="Movement Delay Detection",
            severity="Medium",
            domain="Operations",
            confidence=0.75,
            sla_minutes=120
        )

    def evaluate(self, event: Event, context: Dict[str, Any]) -> bool:
        movement = context.get("movement")
        if not movement:
            return False
        # Check if movement is past laycan_end
        now = datetime.now(timezone.utc)
        return (
            event.event_type == "operational" and
            movement.laycan_end < now and
            movement.status == "active"
        )

    def generate_description(self, event: Event, context: Dict[str, Any]) -> str:
        movement = context.get("movement")
        return f"Delay detected for movement {movement.id if movement else 'Unknown'}: Past laycan end date"


class AnomalyDetectionRule(AlertRule):
    """Rule for detecting anomalies in event patterns"""

    def __init__(self):
        super().__init__(
            rule_id="RULE_ANOM_001",
            name="Anomaly Detection",
            severity="Medium",
            domain="Intelligence",
            confidence=0.7,
            sla_minutes=60
        )
        self.keywords = [
            "suspicious", "unusual", "unexpected", "unauthorized",
            "unscheduled", "deviation", "anomaly", "threat"
        ]

    def evaluate(self, event: Event, context: Dict[str, Any]) -> bool:
        if not event.description:
            return False
        description_lower = event.description.lower()
        return any(keyword in description_lower for keyword in self.keywords)

    def generate_description(self, event: Event, context: Dict[str, Any]) -> str:
        return f"Potential anomaly detected: {event.description}"


class AlertDerivationEngine:
    """
    Engine for automatically deriving alerts from events.
    Uses a rule-based system with configurable rules.
    """

    def __init__(self, db: Session):
        self.db = db
        self.rules: List[AlertRule] = [
            SecurityEventRule(),
            CriticalSeverityRule(),
            HighRiskZoneRule(),
            DelayDetectionRule(),
            AnomalyDetectionRule(),
        ]
        logger.info(f"Alert Derivation Engine initialized with {len(self.rules)} rules")

    def add_rule(self, rule: AlertRule):
        """Add a custom rule to the engine"""
        self.rules.append(rule)
        logger.info(f"Added rule: {rule.name} ({rule.rule_id})")

    def remove_rule(self, rule_id: str):
        """Remove a rule by ID"""
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        logger.info(f"Removed rule: {rule_id}")

    def process_event(self, event: Event) -> List[Alert]:
        """
        Process an event and generate alerts based on rules.
        Returns list of created alerts.
        """
        created_alerts = []

        # Build context
        context = self._build_context(event)

        # Evaluate each rule
        for rule in self.rules:
            try:
                if rule.evaluate(event, context):
                    alert = self._create_alert(event, rule, context)
                    if alert:
                        created_alerts.append(alert)
                        logger.info(
                            f"Alert created: {alert.id} from rule {rule.rule_id}"
                        )
            except Exception as e:
                logger.error(
                    f"Error evaluating rule {rule.rule_id}: {e}"
                )

        return created_alerts

    def _build_context(self, event: Event) -> Dict[str, Any]:
        """Build context for rule evaluation"""
        context = {
            "timestamp": datetime.now(timezone.utc),
        }

        # Get movement if available
        if event.movement_id:
            movement = self.db.query(Movement).filter(
                Movement.id == event.movement_id
            ).first()
            context["movement"] = movement

            # Get recent events for the movement
            recent_events = self.db.query(Event).filter(
                Event.movement_id == event.movement_id,
                Event.timestamp >= datetime.now(timezone.utc) - timedelta(hours=24)
            ).order_by(Event.timestamp.desc()).limit(10).all()
            context["recent_events"] = recent_events

        return context

    def _create_alert(
        self,
        event: Event,
        rule: AlertRule,
        context: Dict[str, Any]
    ) -> Optional[Alert]:
        """Create an alert from a triggered rule"""
        try:
            # Check for duplicate alerts (same rule, same event, within 1 hour)
            existing = self.db.query(Alert).filter(
                Alert.event_id == event.id,
                Alert.rule_id == rule.rule_id,
                Alert.created_at >= datetime.now(timezone.utc) - timedelta(hours=1)
            ).first()

            if existing:
                logger.debug(f"Duplicate alert suppressed for rule {rule.rule_id}")
                return None

            alert = Alert(
                severity=rule.severity,
                confidence=rule.confidence,
                sla_timer=rule.sla_minutes,
                domain=rule.domain,
                site_zone=event.location,
                movement_id=event.movement_id,
                event_id=event.id,
                description=rule.generate_description(event, context),
                rule_id=rule.rule_id,
                rule_name=rule.name,
                status="open"
            )

            self.db.add(alert)
            self.db.commit()
            self.db.refresh(alert)

            return alert

        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            self.db.rollback()
            return None

    def check_sla_breaches(self) -> List[Alert]:
        """Check for SLA breaches and update alerts"""
        now = datetime.now(timezone.utc)
        breached_alerts = []

        # Find open alerts that might have breached SLA
        open_alerts = self.db.query(Alert).filter(
            Alert.status.in_(["open", "acknowledged"]),
            Alert.sla_breached == False,  # noqa: E712
            Alert.sla_timer.isnot(None)
        ).all()

        for alert in open_alerts:
            sla_deadline = alert.created_at + timedelta(minutes=alert.sla_timer)
            if now > sla_deadline:
                alert.sla_breached = True
                breached_alerts.append(alert)
                logger.warning(f"SLA breached for alert {alert.id}")

        if breached_alerts:
            self.db.commit()

        return breached_alerts

    def get_rule_stats(self) -> Dict[str, Any]:
        """Get statistics for each rule"""
        stats = {}
        for rule in self.rules:
            count = self.db.query(Alert).filter(
                Alert.rule_id == rule.rule_id
            ).count()
            stats[rule.rule_id] = {
                "name": rule.name,
                "severity": rule.severity,
                "domain": rule.domain,
                "total_alerts": count
            }
        return stats
