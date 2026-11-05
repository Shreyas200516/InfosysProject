"""Jira integration. JIRA_MODE=mock (default, offline) or real (Jira Cloud REST v3)."""
from __future__ import annotations

from typing import Any

from ..config import settings
from ..db.repo import Repository, new_id, now_iso

PRIORITY_MAP = {"Critical": "Highest", "High": "High", "Medium": "Medium", "Low": "Low"}


class JiraClient:
    def __init__(self, repo: Repository):
        self.repo = repo
        self.mode = settings.jira_mode

    # ---- public API ----
    def create_issue(self, ticket: dict[str, Any], summary_extra: str = "") -> dict[str, Any]:
        if self.mode == "real":
            key, url = self._real_create(ticket)
        else:
            n = self.repo.count("jira_tickets") + 101
            key = f"{settings.jira_project_key}-{n}"
            url = f"https://mock-jira.local/browse/{key}"
        return self.repo.insert("jira_tickets", {
            "jira_id": new_id("JRA"), "ticket_id": ticket["ticket_id"], "jira_issue_key": key,
            "jira_status": "To Do", "jira_url": url, "mode": self.mode, "last_updated": now_iso()})

    def update_status(self, ticket_id: str, status: str, comment: str | None = None) -> dict[str, Any] | None:
        rows = self.repo.list("jira_tickets", where={"ticket_id": ticket_id}, limit=1)
        if not rows:
            return None
        row = rows[0]
        if self.mode == "real":
            self._real_transition(row["jira_issue_key"], status, comment)
        return self.repo.update("jira_tickets", row["jira_id"], {"jira_status": status, "last_updated": now_iso()})

    # ---- real Jira Cloud (needs credentials; not exercised in tests) ----
    def _auth(self):
        import base64
        token = base64.b64encode(f"{settings.jira_email}:{settings.jira_api_token}".encode()).decode()
        return {"Authorization": f"Basic {token}", "Content-Type": "application/json", "Accept": "application/json"}

    def _real_create(self, ticket: dict[str, Any]) -> tuple[str, str]:
        import requests

        body = {"fields": {
            "project": {"key": settings.jira_project_key},
            "summary": f"[{ticket.get('category', 'IT')}] {ticket['subject']}"[:250],
            "issuetype": {"name": "Task"},
            "priority": {"name": PRIORITY_MAP.get(ticket.get("priority", "Medium"), "Medium")},
            "labels": ["supportpilot", str(ticket.get("category", "general")).lower().replace(" ", "-")],
            "description": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [
                {"type": "text", "text": f"{ticket['description']}\n\nSupportPilot ticket: {ticket['ticket_id']} | Severity: {ticket.get('severity')}"}]}]},
        }}
        r = requests.post(f"{settings.jira_base_url}/rest/api/3/issue", json=body, headers=self._auth(), timeout=20)
        r.raise_for_status()
        key = r.json()["key"]
        return key, f"{settings.jira_base_url}/browse/{key}"

    def _real_transition(self, key: str, status: str, comment: str | None) -> None:
        import requests

        base = f"{settings.jira_base_url}/rest/api/3/issue/{key}"
        if comment:
            requests.post(f"{base}/comment", headers=self._auth(), timeout=20, json={"body": {"type": "doc", "version": 1, "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": comment}]}]}}).raise_for_status()
        transitions = requests.get(f"{base}/transitions", headers=self._auth(), timeout=20).json().get("transitions", [])
        match = next((t for t in transitions if t["to"]["name"].lower() == status.lower()), None)
        if match:
            requests.post(f"{base}/transitions", headers=self._auth(), timeout=20, json={"transition": {"id": match["id"]}}).raise_for_status()
