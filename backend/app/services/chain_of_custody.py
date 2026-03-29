"""
Chain-of-Custody Service - Digital seals, audit trails, and verification

Provides tamper-evident chain-of-custody tracking for shipments with
digital signatures, optional blockchain notarization, and verification.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


class ChainOfCustodyService:
    """Manages chain-of-custody integrity for shipments."""

    def generate_seal_id(self, shipment_ref: str, seal_number: str) -> str:
        """Generate a unique digital seal ID."""
        data = f"{shipment_ref}:{seal_number}:{datetime.now(timezone.utc).isoformat()}"
        return f"SEAL-{hashlib.sha256(data.encode()).hexdigest()[:16].upper()}"

    def generate_digital_signature(self, event_data: Dict[str, Any]) -> str:
        """
        Generate a SHA-256 digital signature for a custody event.
        Creates a deterministic hash of the event data for tamper detection.
        """
        # Serialize with sorted keys for deterministic output
        serialized = json.dumps(event_data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def verify_signature(self, event_data: Dict[str, Any], expected_signature: str) -> bool:
        """Verify that event data matches its stored digital signature."""
        computed = self.generate_digital_signature(event_data)
        return computed == expected_signature

    def build_custody_chain(self, custody_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build a complete chain-of-custody report from custody events.

        Returns a structured report with chain integrity status.
        """
        if not custody_events:
            return {
                "chain_length": 0,
                "integrity": "empty",
                "gaps": [],
                "events": [],
            }

        # Sort events by timestamp
        sorted_events = sorted(custody_events, key=lambda e: e.get("timestamp", ""))

        # Check chain integrity
        gaps = []
        chain = []
        prev_to_party = None

        for i, event in enumerate(sorted_events):
            entry = {
                "sequence": i + 1,
                "event_type": event.get("event_type"),
                "timestamp": event.get("timestamp"),
                "location": event.get("location"),
                "from_party": event.get("from_party"),
                "to_party": event.get("to_party"),
                "seal_status": event.get("seal_status"),
                "volume_variance_pct": event.get("volume_variance_pct"),
                "has_signature": bool(event.get("digital_signature")),
            }

            # Check for custody gaps (to_party of prev != from_party of current)
            if prev_to_party and event.get("from_party"):
                if prev_to_party != event.get("from_party"):
                    gaps.append({
                        "between_events": [i, i + 1],
                        "expected_from": prev_to_party,
                        "actual_from": event.get("from_party"),
                        "message": f"Custody gap: expected handover from '{prev_to_party}' but received from '{event.get('from_party')}'",
                    })

            prev_to_party = event.get("to_party")
            chain.append(entry)

        # Check for seal integrity
        seal_issues = []
        for event in sorted_events:
            if event.get("seal_status") in ("broken", "tampered"):
                seal_issues.append({
                    "timestamp": event.get("timestamp"),
                    "location": event.get("location"),
                    "status": event.get("seal_status"),
                })

        # Check for volume discrepancies
        volume_issues = []
        for event in sorted_events:
            variance = event.get("volume_variance_pct")
            if variance is not None and abs(variance) > 2.0:
                volume_issues.append({
                    "timestamp": event.get("timestamp"),
                    "location": event.get("location"),
                    "variance_pct": variance,
                    "measured": event.get("measured_volume"),
                    "expected": event.get("expected_volume"),
                })

        # Overall integrity assessment
        if seal_issues or len(gaps) > 0 or any(abs(v.get("variance_pct", 0)) > 5 for v in volume_issues):
            integrity = "compromised"
        elif volume_issues:
            integrity = "warning"
        else:
            integrity = "intact"

        return {
            "chain_length": len(chain),
            "integrity": integrity,
            "gaps": gaps,
            "seal_issues": seal_issues,
            "volume_issues": volume_issues,
            "events": chain,
        }

    def generate_compliance_report(
        self,
        shipment_ref: str,
        custody_chain: Dict[str, Any],
        shipment_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate a compliance-ready chain-of-custody report.
        Suitable for insurance claims, regulatory audits, and dispute resolution.
        """
        return {
            "report_type": "chain_of_custody",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "shipment_ref": shipment_ref,
            "cargo_type": shipment_data.get("cargo_type"),
            "volume_tonnes": shipment_data.get("volume_tonnes"),
            "origin": shipment_data.get("origin"),
            "destination": shipment_data.get("destination"),
            "chain_integrity": custody_chain.get("integrity"),
            "total_custody_events": custody_chain.get("chain_length"),
            "custody_gaps": len(custody_chain.get("gaps", [])),
            "seal_issues": len(custody_chain.get("seal_issues", [])),
            "volume_discrepancies": len(custody_chain.get("volume_issues", [])),
            "events": custody_chain.get("events", []),
            "issues_summary": {
                "gaps": custody_chain.get("gaps", []),
                "seal_issues": custody_chain.get("seal_issues", []),
                "volume_issues": custody_chain.get("volume_issues", []),
            },
            "compliance_status": "pass" if custody_chain.get("integrity") == "intact" else "review_required",
        }


# Singleton instance
custody_service = ChainOfCustodyService()
