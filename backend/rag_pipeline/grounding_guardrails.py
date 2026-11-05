"""Post-generation checks for citations, relevance, and unsupported answers."""

import re
from typing import List

from .schemas import GroundingResult, RetrievedDocument, TicketInput


class GroundingGuardrail:
    """Check that generated troubleshooting is supported by retrieved chunks."""

    def __init__(self, min_similarity_threshold: float = 0.30) -> None:
        self.min_similarity_threshold = min_similarity_threshold

    def evaluate(
        self,
        ticket: TicketInput,
        response_text: str,
        retrieved_documents: List[RetrievedDocument],
    ) -> GroundingResult:
        if not retrieved_documents:
            return GroundingResult(
                is_grounded=False,
                confidence_score=0.0,
                unsupported_detected=True,
                needs_escalation=True,
                escalation_reason="No relevant knowledge base articles were retrieved.",
                cited_sources_valid=False,
            )

        if "UNSUPPORTED_BY_DOCUMENTATION" in response_text.upper():
            return GroundingResult(
                is_grounded=False,
                confidence_score=0.0,
                unsupported_detected=True,
                needs_escalation=True,
                escalation_reason="The available documentation does not support a verified resolution.",
                cited_sources_valid=True,
            )

        max_relevance = max(doc.relevance_score for doc in retrieved_documents)
        if max_relevance < self.min_similarity_threshold:
            return GroundingResult(
                is_grounded=False,
                confidence_score=round(max_relevance, 2),
                unsupported_detected=True,
                needs_escalation=True,
                escalation_reason=(
                    f"Top retrieved relevance ({max_relevance:.2f}) is below the "
                    f"required threshold ({self.min_similarity_threshold:.2f})."
                ),
                cited_sources_valid=False,
            )

        citations = self.extract_citations(response_text)
        steps = self.extract_steps(response_text)

        def citation_is_known(citation: str) -> bool:
            return any(
                self._citation_matches_document(citation, doc)
                for doc in retrieved_documents
            )

        citations_valid = bool(citations) and all(citation_is_known(item) for item in citations)
        steps_are_cited = bool(steps) and all(
            self.extract_citations(line)
            and all(citation_is_known(item) for item in self.extract_citations(line))
            and self._step_has_exact_evidence(line, retrieved_documents)
            for line in response_text.splitlines()
            if re.match(r"^\s*\d+[.)]\s+", line)
        )
        # SupportPilot change: the ticket-relevance check applies to the answer as a whole
        # (generic steps such as "contact IT support" legitimately share no keyword with a ticket).
        steps_are_cited = steps_are_cited and any(
            self._step_matches_ticket(line, ticket)
            for line in response_text.splitlines()
            if re.match(r"^\s*\d+[.)]\s+", line)
        )
        citations_valid = citations_valid and steps_are_cited

        confidence = max(0.0, min(1.0, max_relevance))
        if not citations_valid:
            confidence *= 0.5
        grounded = citations_valid and confidence >= max(0.5, self.min_similarity_threshold)

        return GroundingResult(
            is_grounded=grounded,
            confidence_score=round(confidence, 2),
            unsupported_detected=not grounded,
            needs_escalation=not grounded,
            escalation_reason=(
                None
                if grounded
                else "The answer lacks valid citations for its troubleshooting instructions, or retrieval confidence is low."
            ),
            cited_sources_valid=citations_valid,
        )

    @staticmethod
    def extract_citations(text: str) -> List[str]:
        """Return citation values from ``[Source: ...]`` references."""
        return [
            value.strip()
            for value in re.findall(r"\[Source:\s*([^\]]+)\]", text, re.IGNORECASE)
            if value.strip()
        ]

    @staticmethod
    def extract_steps(text: str) -> List[str]:
        """Extract numbered troubleshooting instructions from generated text."""
        steps: List[str] = []
        for line in text.splitlines():
            line = line.strip()
            if re.match(r"^\d+[.)]\s+", line):
                steps.append(re.sub(r"^\d+[.)]\s+", "", line))
        return steps

    @staticmethod
    def _step_has_exact_evidence(line: str, documents: List[RetrievedDocument]) -> bool:
        citations = GroundingGuardrail.extract_citations(line)
        match = re.search(r"\[Evidence:\s*(.+?)\]\s*$", line, re.IGNORECASE)
        if len(citations) != 1 or not match:
            return False
        evidence = GroundingGuardrail._normalize_text(match.group(1))
        action = re.sub(r"\[Source:.*?\]", "", line, flags=re.IGNORECASE)
        action = re.sub(r"\[Evidence:.*?\]", "", action, flags=re.IGNORECASE)
        action = re.sub(r"^\s*\d+[.)]\s+", "", action).strip()
        normalized_action = GroundingGuardrail._normalize_text(action)
        return normalized_action == evidence and any(
            GroundingGuardrail._citation_matches_document(citations[0], doc)
            and evidence in GroundingGuardrail._normalize_text(doc.content)
            for doc in documents
        )

    @staticmethod
    def _normalize_text(value: str) -> str:
        return " ".join(value.split()).casefold()

    @staticmethod
    def _citation_matches_document(citation: str, document: RetrievedDocument) -> bool:
        normalized = GroundingGuardrail._normalize_text(citation)
        references = {
            GroundingGuardrail._normalize_text(value)
            for value in (
                document.title,
                document.doc_id,
                document.source,
                str(document.metadata.get("document_id", "")),
            )
            if value and value.strip()
        }
        return normalized in references

    @staticmethod
    def _step_matches_ticket(line: str, ticket: TicketInput) -> bool:
        # Basic consistency check only; exact evidence remains the primary gate.
        action = re.sub(r"\[Source:.*?\]", "", line, flags=re.IGNORECASE)
        action = re.sub(r"\[Evidence:.*?\]", "", action, flags=re.IGNORECASE)
        action = re.sub(r"^\s*\d+[.)]\s+", "", action).strip()
        text = f"{ticket.subject} {ticket.description} {ticket.category or ''}".casefold()
        terms = {
            GroundingGuardrail._normalize_ticket_term(term)
            for term in re.findall(r"[a-z0-9]{3,}", text)
        }
        step_terms = {
            GroundingGuardrail._normalize_ticket_term(term)
            for term in re.findall(r"[a-z0-9]{3,}", action.casefold())
        }
        generic = {
            "check", "follow", "restart", "verify", "contact", "source", "evidence",
            "service", "services", "system", "systems", "issue", "issues", "problem",
            "problems", "support", "help", "user", "users", "ticket", "tickets",
            "guide", "article", "step", "steps", "troubleshooting", "the", "and",
            "for", "are", "can", "you", "your", "with", "from", "this", "that",
            "then", "into", "when", "where", "what", "were", "was", "has", "have",
            "does", "not", "but", "all", "new", "out",
        }
        meaningful_ticket_terms = terms - generic
        meaningful_step_terms = step_terms - generic
        return bool(meaningful_ticket_terms & meaningful_step_terms)

    @staticmethod
    def _normalize_ticket_term(term: str) -> str:
        return {
            "connection": "connect",
            "connections": "connect",
            "connected": "connect",
            "connecting": "connect",
            "connectivity": "connect",
            "connects": "connect",
            "failure": "fail",
            "failures": "fail",
            "failed": "fail",
            "failing": "fail",
            "fails": "fail",
        }.get(term, term)
