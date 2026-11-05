"""
SupportPilot RAG Pipeline Test Suite
====================================
Tests for RAG Pipeline deliverable.
Verifies:
1. Connection of ticket input to retrieval engine.
2. Retrieval and context augmentation into LLM prompts.
3. Context-aware answer generation with step-by-step instructions.
4. Anti-hallucination prompt enforcement on unsupported / out-of-domain queries.
5. Accurate source reference citations.
6. Grounding guardrails and automatic escalation triggers.
"""

import pytest
from rag_pipeline.schemas import TicketInput, RAGResponse, RetrievedDocument
from rag_pipeline.retriever import InMemoryKnowledgeRetriever
from rag_pipeline.prompts import (
    create_rag_prompt,
    format_retrieved_context,
    STRICT_RAG_SYSTEM_PROMPT,
)
from rag_pipeline.grounding_guardrails import GroundingGuardrail
from rag_pipeline.rag_pipeline import SupportPilotRAGPipeline
from rag_pipeline.llm_service import LLMService


@pytest.fixture
def rag_pipeline():
    """Use local chunks and the deterministic generator for repeatable tests."""
    return SupportPilotRAGPipeline(
        retriever=InMemoryKnowledgeRetriever(),
        llm_service=LLMService(provider="offline"),
    )


class TestTicketIntakeAndRetrieval:
    """Tests requirement: Connect ticket input with retrieval engine."""

    def test_ticket_input_creation(self):
        ticket = TicketInput(
            ticket_id="T-2026-001",
            subject="VPN connection timeout",
            description="Unable to connect to GlobalProtect corporate VPN gateway",
            category="VPN",
            priority="High",
            severity="P2",
        )
        assert ticket.ticket_id == "T-2026-001"
        assert "VPN connection timeout" in ticket.full_query
        assert "GlobalProtect" in ticket.full_query

    def test_retriever_returns_relevant_vpn_document(self):
        retriever = InMemoryKnowledgeRetriever()
        ticket = TicketInput(
            ticket_id="T-2026-002",
            subject="VPN Connection Failing on Corporate Network",
            description="GlobalProtect client reports timeout trying to reach vpn.corp.company.com",
            category="VPN",
        )
        docs = retriever.retrieve_for_ticket(ticket, top_k=3)
        assert len(docs) > 0
        top_doc = docs[0]
        assert "VPN" in top_doc.category or "VPN" in top_doc.title
        assert top_doc.relevance_score > 0.0

    def test_retriever_returns_printer_document(self):
        retriever = InMemoryKnowledgeRetriever()
        ticket = TicketInput(
            ticket_id="T-2026-003",
            subject="Printer Not Responding",
            description="Network office printer in 3rd floor shows offline and jobs are stuck in print spooler",
            category="Hardware",
        )
        docs = retriever.retrieve_for_ticket(ticket, top_k=2)
        assert len(docs) > 0
        assert any("print" in d.title.lower() for d in docs)


class TestContextPassingAndPrompts:
    """Tests requirement: Pass retrieved documents to the LLM as context."""

    def test_format_retrieved_context(self):
        docs = [
            RetrievedDocument(
                doc_id="KB-TEST-01",
                title="Test Guide",
                category="Network",
                source="SOP-01",
                content="Step 1: Check cable.",
                relevance_score=0.95,
            )
        ]
        context_str = format_retrieved_context(docs)
        assert "KB-TEST-01" in context_str
        assert "Test Guide" in context_str
        assert "Step 1: Check cable." in context_str

    def test_create_rag_prompt_injects_ticket_and_context(self):
        ticket = TicketInput(
            ticket_id="T-2026-004",
            subject="Outlook mailbox sync error",
            description="OST file appears corrupt, Outlook freezing on launch",
            category="Software",
        )
        docs = [
            RetrievedDocument(
                doc_id="KB-SFT-005",
                title="Outlook OST Rebuild",
                category="Software",
                source="SOP-APP-03",
                content="Rename .ost to .ost.bak and restart Outlook.",
                relevance_score=0.90,
            )
        ]
        prompt = create_rag_prompt(ticket, docs)
        assert "Outlook mailbox sync error" in prompt
        assert "KB-SFT-005" in prompt
        assert "Rename .ost to .ost.bak" in prompt


class TestRAGPipelineExecution:
    """Tests requirement: Generate context-aware answers."""

    def test_resolve_vpn_ticket_end_to_end(self, rag_pipeline):
        ticket = TicketInput(
            ticket_id="T-2026-4521",
            subject="VPN Connection Failing on Corporate Network",
            description="Unable to connect to VPN since this morning. Error message: Connection timed out.",
            category="VPN",
            priority="High",
            severity="P1",
        )

        response: RAGResponse = rag_pipeline.resolve_ticket(ticket)

        assert response.ticket_id == "T-2026-4521"
        assert response.retrieval_count > 0
        assert len(response.step_by_step_steps) > 0
        assert len(response.sources_cited) > 0
        assert response.grounding.is_grounded is True
        assert response.grounding.confidence_score >= 0.5
        assert response.processing_time_ms > 0

    def test_resolve_password_reset_ticket(self, rag_pipeline):
        response = rag_pipeline.resolve(
            subject="Password Reset Required / Account Locked",
            description="User entered wrong password multiple times, Active Directory account is locked",
            category="Access/Account",
        )
        assert response.retrieval_count > 0
        assert any("password" in s.lower() for s in response.step_by_step_steps)
        assert response.grounding.needs_escalation is False


class TestAntiHallucinationAndUnsupportedPrompts:
    """Tests requirement: Add prompts to reduce unsupported answers."""

    def test_unsupported_out_of_domain_ticket_refusal(self, rag_pipeline):
        """A ticket with zero matching IT SOPs must refuse and escalate instead of hallucinating."""
        ticket = TicketInput(
            ticket_id="T-2026-9999",
            subject="How to make homemade sourdough pizza crust",
            description="Need recipe for high hydration sourdough pizza dough and oven temperature",
            category="Unknown",
        )

        response = rag_pipeline.resolve_ticket(ticket)

        assert (
            response.retrieval_count == 0
            or "UNSUPPORTED_BY_DOCUMENTATION" in response.resolution
        )
        assert response.grounding.needs_escalation is True
        assert response.grounding.unsupported_detected is True

    def test_guardrail_detects_low_relevance_threshold(self):
        guardrail = GroundingGuardrail(min_similarity_threshold=0.80)
        ticket = TicketInput(
            ticket_id="T-TEST-005",
            subject="Obscure unknown protocol failure",
            description="Error XYZ-9999 occurred",
        )
        docs = [
            RetrievedDocument(
                doc_id="KB-LOW-01",
                title="Generic Guide",
                content="Some irrelevant text",
                relevance_score=0.32,  # Below 0.80 threshold
            )
        ]
        result = guardrail.evaluate(ticket, "Generic response", docs)
        assert result.needs_escalation is True
        assert result.unsupported_detected is True

    def test_guardrail_rejects_step_without_exact_evidence(self):
        guardrail = GroundingGuardrail(min_similarity_threshold=0.3)
        ticket = TicketInput(
            subject="VPN connection fails", description="VPN connection times out"
        )
        docs = [
            RetrievedDocument(
                doc_id="VPN-1",
                title="VPN guide",
                content="Restart the VPN client.",
                relevance_score=0.9,
            )
        ]
        result = guardrail.evaluate(
            ticket,
            "1. Run an unrelated destructive command. [Source: VPN guide]",
            docs,
        )
        assert result.unsupported_detected is True
        assert result.needs_escalation is True

    def test_guardrail_requires_evidence_matching_ticket(self):
        guardrail = GroundingGuardrail(min_similarity_threshold=0.3)
        ticket = TicketInput(
            subject="VPN connection fails", description="VPN connection times out"
        )
        docs = [
            RetrievedDocument(
                doc_id="VPN-1",
                title="VPN guide",
                content="Restart the printer service.",
                relevance_score=0.9,
            )
        ]
        result = guardrail.evaluate(
            ticket,
            "1. Restart the printer service. [Source: VPN guide] [Evidence: Restart the printer service.]",
            docs,
        )
        assert result.unsupported_detected is True
