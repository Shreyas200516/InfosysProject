"""Retrieval adapters for the SupportPilot knowledge base.

The primary adapter reads the Chroma collection created by
``semantic_search/build_vector_database.py``. If that index is unavailable, it
uses the prepared  CSV chunks for a lightweight local fallback; it never
silently substitutes a separate, hard-coded knowledge base.
"""

from __future__ import annotations

import csv
import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schemas import RetrievedDocument, TicketInput

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VECTOR_STORE = PROJECT_ROOT / "semantic_search" / "chroma_db"
DEFAULT_COLLECTION_NAME = "supportpilot_knowledge_base"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


class BaseKnowledgeRetriever(ABC):
    """Interface between ticket intake and semantic search."""

    @abstractmethod
    def search(
        self,
        query: str,
        top_k: int = 3,
        category: Optional[str] = None,
        similarity_threshold: float = 0.35,
    ) -> List[RetrievedDocument]:
        """Return the most relevant knowledge chunks for a query."""

    def retrieve_for_ticket(
        self,
        ticket: TicketInput,
        top_k: int = 3,
        similarity_threshold: float = 0.35,
    ) -> List[RetrievedDocument]:
        """Build a search query from the ticket and retrieve relevant chunks."""
        return self.search(
            query=f"{ticket.category or ''} - {ticket.full_query}",
            top_k=top_k,
            category=None,
            similarity_threshold=similarity_threshold,
        )


def _prepared_chunks_path() -> Path:
    # Combined KB (team chunks + SupportPilot extension articles) takes priority.
    combined = PROJECT_ROOT / "data" / "knowledge_base_combined.csv"
    if combined.is_file():
        return combined
    return (
        PROJECT_ROOT
        / "knowledge_base_preparation"
        / "data"
        / "knowledge_base_chunks.csv"
    )


def _load_prepared_chunks(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load prepared chunks using the dataset's documented schema."""
    csv_path = path or _prepared_chunks_path()
    if not csv_path.is_file():
        return []

    documents: List[Dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            content = (row.get("content") or "").strip()
            chunk_id = (row.get("chunk_id") or row.get("document_id") or "").strip()
            if not content or not chunk_id:
                continue
            documents.append(
                {
                    "doc_id": chunk_id,
                    "title": (row.get("title") or "IT Troubleshooting Guide").strip(),
                    "category": (row.get("category") or "General IT").strip(),
                    "source": (row.get("source") or "Knowledge Base").strip(),
                    "content": content,
                    "tags": row.get("tags") or "",
                    "metadata": {
                        key: value
                        for key, value in row.items()
                        if key not in {"content", "tags"} and value is not None
                    },
                }
            )
    return documents


class ChromaKnowledgeRetriever(BaseKnowledgeRetriever):
    """Query the ChromaDB index with matching embeddings."""

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None,
        embedding_model_name: str = EMBEDDING_MODEL_NAME,
    ) -> None:
        self.persist_directory = Path(
            persist_directory
            or os.getenv("SUPPORTPILOT_CHROMA_PATH")
            or DEFAULT_VECTOR_STORE
        )
        self.collection_name = (
            collection_name
            or os.getenv("SUPPORTPILOT_CHROMA_COLLECTION")
            or DEFAULT_COLLECTION_NAME
        )
        self.embedding_model_name = embedding_model_name
        self.client = None
        self.collection = None
        self._embedding_model = None
        self._init_chroma()

    def _init_chroma(self) -> None:
        """Open the existing collection without creating a shadow DB."""
        if not self.persist_directory.is_dir():
            return
        try:
            import chromadb

            self.client = chromadb.PersistentClient(path=str(self.persist_directory))
            self.collection = self.client.get_collection(name=self.collection_name)
        except Exception:
            # The prepared CSV fallback remains available if Chroma is missing,
            # incomplete, or has not yet been built.
            self.client = None
            self.collection = None

    def _get_embedding_model(self):
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer

            self._embedding_model = SentenceTransformer(self.embedding_model_name)
        return self._embedding_model

    def search(
        self,
        query: str,
        top_k: int = 3,
        category: Optional[str] = None,
        similarity_threshold: float = 0.35,
    ) -> List[RetrievedDocument]:
        query = (query or "").strip()
        if not query or top_k <= 0:
            return []

        if self.collection is not None:
            try:
                count = self.collection.count()
                if count:
                    embedding = self._get_embedding_model().encode(query).tolist()
                    results = self.collection.query(
                        query_embeddings=[embedding],
                        n_results=min(top_k, count),
                        include=["documents", "metadatas", "distances"],
                    )
                    return self._convert_results(results, similarity_threshold)
            except Exception:
                # Fall through to the prepared chunks if the vector index cannot
                # be queried, for example when its model is not installed.
                pass

        return InMemoryKnowledgeRetriever().search(
            query=query,
            top_k=top_k,
            category=category,
            similarity_threshold=similarity_threshold,
        )

    @staticmethod
    def _convert_results(
        results: Dict[str, Any], similarity_threshold: float
    ) -> List[RetrievedDocument]:
        docs = (results.get("documents") or [[]])[0] or []
        ids = (results.get("ids") or [[]])[0] or []
        metadatas = (results.get("metadatas") or [[]])[0] or [{} for _ in docs]
        distances = (results.get("distances") or [[]])[0] or [1.0 for _ in docs]

        retrieved: List[RetrievedDocument] = []
        for doc_id, content, metadata, distance in zip(ids, docs, metadatas, distances):
            metadata = metadata or {}
            # Chroma's cosine space, whose distance is
            # 1 - cosine similarity.
            similarity = max(0.0, min(1.0, 1.0 - float(distance)))
            if similarity < similarity_threshold:
                continue

            tags = metadata.get("tags", "")
            if isinstance(tags, str):
                tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
            elif not isinstance(tags, list):
                tags = []

            retrieved.append(
                RetrievedDocument(
                    doc_id=str(doc_id),
                    title=str(metadata.get("title") or "IT Troubleshooting Guide"),
                    category=str(metadata.get("category") or "General IT"),
                    source=str(metadata.get("source") or "Knowledge Base"),
                    content=str(content or ""),
                    tags=tags,
                    relevance_score=round(similarity, 4),
                    metadata={**metadata, "retrieval_method": "chroma"},
                )
            )
        return retrieved


class InMemoryKnowledgeRetriever(BaseKnowledgeRetriever):
    """Small lexical fallback over the actual prepared chunks."""

    _STOP_WORDS = frozenset(
        "a an and are as at be by can for from has have how i in is it of on or "
        "that the this to was were what when where which with you your issue issues "
        "error errors problem problems help support ticket user unable please "
        "work working not no never".split()
    )
    _TERM_NORMALIZATION = {
        "connection": "connect",
        "connections": "connect",
        "connected": "connect",
        "connecting": "connect",
        "connectivity": "connect",
        "connects": "connect",
        "reconnect": "connect",
        "reconnected": "connect",
        "reconnecting": "connect",
        "failure": "fail",
        "failures": "fail",
        "failed": "fail",
        "failing": "fail",
        "fails": "fail",
    }

    def __init__(self, documents: Optional[List[Dict[str, Any]]] = None) -> None:
        self.documents = documents if documents is not None else _load_prepared_chunks()

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        # Use specific terms so generic ticket language cannot make an unrelated
        # KB article appear relevant in the CSV fallback.
        tokens = set(re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", text.lower()))
        normalized = {
            InMemoryKnowledgeRetriever._TERM_NORMALIZATION.get(token, token)
            for token in tokens
        }
        return normalized - InMemoryKnowledgeRetriever._STOP_WORDS

    def search(
        self,
        query: str,
        top_k: int = 3,
        category: Optional[str] = None,
        similarity_threshold: float = 0.20,
    ) -> List[RetrievedDocument]:
        query_tokens = self._tokenize(query or "")
        if not query_tokens or top_k <= 0:
            return []

        scored: List[tuple[float, Dict[str, Any]]] = []
        # Keep fallback relevance on a bounded scale: query coverage measures
        # how much of the ticket matched, while title/tag precision rewards
        # focused matches without turning one incidental word into 1.0.
        for doc in self.documents:
            if (
                category
                and category.casefold() != str(doc.get("category", "")).casefold()
            ):
                continue
            tags = doc.get("tags", "")
            if isinstance(tags, list):
                tags_text = " ".join(str(tag) for tag in tags)
            else:
                tags_text = str(tags)
            title_tokens = self._tokenize(str(doc.get("title", "")))
            tag_tokens = self._tokenize(tags_text)
            content_tokens = self._tokenize(str(doc.get("content", "")))
            doc_tokens = title_tokens | tag_tokens | content_tokens
            overlap = query_tokens & doc_tokens
            if not overlap:
                continue

            query_size = max(1, len(query_tokens))
            score = (
                0.50 * len(query_tokens & content_tokens) / query_size
                + 0.35 * len(query_tokens & title_tokens) / max(1, len(title_tokens))
                + 0.15 * len(query_tokens & tag_tokens) / max(1, len(tag_tokens))
            )
            if score >= similarity_threshold:
                scored.append((min(1.0, score), doc))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            RetrievedDocument(
                doc_id=str(doc.get("doc_id", "")),
                title=str(doc.get("title") or "IT Troubleshooting Guide"),
                category=str(doc.get("category") or "General IT"),
                source=str(doc.get("source") or "Knowledge Base"),
                content=str(doc.get("content") or ""),
                tags=(
                    doc.get("tags", [])
                    if isinstance(doc.get("tags", []), list)
                    else [
                        tag.strip()
                        for tag in str(doc.get("tags", "")).split(",")
                        if tag.strip()
                    ]
                ),
                relevance_score=round(score, 4),
                metadata={
                    **(doc.get("metadata") or {}),
                    "retrieval_method": "lexical_fallback",
                },
            )
            for score, doc in scored[:top_k]
        ]


def get_default_retriever() -> BaseKnowledgeRetriever:
    """Use  Chroma index, with prepared chunks as a safe fallback."""
    return ChromaKnowledgeRetriever()
