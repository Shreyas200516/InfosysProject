"""The four SupportPilot agents (Milestone 3)."""
from __future__ import annotations

import re
from typing import Any

from ..config import settings
from ..services.knowledge import KnowledgeService
from .base import Agent, AgentContext

TEAM_BY_CATEGORY = {
    "Network": "Network Engineering", "VPN": "Network Engineering", "Email": "Messaging & Collaboration",
    "Software": "Application Support", "Hardware": "Workplace & Desktop Support",
    "Access": "Identity & Access Management", "Security": "InfoSec / Security Operations",
}
ERROR_CODE_RX = re.compile(r"(0x[0-9a-f]{4,8}|error\s*(?:code\s*)?#?\d{2,5}|\b[45]\d{2}\s+error|\b(?:err|e)_[a-z_]+)", re.I)
SCOPE_HINTS = [("company-wide", r"whole company|entire company|company[- ]wide|all (employees|users|staff)"),
               ("team/department", r"\b(team|department|floor|office)\b"), ("single user", r".")]


class DiagnosisAgent(Agent):
    """Understands the ticket: symptoms, error codes, scope, and builds the retrieval query."""
    name = "Diagnosis Agent"

    def run(self, ctx: AgentContext) -> dict[str, Any]:
        text = ctx.ticket["ticket_text"]
        codes = sorted({m.group(0).strip() for m in ERROR_CODE_RX.finditer(text)})
        scope = next(label for label, rx in SCOPE_HINTS if re.search(rx, text, re.I))
        users = ctx.triage["affected_users"]
        if users >= 200:
            scope = "company-wide"
        category = ctx.classification["category"]
        ctx.diagnosis = {
            "category": category, "category_confidence": ctx.classification["confidence"],
            "severity": ctx.triage["severity"], "priority": ctx.triage["priority"],
            "error_codes": codes, "scope": scope, "affected_users": users,
            "query": f"{category} {ctx.ticket['subject']} {ctx.ticket['description']}"[:600],
            "summary": (f"{category} issue, {ctx.triage['severity']} severity, scope: {scope}"
                        + (f", error codes: {', '.join(codes)}" if codes else "") + "."),
        }
        return ctx.diagnosis


class KnowledgeRetrievalAgent(Agent):
    """Semantic search over the knowledge base (ChromaDB, or the lexical fallback)."""
    name = "Knowledge Retrieval Agent"

    def __init__(self, knowledge: KnowledgeService):
        self.kb = knowledge

    def run(self, ctx: AgentContext) -> dict[str, Any]:
        ctx.docs = self.kb.search(ctx.diagnosis.get("query") or ctx.ticket["ticket_text"], top_k=settings.top_k)
        return {"retrieval_mode": self.kb.mode, "count": len(ctx.docs),
                "articles": [{"title": d.title, "category": d.category, "source": d.source,
                              "score": d.relevance_score, "doc_id": d.doc_id} for d in ctx.docs]}


class ResolutionAgent(Agent):
    """Generates a grounded, cited, step-by-step answer with the team's RAG pipeline."""
    name = "Resolution Agent"

    def __init__(self, knowledge: KnowledgeService):
        self.kb = knowledge

    def run(self, ctx: AgentContext) -> dict[str, Any]:
        ctx.rag = self.kb.resolve(ctx.ticket_input, docs=ctx.docs)
        g = ctx.rag.grounding
        cat_conf = ctx.classification["confidence"]
        ctx.confidence = round(0.75 * g.confidence_score + 0.25 * cat_conf, 2) if g.is_grounded else round(g.confidence_score * 0.6, 2)
        return {"grounded": g.is_grounded, "confidence": ctx.confidence, "steps": len(ctx.rag.step_by_step_steps),
                "sources": ctx.rag.sources_cited, "provider": ctx.rag.provider, "model": ctx.rag.model_name,
                "processing_ms": ctx.rag.processing_time_ms, "unsupported": g.unsupported_detected}


class EscalationAgent(Agent):
    """Decides whether a human must take over, and which team gets it."""
    name = "Escalation Agent"

    def run(self, ctx: AgentContext) -> dict[str, Any]:
        reasons: list[str] = []
        g = ctx.rag.grounding if ctx.rag else None
        if g is None or g.needs_escalation:
            reasons.append((g.escalation_reason if g else None) or "No verified resolution could be generated.")
        if ctx.classification["category"] == "Security":
            reasons.append("Security incidents always require human review.")
        if ctx.triage["severity"] == "Critical":
            reasons.append(f"Critical severity (score {ctx.triage['severity_score']}): {ctx.triage['sla']['escalation']}.")
        if ctx.classification["category"] == "General IT":
            reasons.append("Category could not be determined with confidence.")
        if ctx.rag and not reasons and ctx.confidence < settings.auto_resolve_min_confidence:
            reasons.append(f"Resolution confidence {ctx.confidence:.2f} is below the {settings.auto_resolve_min_confidence:.2f} auto-resolve threshold.")
        escalate = bool(reasons)
        team = TEAM_BY_CATEGORY.get(ctx.classification["category"], "IT Service Desk (Tier 2)")
        ctx.decision = {"escalate": escalate, "team": team if escalate else None, "reason": " ".join(reasons) if escalate else None,
                        "priority": ctx.triage["priority"], "sla": ctx.triage["sla"]}
        return ctx.decision
