# SupportPilot – Milestone 1: Deliverable Report
## Priority Prediction Model & ITIL Severity Scoring Engine

---

### Executive Summary

| Deliverable | Description | Status & Benchmark |
| :--- | :--- | :--- |
| **ML Priority Model** | TF-IDF + Balanced Multi-class Logistic Regression (`priority_model.joblib`) | **90.91% Accuracy** (Exceeds >= 90% target) |
| **ITIL Severity Engine** | Deterministic composite scoring (Impact 40% + Users 30% + Tier 30% + Overrides) | **100% Validation Pass Rate** (Exceeds >= 85% target) |
| **Unified Service** | Single pipeline (`priority_severity_service.py`) with text inference & ITIL alignment | Production-ready for  FastAPI |
| **Test Suite** | Comprehensive 8-scenario suite (`test_priority_severity.py`) | **8/8 Tests Passed (100%)** |

---

### 1. ITIL Severity & SLA Matrix

> **Composite Severity Score (0 - 100)** = Business Impact (40%) + Affected Users (30%) + Service Criticality Tier (30%)

| Severity Level | Score Range | Criteria & Triggers | Target SLA (Resp / Reso) | Escalation Channel |
| :--- | :--- | :--- | :--- | :--- |
| **Critical (Sev-1)** | >= 80 | Outage, data breach, >= 200 users on Tier 1/2, or Tier 1 blocker | < 15 min / < 2 hr | PagerDuty On-Call + Incident Commander + VP |
| **High (Sev-2)** | 55 - 79 | Major impairment, VIP/Executive blocked, no workaround | < 60 min / < 6 hr | Senior Technical Specialist + Ops Lead |
| **Medium (Sev-3)** | 32 - 54 | Localized issue, single user/small group, workaround available | < 4 hr / < 24 hr | Tier-2 Support Queue |
| **Low (Sev-4)** | < 32 | Minor inquiry, cosmetic issue, routine hardware/software request | < 8 hr / < 72 hr | General Queue / Knowledge Base |

**Safety Overrides**: Immediate escalation to **Critical** if:
- Tier 1 system has critical impact.
- >= 200 users affected on Tier 1 or Tier 2 services.
- Critical security or outage triggers detected (`ransomware`, `500 error`, `data breach`, `total outage`).

---

### 2. Model Performance & Evaluation

- **Pipeline**: Scikit-Learn `TfidfVectorizer` (unigrams + bigrams, 5k features) -> `LogisticRegression(class_weight='balanced')`.
- **Metrics**: **Accuracy: 90.91%** | **Precision: 91.51%** | **Recall: 90.91%** | **F1-Score: 90.75%**

```
              precision    recall  f1-score   support
    Critical     0.8571    1.0000    0.9231        12
        High     1.0000    0.8333    0.9091        12
         Low     0.9091    1.0000    0.9524        10
      Medium     0.8889    0.8000    0.8421        10
    accuracy                         0.9091        44
```

---

### 3. Test Suite Summary (`test_priority_severity.py`)

| Test Scenario | Parameters (Impact / Users / Tier) | Predicted Priority | Severity (Score) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **1. Primary DB Outage** | Critical / 2500 / Tier 1 | **Critical** | **Critical (100)** | [PASSED] |
| **2. Active Ransomware** | Critical / 150 / Tier 1 | **Critical** | **Critical (95)** | [PASSED] |
| **3. Regional VPN Gateway** | High / 120 / Tier 2 | **High** | **High (77)** | [PASSED] |
| **4. CFO Laptop Crash** | High / 1 / Tier 2 | **High** | **High (57)** | [PASSED] |
| **5. USB-C Dock Display** | Medium / 1 / Tier 3 | **Medium** | **Medium (37)** | [PASSED] |
| **6. 4th Floor Printer Jam** | Medium / 8 / Tier 3 | **Medium** | **Medium (44)** | [PASSED] |
| **7. Password Reset** | Low / 1 / Tier 4 | **Low** | **Low (17)** | [PASSED] |
| **8. Ergonomic Mouse Req** | Low / 1 / Tier 4 | **Low** | **Low (17)** | [PASSED] |

---

### 4. Integration Snippet (FastAPI)

```python
from fastapi import FastAPI
from pydantic import BaseModel
from priority_severity_service import PrioritySeverityService

app = FastAPI(title="SupportPilot Ticket API")
service = PrioritySeverityService(model_path="priority_model.joblib")

class TicketPayload(BaseModel):
    ticket_text: str
    business_impact: str = "medium"       # "critical", "high", "medium", "low"
    affected_users: int = 1
    service_criticality: str = "tier_2"   # "tier_1", "tier_2", "tier_3", "tier_4"

@app.post("/api/v1/tickets/process")
def process_ticket(payload: TicketPayload):
    return {"status": "success", "analysis": service.evaluate_ticket(**payload.dict())}
```
