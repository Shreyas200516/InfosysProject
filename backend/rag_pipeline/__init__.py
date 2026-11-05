"""
SupportPilot RAG Pipeline Module
================================
Deliverable: Retrieval and LLM Integration
- Connects ticket input with semantic retrieval engine.
- Formats and passes retrieved knowledge chunks as prompt context.
- Generates context-aware, step-by-step IT troubleshooting solutions.
- Incorporates strict anti-hallucination prompts to eliminate unsupported answers.
- Implements grounding guardrails and automated escalation triggers.
"""

from .schemas import TicketInput, RetrievedDocument, RAGResponse, GroundingResult
from .retriever import (
    BaseKnowledgeRetriever,
    ChromaKnowledgeRetriever,
    InMemoryKnowledgeRetriever,
)
from .prompts import (
    STRICT_RAG_SYSTEM_PROMPT,
    TICKET_RAG_PROMPT_TEMPLATE,
    create_rag_prompt,
)
from .llm_service import LLMService, get_llm_service
from .grounding_guardrails import GroundingGuardrail
from .rag_pipeline import SupportPilotRAGPipeline, get_rag_pipeline

__all__ = [
    "TicketInput",
    "RetrievedDocument",
    "RAGResponse",
    "GroundingResult",
    "BaseKnowledgeRetriever",
    "ChromaKnowledgeRetriever",
    "InMemoryKnowledgeRetriever",
    "STRICT_RAG_SYSTEM_PROMPT",
    "TICKET_RAG_PROMPT_TEMPLATE",
    "create_rag_prompt",
    "LLMService",
    "get_llm_service",
    "GroundingGuardrail",
    "SupportPilotRAGPipeline",
    "get_rag_pipeline",
]
