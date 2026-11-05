from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import pipeline
from ..auth import current_user, staff_only
from ..db.repo import get_repo, now_iso
from ..integrations.jira import JiraClient
from ..schemas import AnalyzeRequest, StatusUpdate, TicketCreate

router = APIRouter(prefix="/api/v1/tickets", tags=["tickets"])
NOT_FOUND = HTTPException(404, "Ticket not found")


@router.post("", status_code=201)
def create_ticket(body: TicketCreate, user=Depends(current_user)):
    """Accept a ticket from the signed-in user, classify it, score priority/severity, run the agents."""
    data = body.model_dump()
    data["department"] = data.get("department") or user.get("department")
    return pipeline.process_ticket(get_repo(), requester_name=user["name"], requester_email=user["email"], **data)


@router.post("/analyze")
def analyze_ticket(body: AnalyzeRequest, user=Depends(current_user)):
    """Stateless live preview (nothing stored): category, priority, severity, SLA, top articles."""
    if len((body.subject + body.description).strip()) < 5:
        raise HTTPException(422, "Provide at least a few words of ticket text.")
    return pipeline.analyze(body.subject, body.description, business_impact=body.business_impact,
                            affected_users=body.affected_users, service_criticality=body.service_criticality)


@router.get("")
def list_tickets(status: Optional[str] = None, category: Optional[str] = None, priority: Optional[str] = None,
                 severity: Optional[str] = None, q: Optional[str] = None,
                 limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0), user=Depends(current_user)):
    """Employees see only their own tickets; support engineers and admins see all."""
    repo = get_repo()
    where = {k: v for k, v in {"status": status, "category": category, "priority": priority, "severity": severity}.items() if v}
    if user["role"] == "employee":
        where["user_id"] = user["user_id"]
    rows = repo.list("tickets", where or None, "created_at", True)
    if q:
        ql = q.lower()
        rows = [r for r in rows if ql in (r["subject"] + " " + r["ticket_id"]).lower()]
    total = len(rows)
    page = rows[offset: offset + limit]
    users = {u["user_id"]: u for u in repo.list("users")}
    jira = {j["ticket_id"]: j for j in repo.list("jira_tickets")}
    for r in page:
        u = users.get(r.get("user_id")) or {}
        r["requester_name"], r["requester_email"] = u.get("name"), u.get("email")
        r["jira_key"] = (jira.get(r["ticket_id"]) or {}).get("jira_issue_key")
    return {"total": total, "items": page}


@router.get("/{ticket_id}")
def get_ticket(ticket_id: str, user=Depends(current_user)):
    detail = pipeline.get_ticket_detail(get_repo(), ticket_id)
    # An employee asking for someone else's ticket gets the same answer as for a ticket that doesn't exist.
    if not detail or (user["role"] == "employee" and detail["ticket"]["user_id"] != user["user_id"]):
        raise HTTPException(404, "Ticket not found")
    return detail


@router.patch("/{ticket_id}/status")
def update_status(ticket_id: str, body: StatusUpdate, user=Depends(staff_only)):
    repo = get_repo()
    if not repo.get("tickets", ticket_id):
        raise HTTPException(404, "Ticket not found")
    patch = {"status": body.status, "updated_at": now_iso()}
    if body.status in {"Resolved", "Closed"}:
        patch["resolved_at"] = now_iso()
    repo.update("tickets", ticket_id, patch)
    pipeline.log(repo, ticket_id, "status_changed", f"{user['name']} ({user['role']})", {"status": body.status, "note": body.note})
    jira_status = {"Resolved": "Done", "Closed": "Done", "In Progress": "In Progress"}.get(body.status)
    if jira_status:
        JiraClient(repo).update_status(ticket_id, jira_status, body.note)
    for esc in repo.list("escalations", {"ticket_id": ticket_id}):
        if body.status in {"Resolved", "Closed"}:
            repo.update("escalations", esc["escalation_id"], {"status": "Resolved"})
        elif body.status == "In Progress":
            repo.update("escalations", esc["escalation_id"], {"status": "In Progress"})
    return pipeline.get_ticket_detail(repo, ticket_id)
