"""
Defines Severity Levels (Critical, High, Medium, Low) and evaluates business impact,
affected user counts, and service criticality tiers to compute standard ITIL severity scores.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
import re


class SeverityLevel(str, Enum):
    CRITICAL = "Critical"  # Sev-1: Catastrophic business outage or security crisis
    HIGH = "High"  # Sev-2: Major business disruption with wide impact
    MEDIUM = "Medium"  # Sev-3: Moderate localized issue with viable workaround
    LOW = "Low"  # Sev-4: Minor issue, single user, or general inquiry


class BusinessImpact(str, Enum):
    EXTREME = "critical"  # Production stopped, financial loss, regulatory/legal risk
    HIGH = "high"  # Major operational impairment, significant delays
    MEDIUM = "medium"  # Moderate inconvenience, operational workaround exists
    LOW = "low"  # Minimal impact, cosmetic, informational, or query


class ServiceCriticality(str, Enum):
    TIER_1 = "tier_1"  # Mission-Critical (Production DB, Payment Gateway, Core SSO, WAN/Firewall)
    TIER_2 = (
        "tier_2"  # Business-Operational (ERP, CRM, Corporate Email, CI/CD, Payroll)
    )
    TIER_3 = "tier_3"  # Productivity & Administrative (Local Printers, Peripherals, Standard Dev Tools)
    TIER_4 = "tier_4"  # Non-Essential (Intranet links, accessories, staging sandboxes)


class SeverityScoringEngine:
    """
    ITIL-compliant Severity Scoring Engine that evaluates:
    1. Business Impact level
    2. Number of Affected Users
    3. Service Criticality Tier
    4. Heuristic urgency triggers in ticket content
    """

    # ITIL SLA Guidelines for SupportPilot
    SLA_MATRIX = {
        SeverityLevel.CRITICAL: {
            "initial_response_mins": 15,
            "target_resolution_hours": 2,
            "escalation_path": "Immediate PagerDuty On-Call + Incident Commander + VP Alert",
            "communication_cadence_mins": 30,
        },
        SeverityLevel.HIGH: {
            "initial_response_mins": 60,
            "target_resolution_hours": 6,
            "escalation_path": "Senior Technical Specialist + Operations Team Lead",
            "communication_cadence_mins": 120,
        },
        SeverityLevel.MEDIUM: {
            "initial_response_mins": 240,  # 4 hours
            "target_resolution_hours": 24,
            "escalation_path": "Standard Tier-2 Queue Assignment",
            "communication_cadence_mins": 480,
        },
        SeverityLevel.LOW: {
            "initial_response_mins": 480,  # 8 hours
            "target_resolution_hours": 72,
            "escalation_path": "General Support Queue / Self-Service Knowledge Base",
            "communication_cadence_mins": 1440,
        },
    }

    # High-risk trigger patterns that force immediate rule escalation
    CRITICAL_URGENCY_REGEX = re.compile(
        r"\b(ransomware|data breach|exfiltration|ddos|zero-day|total outage|blackout|hospital|patient|emergency|crashloop|500 error|production down|checkout down)\b|"
        r"\b(whole company|entire company|company[- ]wide|firm[- ]wide|all employees|all users|all staff|global)\b.*\b(down|outage|offline|unreachable|broken|crash|failing)\b|"
        r"\b(down|outage|offline|unreachable|broken|crash|failing)\b.*\b(whole company|entire company|company[- ]wide|firm[- ]wide|all employees|all users|all staff)\b|"
        r"\b(vpn is down|network is down|network down|internet is down|servers? (?:is|are) down|database down)\b",
        re.IGNORECASE,
    )

    HIGH_URGENCY_REGEX = re.compile(
        r"\b(payroll|freeze|cfo|board meeting|blocked|out of disk|rebooting|delayed|sync broken|vpn concentrator|staging down|vpn down|cannot connect)\b",
        re.IGNORECASE,
    )

    def __init__(self):
        pass

    def _normalize_business_impact(self, val: str) -> BusinessImpact:
        val = str(val).lower().strip()
        if val in ["critical", "extreme", "severe", "catastrophic", "blocker"]:
            return BusinessImpact.EXTREME
        elif val in ["high", "major", "significant"]:
            return BusinessImpact.HIGH
        elif val in ["medium", "moderate", "normal"]:
            return BusinessImpact.MEDIUM
        return BusinessImpact.LOW

    def _normalize_service_criticality(self, val: str) -> ServiceCriticality:
        val = str(val).lower().strip()
        if "1" in val or "mission" in val or "core" in val or "prod" in val:
            return ServiceCriticality.TIER_1
        elif "2" in val or "operation" in val or "business" in val:
            return ServiceCriticality.TIER_2
        elif "3" in val or "productivity" in val or "standard" in val:
            return ServiceCriticality.TIER_3
        return ServiceCriticality.TIER_4

    def infer_parameters_from_text(self, text: str) -> Dict[str, Any]:
        """
        Intelligently infers business_impact, affected_users, and service_criticality
        directly from ticket text when they are not explicitly provided by the user.
        """
        lower = text.lower() if text else ""

        # 1. Infer Affected Users
        users = 1
        user_match = re.search(
            r"(\d+)\s*(?:users|people|employees|clients|workers|engineers|staff)", lower
        )
        if user_match:
            try:
                users = int(user_match.group(1))
            except ValueError:
                pass
        elif any(
            w in lower
            for w in [
                "whole company",
                "entire company",
                "company-wide",
                "company wide",
                "all employees",
                "all staff",
                "all users",
                "across the company",
                "firm-wide",
                "global outage",
                "everyone",
                "whole office",
                "entire organization",
            ]
        ):
            users = 1000
        elif any(
            w in lower
            for w in [
                "entire department",
                "entire team",
                "all engineers",
                "branch office",
                "whole team",
            ]
        ):
            users = 50

        # 2. Infer Service Criticality Tier
        is_company_wide = users >= 200
        if any(
            w in lower
            for w in [
                "production",
                "prod db",
                "database cluster",
                "payment",
                "checkout",
                "gateway",
                "firewall",
                "datacenter",
                "data center",
                "core sso",
                "wan",
                "active directory",
                "telemetry",
                "kubernetes prod",
                "main cluster",
                "pos",
            ]
        ) or (
            is_company_wide
            and any(w in lower for w in ["vpn", "network", "internet", "wifi", "email"])
        ):
            tier = "tier_1"
        elif any(
            w in lower
            for w in [
                "vpn",
                "crm",
                "salesforce",
                "erp",
                "sap",
                "jira",
                "confluence",
                "gitlab",
                "jenkins",
                "payroll",
                "workday",
                "email server",
                "exchange",
                "vpn concentrator",
                "staging",
            ]
        ):
            tier = "tier_2"
        elif any(
            w in lower
            for w in [
                "printer",
                "monitor",
                "docking",
                "usb-c",
                "webcam",
                "headset",
                "mouse",
                "keyboard",
                "audio",
                "bluetooth",
                "macbook",
                "latitude",
                "wifi",
                "wi-fi",
                "display",
                "font",
            ]
        ):
            tier = "tier_3"
        elif any(
            w in lower
            for w in [
                "shortcut",
                "link",
                "intranet",
                "lunch",
                "cafeteria",
                "ergonomic",
                "pad",
                "cable",
                "bag",
            ]
        ):
            tier = "tier_4"
        else:
            tier = "tier_2"

        # 3. Infer Business Impact
        is_down = any(
            w in lower
            for w in [
                "down",
                "outage",
                "crash",
                "crashed",
                "offline",
                "unreachable",
                "blackout",
            ]
        )
        if any(
            w in lower
            for w in [
                "ransomware",
                "breach",
                "zero-day",
                "blackout",
                "total outage",
                "500 error",
                "production down",
                "checkout down",
                "unreachable",
                "fatal",
                "emergency",
                "compromise",
            ]
        ) or (is_company_wide and is_down):
            impact = "critical"
        elif (
            any(
                w in lower
                for w in [
                    "blocked",
                    "freeze",
                    "payroll",
                    "cfo",
                    "board meeting",
                    "sync broken",
                    "delayed",
                    "out of disk",
                    "rebooting",
                    "corrupt",
                ]
            )
            or is_down
        ):
            impact = "high"
        elif any(
            w in lower
            for w in [
                "forgot password",
                "reset password",
                "how to",
                "how do i",
                "inquiry",
                "guidelines",
                "request new",
                "replacement",
                "wrist rest",
                "cable",
                "signature",
                "clean",
            ]
        ):
            impact = "low"
        else:
            impact = "medium"

        return {
            "business_impact": impact,
            "affected_users": users,
            "service_criticality": tier,
        }

    def calculate_severity(
        self,
        ticket_text: str = "",
        business_impact: Optional[str] = None,
        affected_users: Optional[int] = None,
        service_criticality: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculates severity level based on enterprise impact rules, affected users,
        service criticality tier, and contextual ticket content.
        If parameters are not provided, infers them directly from the ticket text.
        """
        # Contextual inference if any parameters omitted
        if (
            business_impact is None
            or affected_users is None
            or service_criticality is None
        ):
            inferred = self.infer_parameters_from_text(ticket_text)
            if business_impact is None:
                business_impact = inferred["business_impact"]
            if affected_users is None:
                affected_users = inferred["affected_users"]
            if service_criticality is None:
                service_criticality = inferred["service_criticality"]

        impact_enum = self._normalize_business_impact(business_impact)
        crit_enum = self._normalize_service_criticality(service_criticality)
        user_count = max(1, int(affected_users) if affected_users is not None else 1)

        rule_reasons: List[str] = []
        rule_overrides: Optional[SeverityLevel] = None

        # Rule 1: Catastrophic Security or Outage Heuristic Trigger
        if ticket_text and self.CRITICAL_URGENCY_REGEX.search(ticket_text):
            if (
                impact_enum in [BusinessImpact.EXTREME, BusinessImpact.HIGH]
                or crit_enum == ServiceCriticality.TIER_1
            ):
                rule_overrides = SeverityLevel.CRITICAL
                rule_reasons.append(
                    "Triggered by Critical Emergency / Security keyword pattern on mission-critical system."
                )

        # Rule 2: Large scale outage (> 200 users on Tier 1 / Tier 2)
        if user_count >= 200 and crit_enum in [
            ServiceCriticality.TIER_1,
            ServiceCriticality.TIER_2,
        ]:
            rule_overrides = SeverityLevel.CRITICAL
            rule_reasons.append(
                f"Widespread outage affecting {user_count} users on {crit_enum.value} service."
            )

        # Rule 3: Tier 1 system with extreme business impact
        if (
            crit_enum == ServiceCriticality.TIER_1
            and impact_enum == BusinessImpact.EXTREME
        ):
            rule_overrides = SeverityLevel.CRITICAL
            rule_reasons.append(
                "Tier 1 mission-critical service experiencing extreme business impact."
            )

        # Compute Numerical Base Score (0 to 100) if no override or to validate confidence
        # Weights: Business Impact (40%), Affected Users (30%), Service Criticality (30%)
        impact_scores = {
            BusinessImpact.EXTREME: 40,
            BusinessImpact.HIGH: 30,
            BusinessImpact.MEDIUM: 18,
            BusinessImpact.LOW: 6,
        }

        # User impact logarithmic/tiered curve (max 30 pts)
        if user_count >= 500:
            user_score = 30
        elif user_count >= 100:
            user_score = 25
        elif user_count >= 20:
            user_score = 18
        elif user_count >= 5:
            user_score = 12
        else:
            user_score = 5

        # Service Tier score (max 30 pts)
        tier_scores = {
            ServiceCriticality.TIER_1: 30,
            ServiceCriticality.TIER_2: 22,
            ServiceCriticality.TIER_3: 14,
            ServiceCriticality.TIER_4: 6,
        }

        total_score = impact_scores[impact_enum] + user_score + tier_scores[crit_enum]

        # Determine level based on total calculated score
        if total_score >= 80:
            calculated_level = SeverityLevel.CRITICAL
            rule_reasons.append(
                f"Score {total_score}/100 exceeds Critical threshold (>=80)."
            )
        elif total_score >= 55:
            calculated_level = SeverityLevel.HIGH
            rule_reasons.append(
                f"Score {total_score}/100 exceeds High threshold (>=55)."
            )
        elif total_score >= 32:
            calculated_level = SeverityLevel.MEDIUM
            rule_reasons.append(
                f"Score {total_score}/100 matches Medium threshold (>=32)."
            )
        else:
            calculated_level = SeverityLevel.LOW
            rule_reasons.append(
                f"Score {total_score}/100 is within Low threshold (<32)."
            )

        # Apply rule override if higher severity is dictated by safety rules
        final_level = rule_overrides if rule_overrides is not None else calculated_level

        # Calculate confidence metric
        confidence = min(0.99, max(0.85, 0.75 + (total_score / 400.0)))

        sla = self.SLA_MATRIX[final_level]

        return {
            "severity": final_level.value,
            "severity_score": total_score,
            "confidence": round(confidence, 3),
            "parameters": {
                "business_impact": impact_enum.value,
                "affected_users": user_count,
                "service_criticality": crit_enum.value,
            },
            "sla": {
                "response_time": f"{sla['initial_response_mins']} mins",
                "resolution_time": f"{sla['target_resolution_hours']} hours",
                "escalation": sla["escalation_path"],
            },
            "reasoning": "; ".join(rule_reasons),
        }
