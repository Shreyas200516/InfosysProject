"""End-to-end ticket processing: intake -> classify -> triage -> agents -> Jira/email -> storage."""
from __future__ import annotations

from typing import Any, Optional

from rag_pipeline.schemas import TicketInput

from .agents.agents import DiagnosisAgent, EscalationAgent, KnowledgeRetrievalAgent, ResolutionAgent
from .agents.base import AgentContext, run_agent
from .db.repo import Repository, new_id, new_ticket_id, now_iso, public_user
from .integrations.jira import JiraClient
from .integrations.notifier import Notifier
from .services.classifier import get_classifier
from .services.knowledge import get_knowledge
from .services.triage import get_triage


def log(repo: Repository, ticket_id: str, action: str, by: str = "system", details: Optional[dict] = None) -> None:
    repo.insert("activity_logs", {"log_id": new_id("LOG"), "ticket_id": ticket_id, "action": action,
                                  "performed_by": by, "details": details or {}, "timestamp": now_iso()})


def analyze(subject: str, description: str, **overrides) -> dict[str, Any]:
    """Stateless preview used by the live-classification UI: classification + triage + top articles."""
    text = f"{subject}. {description}".strip()
    cls = get_classifier().predict(text)
    tri = get_triage().evaluate(text, **overrides)
    docs = get_knowledge().search(f"{cls['category']} {text}"[:600])
    return {"ticket_text": text, "classification": cls, "triage": tri,
            "articles": [d.model_dump() for d in docs], "retrieval_mode": get_knowledge().mode}


def upsert_user(repo: Repository, name: str, email: str, department: Optional[str]) -> dict[str, Any]:
    existing = repo.list("users", where={"email": email.lower()}, limit=1)
    if existing:
        return existing[0]
    return repo.insert("users", {"user_id": new_id("USR"), "name": name, "email": email.lower(),
                                 "department": department, "role": "employee", "created_at": now_iso()})


def process_ticket(repo: Repository, *, subject: str, description: str, requester_name: str, requester_email: str,
                   department: Optional[str] = None, source: str = "portal", business_impact: Optional[str] = None,
                   affected_users: Optional[int] = None, service_criticality: Optional[str] = None,
                   run_agents: bool = True) -> dict[str, Any]:
    user = upsert_user(repo, requester_name, requester_email, department)
    text = f"{subject}. {description}".strip()
    cls = get_classifier().predict(text)
    tri = get_triage().evaluate(text, business_impact, affected_users, service_criticality)

    ticket = repo.insert("tickets", {
        "ticket_id": new_ticket_id(), "user_id": user["user_id"], "subject": subject, "description": description,
        "ticket_text": text, "category": cls["category"], "category_confidence": cls["confidence"],
        "priority": tri["priority"], "priority_confidence": tri["priority_confidence"], "severity": tri["severity"],
        "severity_score": tri["severity_score"], "business_impact": tri["business_impact"], "affected_users": tri["affected_users"],
        "service_tier": tri["service_tier"], "sla_response": tri["sla"]["response_time"], "sla_resolution": tri["sla"]["resolution_time"],
        "status": "Processing", "source": source, "created_at": now_iso(), "updated_at": now_iso()})
    tid = ticket["ticket_id"]
    log(repo, tid, "ticket_created", "user", {"source": source})
    log(repo, tid, "classified", "classifier", {"category": cls["category"], "confidence": cls["confidence"], "source": cls["source"]})
    log(repo, tid, "triaged", "severity_engine", {"priority": tri["priority"], "severity": tri["severity"], "score": tri["severity_score"]})

    notifier, jira = Notifier(repo), JiraClient(repo)
    notifier.ticket_received(ticket, user["email"])

    if run_agents:
        _run_agents(repo, ticket, user, cls, tri, notifier, jira)
    return get_ticket_detail(repo, tid)


def _run_agents(repo, ticket, user, cls, tri, notifier: Notifier, jira: JiraClient) -> None:
    tid = ticket["ticket_id"]
    kb = get_knowledge()
    ctx = AgentContext(ticket=ticket, classification=cls, triage=tri, ticket_input=TicketInput(
        ticket_id=tid, subject=ticket["subject"], description=ticket["description"], category=cls["category"],
        priority=tri["priority"], severity=tri["severity"], requester_email=user["email"], department=user.get("department")))

    for agent in (DiagnosisAgent(), KnowledgeRetrievalAgent(kb), ResolutionAgent(kb), EscalationAgent()):
        result = run_agent(agent, ctx, repo)
        log(repo, tid, f"agent:{agent.name}", agent.name, {"status": result["status"], "ms": result["duration_ms"]})

    # Failed Resolution/Escalation agents must never leave a ticket silently stuck.
    if ctx.rag is None or not ctx.decision:
        ctx.decision = {"escalate": True, "team": "IT Service Desk (Tier 2)", "priority": tri["priority"], "sla": tri["sla"],
                        "reason": "Automated processing failed; routed to a human engineer."}

    rag = ctx.rag
    if rag is not None:
        repo.insert("ticket_responses", {
            "response_id": new_id("RSP"), "ticket_id": tid, "generated_response": rag.resolution,
            "steps": rag.step_by_step_steps, "sources": rag.sources_cited,
            "retrieved": [{"title": d.title, "category": d.category, "source": d.source, "score": d.relevance_score} for d in rag.retrieved_documents],
            "confidence_score": ctx.confidence, "grounded": rag.grounding.is_grounded, "provider": rag.provider,
            "model": rag.model_name, "processing_time_ms": rag.processing_time_ms, "generated_at": now_iso()})

    d = ctx.decision
    issue = jira.create_issue({**ticket, "priority": tri["priority"], "severity": tri["severity"]})
    log(repo, tid, "jira_created", "jira", {"key": issue["jira_issue_key"], "mode": issue["mode"]})

    if d["escalate"]:
        repo.insert("escalations", {"escalation_id": new_id("ESC"), "ticket_id": tid, "assigned_team": d["team"],
                                    "escalation_reason": d["reason"], "status": "Open", "priority": tri["priority"], "created_at": now_iso()})
        repo.update("tickets", tid, {"status": "Escalated", "resolution_type": "human", "updated_at": now_iso()})
        jira.update_status(tid, "In Progress", f"Escalated to {d['team']}: {d['reason']}")
        notifier.escalated(ticket, user["email"], d["team"], d["reason"], tri["sla"])
        log(repo, tid, "escalated", "Escalation Agent", {"team": d["team"], "reason": d["reason"]})
    else:
        repo.update("tickets", tid, {"status": "AI Resolved", "resolution_type": "ai", "resolved_at": now_iso(), "updated_at": now_iso()})
        jira.update_status(tid, "Done", "Resolved automatically by SupportPilot.")
        notifier.resolved(ticket, user["email"], rag.step_by_step_steps, rag.sources_cited)
        log(repo, tid, "auto_resolved", "Resolution Agent", {"confidence": ctx.confidence})


def get_ticket_detail(repo: Repository, ticket_id: str) -> Optional[dict[str, Any]]:
    t = repo.get("tickets", ticket_id)
    if not t:
        return None
    resp = repo.list("ticket_responses", {"ticket_id": ticket_id}, "generated_at", limit=1)
    esc = repo.list("escalations", {"ticket_id": ticket_id}, "created_at", limit=1)
    jira = repo.list("jira_tickets", {"ticket_id": ticket_id}, "last_updated", limit=1)
    return {
        "ticket": t, "user": public_user(repo.get("users", t["user_id"])) if t.get("user_id") else None,
        "response": resp[0] if resp else None, "escalation": esc[0] if esc else None, "jira": jira[0] if jira else None,
        "agent_runs": repo.list("agent_runs", {"ticket_id": ticket_id}, "started_at", desc=False),
        "activity": repo.list("activity_logs", {"ticket_id": ticket_id}, "timestamp", desc=False),
        "notifications": repo.list("notifications", {"ticket_id": ticket_id}, "created_at", desc=False),
    }
