"""
SupportPilot Integrated RAG Pipeline
====================================
RAG Pipeline
- Connects ticket input with retrieval engine ( ChromaDB module).
- Passes retrieved documents to the LLM as context.
- Generates context-aware troubleshooting answers.
- Adds prompts and guardrails to reduce unsupported answers.
"""

import time
from typing import List, Optional, Union, Dict, Any

from .schemas import TicketInput, RetrievedDocument, RAGResponse, GroundingResult
from .retriever import BaseKnowledgeRetriever, get_default_retriever
from .prompts import STRICT_RAG_SYSTEM_PROMPT, create_rag_prompt
from .llm_service import LLMService, get_llm_service
from .grounding_guardrails import GroundingGuardrail

UNSUPPORTED_RESOLUTION = (
    "UNSUPPORTED_BY_DOCUMENTATION: The available enterprise knowledge base does not "
    "contain verified troubleshooting procedures for this request.\n\n"
    "### Recommended Escalation\n"
    "Route the ticket to the responsible IT support team for manual triage. Include "
    "the exact error message, affected device or service, when the issue started, "
    "and the troubleshooting steps already attempted."
)


class SupportPilotRAGPipeline:
    """
    Production-ready RAG Pipeline integrating semantic retrieval,
    LangChain LLM orchestration, anti-hallucination prompts, and grounding guardrails.
    """

    def __init__(
        self,
        retriever: Optional[BaseKnowledgeRetriever] = None,
        llm_service: Optional[LLMService] = None,
        guardrail: Optional[GroundingGuardrail] = None,
        top_k: int = 3,
        min_similarity_threshold: float = 0.35,
    ):
        self.retriever = retriever or get_default_retriever()
        self.llm_service = llm_service or get_llm_service()
        self.guardrail = guardrail or GroundingGuardrail(
            min_similarity_threshold=min_similarity_threshold
        )
        self.top_k = top_k
        self.min_similarity_threshold = min_similarity_threshold

    def resolve_ticket(self, ticket: Union[TicketInput, Dict[str, Any]]) -> RAGResponse:
        """
        Execute end-to-end RAG resolution for a single support ticket.

        Workflow:
        1. Parse & validate ticket input.
        2. Query retrieval engine (ChromaDB / semantic retriever).
        3. Pass retrieved documents to the LLM as context.
        4. Generate context-aware troubleshooting instructions using strict anti-hallucination prompt.
        5. Evaluate response grounding and verify source citations.
        6. Return complete structured RAGResponse.
        """
        start_time = time.perf_counter()

        if isinstance(ticket, dict):
            ticket_obj = TicketInput(**ticket)
        else:
            ticket_obj = ticket

        # Step 1: Semantic retrieval for ticket
        retrieved_docs: List[RetrievedDocument] = self.retriever.retrieve_for_ticket(
            ticket=ticket_obj,
            top_k=self.top_k,
            similarity_threshold=self.min_similarity_threshold,
        )

        # Do not ask the LLM to improvise when retrieval has no supporting context.
        if not retrieved_docs:
            raw_response = UNSUPPORTED_RESOLUTION
        else:
            # Pass the retrieved chunks to the LLM with strict grounding rules.
            user_prompt = create_rag_prompt(ticket=ticket_obj, documents=retrieved_docs)
            raw_response = self.llm_service.generate(
                system_prompt=STRICT_RAG_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )

        # Reject generated instructions if retrieval confidence or source citations fail.
        grounding_result = self.guardrail.evaluate(
            ticket=ticket_obj,
            response_text=raw_response,
            retrieved_documents=retrieved_docs,
        )
        if "UNSUPPORTED_BY_DOCUMENTATION" in raw_response.upper():
            # Keep explicit refusals canonical so a model cannot append guesses
            # after correctly stating that the KB is insufficient.
            raw_response = UNSUPPORTED_RESOLUTION
            grounding_result = self.guardrail.evaluate(
                ticket=ticket_obj,
                response_text=raw_response,
                retrieved_documents=retrieved_docs,
            )
        elif grounding_result.unsupported_detected:
            raw_response = UNSUPPORTED_RESOLUTION
            grounding_result = self.guardrail.evaluate(
                ticket=ticket_obj,
                response_text=raw_response,
                retrieved_documents=retrieved_docs,
            )

        steps = self.guardrail.extract_steps(raw_response)
        citations = self.guardrail.extract_citations(raw_response)
        retrieval_fallback_used = any(
            document.metadata.get("retrieval_method") == "lexical_fallback"
            for document in retrieved_docs
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return RAGResponse(
            ticket_id=ticket_obj.ticket_id,
            ticket_subject=ticket_obj.subject,
            ticket_category=ticket_obj.category or "General IT",
            resolution=raw_response,
            step_by_step_steps=steps,
            sources_cited=citations,
            retrieved_documents=retrieved_docs,
            grounding=grounding_result,
            model_name=self.llm_service.model_name or "supportpilot-llm",
            provider=getattr(self.llm_service, "provider", "custom"),
            fallback_used=(
                bool(getattr(self.llm_service, "fallback_used", False))
                or retrieval_fallback_used
            ),
            retrieval_count=len(retrieved_docs),
            processing_time_ms=round(elapsed_ms, 2),
        )

    def resolve(
        self,
        subject: str,
        description: str,
        category: Optional[str] = "General IT",
        priority: Optional[str] = "Medium",
        severity: Optional[str] = "Normal",
        ticket_id: Optional[str] = None,
    ) -> RAGResponse:
        """Convenience method accepting raw ticket attributes."""
        ticket = TicketInput(
            ticket_id=ticket_id or f"T-{int(time.time())}",
            subject=subject,
            description=description,
            category=category,
            priority=priority,
            severity=severity,
        )
        return self.resolve_ticket(ticket)

    def batch_resolve(
        self, tickets: List[Union[TicketInput, Dict[str, Any]]]
    ) -> List[RAGResponse]:
        """Resolve a batch of incoming tickets."""
        return [self.resolve_ticket(t) for t in tickets]


def get_rag_pipeline(
    retriever: Optional[BaseKnowledgeRetriever] = None,
    llm_service: Optional[LLMService] = None,
) -> SupportPilotRAGPipeline:
    """Factory helper to obtain an initialized RAG pipeline instance."""
    return SupportPilotRAGPipeline(retriever=retriever, llm_service=llm_service)
