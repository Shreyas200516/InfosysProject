"""Agent activity, integrations status, and analytics."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends

from ..auth import staff_only
from ..config import settings
from ..db.repo import get_repo
from ..services.classifier import get_classifier
from ..services.knowledge import get_knowledge

router = APIRouter(prefix="/api/v1", tags=["operations"])


@router.get("/health")
def health():
    repo, kb = get_repo(), get_knowledge()
    return {"status": "ok", "database": repo.backend, "retrieval": kb.mode, "llm_provider": kb.llm.provider,
            "llm_model": kb.llm.model_name, "category_model_loaded": get_classifier().ready,
            "jira_mode": settings.jira_mode, "email_mode": settings.email_mode}


@router.get("/agents/runs")
def agent_runs(ticket_id: Optional[str] = None, limit: int = 60, user=Depends(staff_only)):
    repo = get_repo()
    rows = repo.list("agent_runs", {"ticket_id": ticket_id} if ticket_id else None, "started_at", True, limit)
    return {"items": rows}


@router.get("/integrations")
def integrations(user=Depends(staff_only)):
    repo = get_repo()
    jira = repo.list("jira_tickets", order_by="last_updated", limit=25)
    mail = repo.list("notifications", order_by="created_at", limit=25)
    kb = get_knowledge()
    return {
        "jira": {"mode": settings.jira_mode, "project": settings.jira_project_key, "total": repo.count("jira_tickets"), "items": jira},
        "email": {"mode": settings.email_mode, "from": settings.email_from, "total": repo.count("notifications"), "items": mail},
        "llm": {"provider": kb.llm.provider, "model": kb.llm.model_name},
        "vector_store": {"mode": kb.mode, "articles": len(kb.list_articles())},
        "database": {"backend": repo.backend},
    }


@router.get("/analytics/summary")
def summary(days: int = 14, user=Depends(staff_only)):
    repo = get_repo()
    tickets = repo.list("tickets", order_by="created_at", limit=5000)
    responses = repo.list("ticket_responses", limit=5000)
    escalations = repo.list("escalations", limit=5000)
    runs = repo.list("agent_runs", limit=5000)
    total = len(tickets)
    ai = sum(1 for t in tickets if t.get("resolution_type") == "ai")
    esc = sum(1 for t in tickets if t.get("status") == "Escalated" or t.get("resolution_type") == "human")

    today = datetime.now(timezone.utc).date()
    volume = defaultdict(int)
    for t in tickets:
        volume[str(t["created_at"])[:10]] += 1
    series = [{"date": str(today - timedelta(days=i)), "tickets": volume.get(str(today - timedelta(days=i)), 0)} for i in range(days - 1, -1, -1)]

    by_agent = defaultdict(list)
    for r in runs:
        by_agent[r["agent_name"]].append(r["duration_ms"] or 0)
    avg = lambda xs: round(sum(xs) / len(xs), 2) if xs else 0.0  # noqa: E731

    def dist(key):
        return [{"name": k or "Unknown", "value": v} for k, v in Counter(t.get(key) for t in tickets).most_common()]

    return {
        "totals": {"tickets": total, "ai_resolved": ai, "escalated": esc, "open": sum(1 for t in tickets if t["status"] in {"Open", "Processing", "In Progress", "Escalated"}),
                   "automation_rate": round(ai / total, 4) if total else 0.0, "escalation_rate": round(esc / total, 4) if total else 0.0},
        "avg_confidence": avg([r["confidence_score"] for r in responses if r.get("confidence_score") is not None]),
        "avg_response_ms": avg([r["processing_time_ms"] for r in responses if r.get("processing_time_ms") is not None]),
        "volume": series, "by_category": dist("category"), "by_priority": dist("priority"), "by_severity": dist("severity"), "by_status": dist("status"),
        "escalations_by_team": [{"name": k, "value": v} for k, v in Counter(e["assigned_team"] for e in escalations).most_common()],
        "escalation_status": [{"name": k, "value": v} for k, v in Counter(e["status"] for e in escalations).most_common()],
        "agent_latency_ms": [{"name": k, "value": avg(v), "runs": len(v)} for k, v in by_agent.items()],
        "recent_escalations": escalations[-8:][::-1],
    }
