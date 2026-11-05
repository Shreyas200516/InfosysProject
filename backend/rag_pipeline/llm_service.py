"""
SupportPilot LLM Integration Service
====================================
Integrates LLM generation with LangChain.
Supports OpenAI (gpt-4o-mini, gpt-3.5-turbo), Groq (llama-3.1-8b-instant, llama-3.3-70b-versatile),
and a built-in deterministic OfflineGroundedLLM to ensure full functionality without external API dependencies.
"""

import os
import re
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()
# Also ensure .env from project root is explicitly loaded
_root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
if os.path.exists(_root_env):
    load_dotenv(_root_env, override=True)


class OfflineGroundedLLM:
    """
    Deterministic rule-based LLM engine for offline verification and testing.
    Strictly simulates an LLM obeying the anti-hallucination prompt:
    - If no relevant context is present -> Outputs UNSUPPORTED_BY_DOCUMENTATION with escalation path.
    - If relevant context is present -> Generates step-by-step resolution referencing only the context SOPs.
    """

    def __init__(self, model_name: str = "offline-grounded-generator"):
        self.model_name = model_name
        self.fallback_used = False
        self.last_error: Optional[str] = None

    def invoke(self, system_prompt: str, user_prompt: str) -> str:
        # Check if the prompt contains context documents
        has_docs = "--- REFERENCE DOCUMENT" in user_prompt
        no_docs = "NO RELEVANT KNOWLEDGE BASE ARTICLES FOUND" in user_prompt

        if no_docs or not has_docs:
            return (
                "UNSUPPORTED_BY_DOCUMENTATION: The available enterprise knowledge base does not contain "
                "verified troubleshooting procedures for this request.\n\n"
                "### Recommended Escalation\n"
                "- **Escalate To**: IT Tier 2 Support / Systems Engineering\n"
                "- **Action**: Route ticket to human support engineer for manual triage.\n"
                "- **Required User Information**: Please attach screenshot of any error code, OS version, "
                "and timestamp of failure."
            )

        # Extract document title and content from prompt
        doc_matches = re.findall(
            r"--- REFERENCE DOCUMENT \[\d+\] ---\s+Doc ID: (.*?)\s+Title: (.*?)\s+Category: (.*?)\s+Source SOP: (.*?)\s+Relevance Score: (.*?)\s+Content:\s+(.*?)(?=(?:--- REFERENCE DOCUMENT|TASK:|$))",
            user_prompt,
            re.DOTALL
        )

        if not doc_matches:
            return (
                "UNSUPPORTED_BY_DOCUMENTATION: Could not parse reference documentation in context.\n"
                "Escalating ticket to IT Tier 2 Support."
            )

        # Use the most relevant document (top match)
        top_doc_id, top_title, top_category, top_source, top_score, top_content = doc_matches[0]
        top_title = top_title.strip()
        top_source = top_source.strip()
        top_content = top_content.strip()

        # Extract lines from content
        sop_lines = [line.strip() for line in top_content.split("\n") if line.strip()]
        steps = [line for line in sop_lines if re.match(r"^\d+\.", line)]

        # Extract escalation notes if present
        escalation_line = next(
            (line for line in sop_lines if "Escalation Criteria:" in line or "escalate" in line.lower()),
            "The retrieved documentation does not specify an escalation trigger. Route the ticket to human IT support if the documented steps do not resolve the issue."
        )
        verification_lines = [
            line for line in sop_lines
            if any(term in line.casefold() for term in ("verify", "confirm", "test", "check"))
            and not re.match(r"^\d+\.", line)
        ]

        # Build grounded response
        response_parts = [
            "### Diagnosis Summary",
            f"The most relevant retrieved procedure is '{top_title}'.",
            "",
            "### Step-by-Step Resolution Workflow"
        ]

        if steps:
            for step in steps:
                evidence = re.sub(r"^\d+\.\s*", "", step).strip()
                response_parts.append(f"{step} [Source: {top_title}] [Evidence: {evidence}]")
        else:
            evidence = re.split(r"(?<=[.!?])\s+", top_content, maxsplit=1)[0].strip()
            response_parts.append(
                f"1. {evidence} [Source: {top_title}] [Evidence: {evidence}]"
            )

        response_parts.extend([
            "",
            "### Verification & Confirmation",
            (
                " ".join(verification_lines)
                if verification_lines
                else "The retrieved documentation does not specify a verification procedure."
            ),
            "",
            "### Escalation Trigger",
            f"{escalation_line}"
        ])

        return "\n".join(response_parts)


class LLMService:
    """Manages LLM API connections and prompt execution via LangChain."""

    def __init__(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.0
    ):
        self.provider = provider or os.getenv("LLM_PROVIDER", "auto").lower()
        self.temperature = temperature
        self.model_name = model_name
        self.client = None
        self._system_message_class = None
        self._human_message_class = None
        self._setup_client()

    def _setup_client(self):
        openai_key = os.getenv("OPENAI_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")

        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if self.provider not in {"auto", "offline", "openai", "groq", "anthropic"}:
            raise ValueError("LLM_PROVIDER must be auto, offline, anthropic, openai, or groq.")

        if self.provider == "offline":
            self._setup_offline_client()
            return

        # Claude first: SupportPilot's default provider.
        provider_keys = {
            "anthropic": anthropic_key,
            "openai": openai_key,
            "groq": groq_key,
        }
        if self.provider in provider_keys:
            key = provider_keys[self.provider]
            if not key:
                raise RuntimeError(f"{self.provider} was explicitly selected, but its API key is unavailable.")
            if not self._setup_cloud_client(self.provider, key, required=True):
                raise RuntimeError(f"{self.provider} was explicitly selected, but its SDK is unavailable.")
            return

        # In auto mode, only import a provider SDK when its credentials are set.
        # This keeps the offline API startup independent of optional cloud SDKs.
        for provider, key in provider_keys.items():
            if key and self._setup_cloud_client(provider, key, required=False):
                return

        self._setup_offline_client()

    def _setup_cloud_client(self, provider: str, api_key: str, required: bool) -> bool:
        if provider == "anthropic":
            try:
                import anthropic
            except ImportError as exc:
                if required:
                    raise RuntimeError("anthropic was selected, but the `anthropic` SDK is not installed.") from exc
                return False
            self.model_name = self.model_name or os.getenv("ANTHROPIC_MODEL_NAME", "claude-sonnet-4-5")
            self.client = anthropic.Anthropic(api_key=api_key)
            self.provider = "anthropic"
            return True
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            if provider == "openai":
                from langchain_openai import ChatOpenAI

                self.model_name = self.model_name or os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
                self.client = ChatOpenAI(
                    model=self.model_name,
                    temperature=self.temperature,
                    api_key=api_key,
                )
            else:
                from langchain_groq import ChatGroq

                self.model_name = self.model_name or os.getenv(
                    "GROQ_MODEL_NAME", "llama-3.1-8b-instant"
                )
                self.client = ChatGroq(
                    model_name=self.model_name,
                    temperature=self.temperature,
                    groq_api_key=api_key,
                )
        except ImportError as exc:
            if required:
                raise RuntimeError(f"{provider} was selected, but its LangChain SDK is unavailable.") from exc
            return False

        self.provider = provider
        self._system_message_class = SystemMessage
        self._human_message_class = HumanMessage
        return True

    def _setup_offline_client(self) -> None:
        # Deterministic, grounded offline engine.
        self.provider = "offline"
        self.model_name = self.model_name or "supportpilot-grounded-v1"
        self.client = OfflineGroundedLLM(model_name=self.model_name)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Execute generation using the configured LangChain client or offline LLM."""
        if self.provider in {"offline", "offline-fallback"}:
            return self.client.invoke(system_prompt, user_prompt)

        if self.provider == "anthropic":
            try:
                msg = self.client.messages.create(
                    model=self.model_name, max_tokens=1500, temperature=self.temperature,
                    system=system_prompt, messages=[{"role": "user", "content": user_prompt}],
                )
                return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
            except Exception as exc:
                self.last_error = f"{type(exc).__name__}: {exc}"
                if os.getenv("LLM_ALLOW_OFFLINE_FALLBACK", "false").casefold() != "true":
                    raise RuntimeError("Configured LLM provider failed; offline fallback is disabled.") from exc
                self.fallback_used = True
                self.provider = "offline-fallback"
                self.model_name = "offline-fallback"
                self.client = OfflineGroundedLLM(model_name=self.model_name)
                return self.client.invoke(system_prompt, user_prompt)

        try:
            messages = [
                self._system_message_class(content=system_prompt),
                self._human_message_class(content=user_prompt),
            ]
            response = self.client.invoke(messages)
            return response.content if hasattr(response, "content") else str(response)
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            if os.getenv("LLM_ALLOW_OFFLINE_FALLBACK", "false").casefold() != "true":
                raise RuntimeError("Configured LLM provider failed; offline fallback is disabled.") from exc
            self.fallback_used = True
            self.provider = "offline-fallback"
            self.model_name = "offline-fallback"
            self.client = OfflineGroundedLLM(model_name=self.model_name)
            return self.client.invoke(system_prompt, user_prompt)


def get_llm_service(provider: Optional[str] = None, model_name: Optional[str] = None) -> LLMService:
    """Factory function for LLM service."""
    return LLMService(provider=provider, model_name=model_name)
