"""Knowledge retrieval + RAG pipeline factory (wraps the team's rag_pipeline package)."""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Any, List, Optional

from rag_pipeline.grounding_guardrails import GroundingGuardrail
from rag_pipeline.llm_service import LLMService, get_llm_service
from rag_pipeline.rag_pipeline import SupportPilotRAGPipeline
from rag_pipeline.retriever import (
    BaseKnowledgeRetriever, ChromaKnowledgeRetriever,
)
from rag_pipeline.schemas import RetrievedDocument, TicketInput

from ..config import BACKEND_DIR, settings

KB_CSV = BACKEND_DIR / "data" / "knowledge_base_combined.csv"
CHROMA_THRESHOLD = 0.35   # cosine similarity (MiniLM) - the team's default
TFIDF_THRESHOLD = 0.20    # TF-IDF cosine scores are lower than embedding similarity


class TfidfKnowledgeRetriever(BaseKnowledgeRetriever):
    """Local cosine-similarity retriever (scikit-learn). Used when the ChromaDB index / embedding
    model is unavailable. Robust to long tickets, unlike the lexical-overlap fallback."""

    def __init__(self, csv_path: Path = KB_CSV):
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.rows: list[dict[str, str]] = []
        if csv_path.is_file():
            with csv_path.open(encoding="utf-8-sig", newline="") as f:
                self.rows = [r for r in csv.DictReader(f) if (r.get("content") or "").strip()]
        self.vec = TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        self.matrix = self.vec.fit_transform([f"{r['title']} {r['title']} {r['category']} {r['content']}" for r in self.rows]) if self.rows else None

    def search(self, query, top_k=3, category=None, similarity_threshold=0.2):
        if self.matrix is None or not (query or "").strip():
            return []
        sims = (self.matrix @ self.vec.transform([query]).T).toarray().ravel()
        order = sims.argsort()[::-1][:top_k]
        out = []
        for i in order:
            if sims[i] < similarity_threshold:
                continue
            r = self.rows[i]
            # Calibrate raw cosine onto the embedding-similarity scale the guardrail expects:
            # the retrieval threshold maps to the guardrail's 0.5 floor, 0.5 raw cosine maps to 1.0.
            calibrated = min(1.0, 0.5 + (float(sims[i]) - similarity_threshold) * (0.5 / max(0.05, 0.5 - similarity_threshold)))
            out.append(RetrievedDocument(
                doc_id=r["chunk_id"], title=r["title"], content=r["content"], category=r.get("category") or "General IT",
                source=r.get("source") or "Knowledge Base", relevance_score=round(calibrated, 4),
                metadata={"document_id": r.get("document_id", ""), "retrieval_method": "tfidf_cosine", "raw_cosine": round(float(sims[i]), 4)}))
        return out


class StaticRetriever(BaseKnowledgeRetriever):
    """Returns documents an upstream agent already retrieved (avoids a second search)."""

    def __init__(self, docs: List[RetrievedDocument]):
        self.docs = docs

    def search(self, query, top_k=3, category=None, similarity_threshold=0.35):
        return list(self.docs)


class KnowledgeService:
    def __init__(self):
        chroma = ChromaKnowledgeRetriever(persist_directory=settings.chroma_path)
        self.uses_chroma = chroma.collection is not None
        self.retriever: BaseKnowledgeRetriever = chroma if self.uses_chroma else TfidfKnowledgeRetriever()
        self.threshold = CHROMA_THRESHOLD if self.uses_chroma else TFIDF_THRESHOLD
        self.llm: LLMService = get_llm_service()
        self.guardrail = GroundingGuardrail(min_similarity_threshold=self.threshold)

    @property
    def mode(self) -> str:
        return "chromadb" if self.uses_chroma else "tfidf_fallback"

    def search(self, query: str, top_k: Optional[int] = None, category: Optional[str] = None) -> List[RetrievedDocument]:
        k = top_k or settings.top_k
        docs = self.retriever.search(query=query, top_k=k, category=None, similarity_threshold=self.threshold)
        return docs

    def resolve(self, ticket: TicketInput, docs: Optional[List[RetrievedDocument]] = None):
        """Run the team's RAG pipeline. If `docs` is given they are used as the context."""
        retriever = StaticRetriever(docs) if docs is not None else self.retriever
        pipe = SupportPilotRAGPipeline(retriever=retriever, llm_service=self.llm, guardrail=self.guardrail,
                                       top_k=settings.top_k, min_similarity_threshold=self.threshold)
        return pipe.resolve_ticket(ticket)

    def list_articles(self) -> list[dict[str, Any]]:
        path = KB_CSV
        if not path.is_file():
            return []
        with path.open(encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def get_knowledge() -> KnowledgeService:
    return KnowledgeService()
