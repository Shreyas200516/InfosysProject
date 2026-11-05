"""Email automation. EMAIL_MODE=mock stores messages (visible in the UI); smtp sends them."""
from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Any, Optional

from ..config import settings
from ..db.repo import Repository, new_id, now_iso


class Notifier:
    def __init__(self, repo: Repository):
        self.repo = repo
        self.mode = settings.email_mode

    def send(self, ticket_id: Optional[str], recipient: str, subject: str, body: str) -> dict[str, Any]:
        status = "mock-sent"
        if self.mode == "smtp":
            try:
                msg = EmailMessage()
                msg["From"], msg["To"], msg["Subject"] = settings.email_from, recipient, subject
                msg.set_content(body)
                with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as s:
                    s.starttls()
                    if settings.smtp_user:
                        s.login(settings.smtp_user, settings.smtp_password)
                    s.send_message(msg)
                status = "sent"
            except Exception as exc:
                status = f"failed: {type(exc).__name__}"
        return self.repo.insert("notifications", {
            "notification_id": new_id("NTF"), "ticket_id": ticket_id, "recipient": recipient,
            "subject": subject, "body": body, "channel": "email", "status": status, "created_at": now_iso()})

    def role_requested(self, to: str, requester: dict[str, Any], role: str):
        return self.send(None, to, f"Role request: {requester['name']} wants {role.replace('_', ' ')} access",
                         f"Hi,\n\n{requester['name']} ({requester['email']}) signed up and asked for the {role.replace('_', ' ')} role.\n"
                         f"They are an employee until you decide. Open SupportPilot > Approvals to approve or reject.\n\n- SupportPilot")

    def role_decided(self, to: str, role: str, approved: bool):
        label = role.replace('_', ' ')
        body = (f"Your request for the {label} role was approved. Sign out and back in if you were already signed in."
                if approved else f"Your request for the {label} role was not approved. Your account stays an employee account.")
        return self.send(None, to, f"Your {label} role request was {'approved' if approved else 'declined'}", f"Hi,\n\n{body}\n\n- SupportPilot")

    # ---- templates ----
    def ticket_received(self, t: dict[str, Any], to: str):
        return self.send(t["ticket_id"], to, f"[{t['ticket_id']}] We received your request: {t['subject']}",
                         f"Hi,\n\nYour ticket {t['ticket_id']} was received and classified as {t.get('category')} "
                         f"({t.get('priority')} priority, {t.get('severity')} severity). SupportPilot is investigating.\n\n- SupportPilot")

    def resolved(self, t: dict[str, Any], to: str, steps: list[str], sources: list[str]):
        numbered = "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
        return self.send(t["ticket_id"], to, f"[{t['ticket_id']}] Suggested fix: {t['subject']}",
                         f"Hi,\n\nHere are the steps that should resolve your issue:\n\n{numbered}\n\nSources: {', '.join(sources) or 'knowledge base'}\n\n"
                         f"If this does not fix it, reply to this email and a support engineer will take over.\n\n- SupportPilot")

    def escalated(self, t: dict[str, Any], to: str, team: str, reason: str, sla: dict[str, Any] | None = None):
        sla_line = f"\nExpected first response: {sla.get('response_time')}." if sla else ""
        return self.send(t["ticket_id"], to, f"[{t['ticket_id']}] Escalated to {team}",
                         f"Hi,\n\nYour ticket {t['ticket_id']} has been escalated to {team}.\nReason: {reason}{sla_line}\n\n- SupportPilot")
