import pytest

from app import pipeline
from app.config import settings

GOOD = dict(requester_name="Asha Rao", requester_email="asha@acme.com", department="Finance")


def run(repo, subject, description, **kw):
    return pipeline.process_ticket(repo, subject=subject, description=description, **GOOD, **kw)


def test_ticket_ids_unique_and_formatted(repo):
    ids = {run(repo, "VPN keeps disconnecting", "The VPN drops every ten minutes at home.")["ticket"]["ticket_id"] for _ in range(5)}
    assert len(ids) == 5 and all(i.startswith("TKT-") for i in ids)


def test_milestone1_outputs_category_priority_severity(repo):
    t = run(repo, "VPN keeps disconnecting", "The VPN drops every ten minutes at home.", run_agents=False)["ticket"]
    assert t["category"] == "VPN"
    assert t["priority"] in {"Critical", "High", "Medium", "Low"} and t["severity"] in {"Critical", "High", "Medium", "Low"}
    assert 0 <= t["severity_score"] <= 100 and t["status"] == "Processing"


def test_routine_ticket_is_auto_resolved_with_cited_steps(repo):
    d = run(repo, "Account locked", "My account is locked after too many password attempts.")
    assert d["ticket"]["status"] == "AI Resolved" and d["ticket"]["resolution_type"] == "ai"
    assert d["response"]["steps"] and d["response"]["sources"] and d["response"]["grounded"] is True
    assert d["escalation"] is None and d["jira"]["jira_status"] == "Done"
    assert any("Suggested fix" in n["subject"] for n in d["notifications"])


def test_unknown_topic_escalates_without_inventing_steps(repo):
    d = run(repo, "SAP invoice error", "SAP FI module throws posting error 4711 when I book invoices.")
    assert d["ticket"]["status"] == "Escalated" and d["escalation"]["assigned_team"]
    assert d["response"]["steps"] == []


def test_security_always_escalates_to_infosec(repo):
    d = run(repo, "Phishing email", "I clicked a link in a fake invoice email")
    assert d["ticket"]["category"] == "Security" and d["ticket"]["status"] == "Escalated"
    assert "InfoSec" in d["escalation"]["assigned_team"]


def test_critical_severity_escalates(repo):
    d = run(repo, "VPN is down", "VPN is down for the whole company, nobody can connect")
    assert d["ticket"]["severity"] == "Critical" and d["ticket"]["status"] == "Escalated"
    assert "Critical" in d["escalation"]["escalation_reason"]


def test_all_four_agents_logged_and_activity_trail(repo):
    d = run(repo, "Outlook not syncing", "Outlook is not syncing new emails on my laptop since Monday.")
    assert [r["agent_name"] for r in d["agent_runs"]] == ["Diagnosis Agent", "Knowledge Retrieval Agent", "Resolution Agent", "Escalation Agent"]
    assert all(r["status"] == "completed" for r in d["agent_runs"])
    actions = [a["action"] for a in d["activity"]]
    assert actions[:3] == ["ticket_created", "classified", "triaged"] and "jira_created" in actions


def test_user_is_reused_by_email(repo):
    run(repo, "Printer offline", "The printer on floor three shows offline.")
    run(repo, "Monitor no signal", "The monitor shows no signal from the dock.")
    assert repo.count("users") == 1 and repo.count("tickets") == 2


def test_agent_failure_does_not_strand_ticket(repo, monkeypatch):
    from app.agents import agents
    monkeypatch.setattr(agents.ResolutionAgent, "run", lambda self, ctx: (_ for _ in ()).throw(RuntimeError("llm down")))
    d = run(repo, "VPN keeps disconnecting", "The VPN drops every ten minutes at home.")
    assert d["ticket"]["status"] == "Escalated"
    assert any(r["status"] == "failed" for r in d["agent_runs"])


def test_analyze_preview_stores_nothing(repo):
    out = pipeline.analyze("Teams crashing", "Microsoft Teams keeps crashing during meetings")
    assert out["classification"]["category"] == "Software" and out["articles"]
    assert repo.count("tickets") == 0
