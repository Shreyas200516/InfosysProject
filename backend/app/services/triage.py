"""Priority prediction + severity scoring (wraps the team's severity_priority package)."""
from __future__ import annotations

import warnings
from functools import lru_cache
from typing import Any, Optional

from severity_priority.priority_severity_service import PrioritySeverityService

from ..config import settings


class TriageService:
    def __init__(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.svc = PrioritySeverityService(model_path=settings.priority_model_path)

    def evaluate(self, text: str, business_impact: Optional[str] = None, affected_users: Optional[int] = None,
                 service_criticality: Optional[str] = None) -> dict[str, Any]:
        r = self.svc.evaluate_ticket(text, business_impact=business_impact, affected_users=affected_users,
                                     service_criticality=service_criticality)
        inputs = r["severity"]["inputs"]
        return {
            "priority": r["priority"]["predicted_priority"],
            "priority_confidence": r["priority"]["confidence"],
            "priority_raw": r["priority"]["raw_model_prediction"],
            "priority_source": r["priority"]["model_source"],
            "severity": r["severity"]["level"],
            "severity_score": int(r["severity"]["score"]),
            "severity_confidence": r["severity"]["confidence"],
            "severity_reasoning": r["severity"]["reasoning"],
            "business_impact": inputs["business_impact"],
            "affected_users": int(inputs["affected_users"]),
            "service_tier": inputs["service_criticality"],
            "sla": r["sla"],
            "alignment_notes": r["alignment_notes"],
        }


@lru_cache(maxsize=1)
def get_triage() -> TriageService:
    return TriageService()
