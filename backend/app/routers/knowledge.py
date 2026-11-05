from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import current_user, staff_only
from rag_pipeline.schemas import TicketInput

from ..schemas import AnalyzeRequest, SearchRequest
from ..services.classifier import get_classifier
from ..services.knowledge import get_knowledge

router = APIRouter(prefix="/api/v1", tags=["knowledge"])


@router.get("/knowledge/articles")
def articles(user=Depends(current_user)):
    kb = get_knowledge()
    return {"retrieval_mode": kb.mode, "items": kb.list_articles()}


@router.post("/knowledge/search")
def search(body: SearchRequest, user=Depends(current_user)):
    """Semantic search: top relevant knowledge-base chunks for a free-text query."""
    kb = get_knowledge()
    docs = kb.search(body.query, top_k=body.top_k)
    return {"retrieval_mode": kb.mode, "items": [d.model_dump() for d in docs]}


@router.post("/rag/resolve")
def resolve(body: AnalyzeRequest, user=Depends(staff_only)):
    """RAG preview (nothing stored): retrieve, generate cited steps, run guardrails."""
    kb = get_knowledge()
    text = f"{body.subject}. {body.description}".strip()
    cat = get_classifier().predict(text)["category"]
    rag = kb.resolve(TicketInput(ticket_id="PREVIEW", subject=body.subject or text[:80], description=body.description or text, category=cat))
    return {"category": cat, "retrieval_mode": kb.mode, **rag.model_dump()}
