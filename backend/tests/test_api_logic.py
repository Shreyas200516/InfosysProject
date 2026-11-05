"""Router functions called directly (works with or without FastAPI installed)."""
import pytest
from pydantic import ValidationError

from app.routers import knowledge, ops, tickets
from app.schemas import TicketCreate

BODY = dict(subject="VPN keeps disconnecting", description="The VPN drops every ten minutes at home.")


@pytest.mark.parametrize("patch", [{"subject": "hi"}, {"description": "short"},
                                   {"affected_users": 0}, {"business_impact": "huge"}, {"source": "fax"}])
def test_validation_rejects_bad_input(patch):
    with pytest.raises(ValidationError):
        TicketCreate(**{**BODY, **patch})


def test_create_list_get_update(repo, make_user):
    emp, eng = make_user("employee", email="asha@acme.com"), make_user("support_engineer")
    d = tickets.create_ticket(TicketCreate(**BODY), user=emp)
    tid = d["ticket"]["ticket_id"]
    listing = tickets.list_tickets(q="vpn", user=eng)
    assert listing["total"] == 1 and listing["items"][0]["requester_email"] == "asha@acme.com" and listing["items"][0]["jira_key"]
    assert tickets.get_ticket(tid, user=eng)["ticket"]["ticket_id"] == tid
    with pytest.raises(Exception) as e:
        tickets.get_ticket("TKT-NOPE", user=eng)
    assert getattr(e.value, "status_code", None) == 404
    from app.schemas import StatusUpdate
    out = tickets.update_status(tid, StatusUpdate(status="Closed", note="done"), user=eng)
    assert out["ticket"]["status"] == "Closed" and out["jira"]["jira_status"] == "Done"


def test_analytics_summary_and_integrations(repo, make_user):
    emp, eng = make_user("employee"), make_user("support_engineer")
    for s, dsc in [("Account locked", "My account is locked after too many password attempts."),
                   ("Phishing email", "I clicked a link in a fake invoice email")]:
        tickets.create_ticket(TicketCreate(**{**BODY, "subject": s, "description": dsc}), user=emp)
    a = ops.summary(user=eng)
    assert a["totals"]["tickets"] == 2 and a["totals"]["ai_resolved"] == 1 and a["totals"]["escalated"] == 1
    assert a["totals"]["automation_rate"] == 0.5 and len(a["volume"]) == 14 and a["agent_latency_ms"]
    i = ops.integrations(user=eng)
    assert i["jira"]["total"] == 2 and i["email"]["total"] >= 2 and i["database"]["backend"] == "sqlite"


def test_search_and_rag_preview(make_user):
    u = make_user("support_engineer")
    from app.schemas import AnalyzeRequest, SearchRequest
    s = knowledge.search(SearchRequest(query="printer shows offline"), user=u)
    assert s["items"][0]["title"] == "Printer Showing Offline"
    r = knowledge.resolve(AnalyzeRequest(subject="Printer offline", description="printer on floor three shows offline"), user=u)
    assert r["step_by_step_steps"] and r["grounding"]["is_grounded"]
