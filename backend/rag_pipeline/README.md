# SupportPilot — RAG Pipeline

**Role**:  RAG Pipeline  
**Module**: Retrieval & Large Language Model (LLM) Integration  
**Tech Stack**: Python 3.14 / 3.13, LangChain, ChromaDB, LLM API (OpenAI / Groq / Fallback Offline Grounded Engine)  
**Deliverable**: Integrated RAG Pipeline (`rag_pipeline`)

---

## 1. Overview & Objective

The **SupportPilot RAG Pipeline** connects incoming IT support tickets with enterprise troubleshooting documentation to deliver accurate, context-aware, step-by-step resolution workflows.

Under the milestone work division:
- prepared the knowledge base documents and SOP chunks.
- built the semantic search engine and ChromaDB vector database.
- delivers the **Integrated RAG Pipeline**:
  1. **Connects ticket intake with the retrieval engine**.
  2. **Passes retrieved documents to the LLM as structured context**.
  3. **Generates context-aware troubleshooting answers**.
  4. **Enforces strict prompts and guardrails to eliminate unsupported answers (hallucinations)**.
  5. **Formats output with step-by-step instructions, inline source citations, and escalation recommendations**.
- consumes this pipeline for resolution generation testing, quality benchmarks, and pytest evaluations.

---

## 2. Architecture & Workflow

```
                                      +------------------------------------+
                                      |     Support Ticket Intake          |
                                      | (Subject, Description, Category)   |
                                      +-----------------+------------------+
                                                        |
                                                        v
                                      +------------------------------------+
                                      |      Semantic Query Extraction     |
                                      +-----------------+------------------+
                                                        |
                                                        v
+-----------------------------+       +------------------------------------+
|      Deliverable            | ----> |     ChromaDB Vector Retrieval      |
|  ChromaDB Knowledge Base    |       |  (Top-k Cosine Semantic Search)    |
+-----------------------------+       +-----------------+------------------+
                                                        | Retrieved Chunks (Docs, Scores)
                                                        v
                                      +------------------------------------+
                                      |     Context Augmentation Layer     |
                                      |  - Document formatting             |
                                      |  - Relevance threshold filtering   |
                                      +-----------------+------------------+
                                                        |
                                                        v
                                      +------------------------------------+
                                      |   Strict Anti-Hallucination Prompt |
                                      |  - Explicit grounding constraint   |
                                      |  - Mandatory [Source: ...] citation|
                                      |  - UNSUPPORTED refusal directive   |
                                      +-----------------+------------------+
                                                        |
                                                        v
+-----------------------------+       +------------------------------------+
|   LangChain LLM Engine      | <---> |   LLM Generation (Temp = 0.0)      |
| (OpenAI / Groq / Grounded)  |       +-----------------+------------------+
+-----------------------------+                         |
                                                        v
                                      +------------------------------------+
                                      |  Grounding & Safety Guardrail      |
                                      |  - Verifies source citations       |
                                      |  - Calculates confidence score     |
                                      |  - Triggers escalation if ungrounded|
                                      +-----------------+------------------+
                                                        |
                                                        v
                                      +------------------------------------+
                                      |     Structured RAGResponse         |
                                      | (Resolution, Steps, Citations,     |
                                      |  Confidence, Escalation Status)    |
                                      +------------------------------------+
```

---

## 3. Directory Structure

```
rag_pipeline/
├── __init__.py                 # Package exports & public API
├── schemas.py                  # Pydantic models (TicketInput, RetrievedDocument, RAGResponse)
├── prompts.py                  # LangChain prompt templates & anti-hallucination policies
├── retriever.py                # ChromaDB semantic search interface
├── llm_service.py              # LangChain LLM orchestrator (OpenAI, Groq, Offline Grounded)
├── grounding_guardrails.py     # Hallucination detector & confidence scoring engine
├── rag_pipeline.py             # Primary SupportPilotRAGPipeline orchestration class
├── interactive_cli.py          # Interactive demonstration and benchmark CLI
├── test_rag_pipeline.py        # Pytest test suite covering all functional requirements
└── README.md                   # Complete module documentation
```

---

## 4. Key Design Decisions: Reducing Unsupported Answers

A primary requirement  is to **"Add prompts to reduce unsupported answers"**. In enterprise IT, hallucinated instructions (e.g. invalid server IPs, destructive commands) can cause network outages or security vulnerabilities.

SupportPilot employs a 4-layer anti-hallucination architecture:

### Layer 1: Zero-Temperature LLM Execution
The LLM service runs with `temperature = 0.0` to encourage consistent output.

### Layer 2: Strict System Prompt Directives
The system prompt (`STRICT_RAG_SYSTEM_PROMPT`) imposes hard boundaries:
- **Grounding Requirement**: The model is restricted to facts explicitly stated in the retrieved context chunks.
- **Refusal Requirement**: If the context does not contain sufficient instructions, the model is strictly forbidden from improvising and MUST output:
  `UNSUPPORTED_BY_DOCUMENTATION: The available enterprise knowledge base does not contain verified troubleshooting procedures for this request.`
- **Mandatory Inline Citations**: Every individual step must cite its origin using `[Source: <Title>]`.

### Layer 3: Semantic Relevance Thresholding
Before passing chunks to the LLM, the retriever filters out documents below the cosine-similarity threshold (`similarity_threshold = 0.35`). If no documents meet the threshold, the pipeline returns a refusal and escalation without calling the LLM.

### Layer 4: Post-Generation Grounding Guardrails
`GroundingGuardrail` analyzes the generated text:
- Checks for the `UNSUPPORTED_BY_DOCUMENTATION` signal.
- Validates that every cited `[Source: ...]` exists in the retrieved documents.
- Calculates a composite `confidence_score` (0.0 to 1.0).
- Automatically sets `needs_escalation = True` and specifies the `escalation_reason` when confidence is low or documentation is absent.

---

## 5. Integration Contracts

### Semantic Search Engine
connects to retriever via `BaseKnowledgeRetriever`:
```python
from rag_pipeline.retriever import BaseKnowledgeRetriever
from rag_pipeline.schemas import RetrievedDocument

class Person2CustomRetriever(BaseKnowledgeRetriever):
    def search(self, query: str, top_k: int = 3, category: str = None, similarity_threshold: float = 0.35) -> List[RetrievedDocument]:
        ...
```
`ChromaKnowledgeRetriever` opens existing `semantic_search/chroma_db` database and `supportpilot_knowledge_base` collection. It encodes ticket queries with the same `all-MiniLM-L6-v2` model used to build that collection. Set `SUPPORTPILOT_CHROMA_PATH` or `SUPPORTPILOT_CHROMA_COLLECTION` to override those defaults. If the vector index is missing or cannot be queried, retrieval falls back to a lightweight lexical search over  `knowledge_base_chunks.csv`; it does not insert or answer from a separate hard-coded knowledge base. Lexical fallback scores use bounded query coverage plus title/tag matches and mark each result with `retrieval_method="lexical_fallback"`.

Install the pipeline dependencies with:
```powershell
python -m pip install -r rag_pipeline/requirements.txt
```

The OpenAI and Groq LangChain integrations are optional when using the offline grounded generator. Their SDKs load only when a configured cloud provider is selected, so offline API startup does not load cloud clients. Configure `LLM_PROVIDER`, `OPENAI_API_KEY`, or `GROQ_API_KEY` in the project environment to select a cloud model.

Cloud provider failures are surfaced as service errors by default. Set
`LLM_ALLOW_OFFLINE_FALLBACK=true` only when you explicitly want fallback; the
response then reports `provider="offline-fallback"` and `fallback_used=true`.
`fallback_used` is also true when retrieval uses the lexical CSV fallback.
Every numbered generated step must include a source and an exact supporting
quote (`[Evidence: ...]`). The guardrail requires an exact source reference and
checks the evidence against that cited document, along with a basic ticket-term
check. This is a conservative filter, not a formal proof of semantic entailment.

The demonstration API exposes `POST /api/tickets/{ticket_id}/resolution` to
authorized support staff and `GET` on the same path to read the saved result.
Resolution generation runs synchronously in the API worker and returns 503 on
provider/retrieval failures; a queue should replace this route for higher-volume
deployment.

### Contract with Resolution Generation & Evaluation
imports `SupportPilotRAGPipeline` directly to run evaluation benchmarks, test edge cases, and measure answer quality and latency:
```python
from rag_pipeline import SupportPilotRAGPipeline, TicketInput

pipeline = SupportPilotRAGPipeline()
response = pipeline.resolve_ticket(
    TicketInput(
        ticket_id="T-2026-4521",
        subject="VPN Connection Failing on Corporate Network",
        description="Connection timed out trying to reach gateway",
        category="VPN"
    )
)

print(response.resolution)
print("Steps:", response.step_by_step_steps)
print("Sources:", response.sources_cited)
print("Confidence:", response.grounding.confidence_score)
print("Needs Escalation:", response.grounding.needs_escalation)
```

---

## 6. How to Run & Verify

### Running the Pytest Suite
Run the 9 automated tests verifying ticket connection, context augmentation, context-aware answers, anti-hallucination refusal, and citations:
```powershell
python -m pytest rag_pipeline/test_rag_pipeline.py -v
```

### Running the Benchmark Demonstration
Execute all standard benchmark IT tickets and view the complete resolution reports:
```powershell
python -m rag_pipeline.interactive_cli --benchmark
```

### Running the Interactive CLI
Launch the interactive console to test custom tickets:
```powershell
python -m rag_pipeline.interactive_cli
```

---

## 7. Sample Output (Prepared Knowledge-Base Article)

```markdown
### Diagnosis Summary
The most relevant retrieved procedure is 'Wi-Fi Connection Issues'.

### Step-by-Step Resolution Workflow
1. Check that Wi-Fi is enabled. [Source: Wi-Fi Connection Issues]
2. Restart the network adapter and reconnect to the correct wireless network. [Source: Wi-Fi Connection Issues]

### Verification & Confirmation
The retrieved documentation does not specify a verification procedure.

### Escalation Trigger
The retrieved documentation does not specify an escalation trigger. Route the ticket to human IT support if the documented steps do not resolve the issue.
```
