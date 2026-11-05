"""Shared agent plumbing: context object and a runner that records every agent run."""
from __future__ import annotations

import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Optional

from ..db.repo import Repository, new_id, now_iso


@dataclass
class AgentContext:
    ticket: dict[str, Any]
    classification: dict[str, Any]
    triage: dict[str, Any]
    ticket_input: Any = None            # rag_pipeline.schemas.TicketInput
    diagnosis: dict[str, Any] = field(default_factory=dict)
    docs: list = field(default_factory=list)          # RetrievedDocument list
    rag: Optional[Any] = None                          # RAGResponse
    decision: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0


class Agent:
    name = "Agent"

    def run(self, ctx: AgentContext) -> dict[str, Any]:  # pragma: no cover - interface
        raise NotImplementedError


def run_agent(agent: Agent, ctx: AgentContext, repo: Repository) -> dict[str, Any]:
    """Execute one agent, time it and persist an agent_runs row. Errors never crash the pipeline."""
    started = now_iso()
    t0 = time.perf_counter()
    try:
        output, status = agent.run(ctx), "completed"
    except Exception as exc:  # noqa: BLE001
        output, status = {"error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc(limit=3)}, "failed"
    ms = round((time.perf_counter() - t0) * 1000, 2)
    repo.insert("agent_runs", {
        "run_id": new_id("RUN"), "ticket_id": ctx.ticket["ticket_id"], "agent_name": agent.name, "status": status,
        "input": {"category": ctx.classification.get("category"), "severity": ctx.triage.get("severity")},
        "output": output, "duration_ms": ms, "started_at": started})
    return {"agent": agent.name, "status": status, "duration_ms": ms, "output": output}
