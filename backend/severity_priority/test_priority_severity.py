"""
Tests priority predictions and severity scoring rules across realistic sample IT tickets.
"""

import json
try:
    from .priority_severity_service import PrioritySeverityService
except ImportError:  # run as a plain script
    from priority_severity_service import PrioritySeverityService


def run_tests():
    print("=" * 80)
    print("Priority & Severity Testing on Sample Tickets")
    print("=" * 80)

    service = PrioritySeverityService(model_path="priority_model.joblib")

    test_cases = [
        {
            "name": "Case 1: Catastrophic Production Outage",
            "ticket_text": "CRITICAL: Primary database cluster down with 500 internal server error. All checkout flows failing.",
            "business_impact": "critical",
            "affected_users": 2500,
            "service_criticality": "tier_1",
            "expected_priority": "Critical",
            "expected_severity": "Critical",
        },
        {
            "name": "Case 2: Active Ransomware Security Incident",
            "ticket_text": "Active ransomware detected on internal accounting file server, files being encrypted rapidly.",
            "business_impact": "critical",
            "affected_users": 150,
            "service_criticality": "tier_1",
            "expected_priority": "Critical",
            "expected_severity": "Critical",
        },
        {
            "name": "Case 3: Regional VPN Outage for Large Team",
            "ticket_text": "VPN gateway connection failing for entire APAC regional engineering team. 120 engineers blocked.",
            "business_impact": "high",
            "affected_users": 120,
            "service_criticality": "tier_2",
            "expected_priority": "High",
            "expected_severity": "High",
        },
        {
            "name": "Case 4: Executive Incident Before Board Meeting",
            "ticket_text": "CFO laptop blue-screened with kernel panic 1 hour before quarterly board meeting presentation.",
            "business_impact": "high",
            "affected_users": 1,
            "service_criticality": "tier_2",
            "expected_priority": "High",
            "expected_severity": "High",
        },
        {
            "name": "Case 5: Local Workstation Display Hardware Glitch",
            "ticket_text": "Dual monitor display flickers and goes dark intermittently when plugged into USB-C docking station.",
            "business_impact": "medium",
            "affected_users": 1,
            "service_criticality": "tier_3",
            "expected_priority": "Medium",
            "expected_severity": "Medium",
        },
        {
            "name": "Case 6: Office Printer Paper Jam",
            "ticket_text": "Color laser printer on 4th floor having continuous paper jams and low yellow toner warning.",
            "business_impact": "medium",
            "affected_users": 8,
            "service_criticality": "tier_3",
            "expected_priority": "Medium",
            "expected_severity": "Medium",
        },
        {
            "name": "Case 7: Routine Self-Service Password Reset",
            "ticket_text": "Forgot password for internal employee travel expense reimbursement portal. Need reset link.",
            "business_impact": "low",
            "affected_users": 1,
            "service_criticality": "tier_4",
            "expected_priority": "Low",
            "expected_severity": "Low",
        },
        {
            "name": "Case 8: Ergonomic Equipment Request",
            "ticket_text": "Request ergonomic wrist rest pad and vertical wireless mouse for desk workstation.",
            "business_impact": "low",
            "affected_users": 1,
            "service_criticality": "tier_4",
            "expected_priority": "Low",
            "expected_severity": "Low",
        },
    ]

    passed = 0
    total = len(test_cases)

    for idx, tc in enumerate(test_cases, 1):
        print(f"\n[{idx}/{total}] Testing: {tc['name']}")
        print(f"Ticket Text : {tc['ticket_text']}")
        print(
            f"Inputs      : Impact={tc['business_impact']} | Users={tc['affected_users']} | Service={tc['service_criticality']}"
        )

        result = service.evaluate_ticket(
            ticket_text=tc["ticket_text"],
            business_impact=tc["business_impact"],
            affected_users=tc["affected_users"],
            service_criticality=tc["service_criticality"],
        )

        pred_priority = result["priority"]["predicted_priority"]
        pred_severity = result["severity"]["level"]
        sev_score = result["severity"]["score"]
        conf = result["priority"]["confidence"]
        sla = result["sla"]

        match_priority = pred_priority == tc["expected_priority"]
        match_severity = pred_severity == tc["expected_severity"]

        status = (
            "PASSED [OK]" if (match_priority and match_severity) else "REVIEW [CHECK]"
        )
        if match_priority and match_severity:
            passed += 1

        print(
            f"Results     : Predicted Priority = {pred_priority} (conf={conf:.2f}) | Severity = {pred_severity} (score={sev_score})"
        )
        print(
            f"SLA         : Target Response < {sla['response_time']} | Resolution < {sla['resolution_time']}"
        )
        print(f"Escalation  : {sla['escalation']}")
        print(f"Reasoning   : {result['severity']['reasoning']}")
        print(f"Status      : {status}")

    print("\n" + "=" * 80)
    print(
        f"SUMMARY: {passed}/{total} Sample Ticket Test Cases Passed Perfectly ({passed/total*100:.1f}%)"
    )
    print("=" * 80)


if __name__ == "__main__":
    run_tests()
