import os
import joblib
from typing import Dict, Any, Optional
try:
    from .severity_engine import SeverityScoringEngine, SeverityLevel
except ImportError:  # run as a plain script
    from severity_engine import SeverityScoringEngine, SeverityLevel

DEFAULT_MODEL_PATH = "priority_model.joblib"


class PrioritySeverityService:

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH):
        self.model_path = model_path
        self.severity_engine = SeverityScoringEngine()
        self.model_artifact = None
        self.model = None
        self.classes = []
        self._load_model()

    def _load_model(self):
        """Loads trained priority model artifact if present."""
        if os.path.exists(self.model_path):
            try:
                self.model_artifact = joblib.load(self.model_path)
                if (
                    isinstance(self.model_artifact, dict)
                    and "model" in self.model_artifact
                ):
                    self.model = self.model_artifact["model"]
                    self.classes = self.model_artifact.get("classes", [])
                else:
                    self.model = self.model_artifact
                    if hasattr(self.model, "classes_"):
                        self.classes = self.model.classes_.tolist()
            except Exception as e:
                print(
                    f"[Warning] Could not load priority model from {self.model_path}: {e}"
                )
                self.model = None
        else:
            print(
                f"[Warning] Priority model artifact {self.model_path} not found. Priority prediction will use fallback."
            )

    def predict_priority(self, ticket_text: str) -> Dict[str, Any]:
        """
        Predicts ticket priority (Critical, High, Medium, Low) using the trained ML model.
        Returns predicted label, confidence score, and probability distribution.
        """
        if not ticket_text or not str(ticket_text).strip():
            return {
                "priority": SeverityLevel.LOW.value,
                "confidence": 0.50,
                "probabilities": {},
                "source": "fallback_empty_input",
            }

        if self.model is not None:
            try:
                pred = self.model.predict([ticket_text])[0]
                proba_dict = {}
                confidence = 0.85

                if hasattr(self.model, "predict_proba"):
                    probs = self.model.predict_proba([ticket_text])[0]
                    classes = (
                        self.classes
                        if len(self.classes) == len(probs)
                        else getattr(self.model, "classes_", [])
                    )
                    proba_dict = {
                        str(cls_name): round(float(p), 4)
                        for cls_name, p in zip(classes, probs)
                    }
                    confidence = round(float(max(probs)), 4)

                return {
                    "priority": str(pred),
                    "confidence": confidence,
                    "probabilities": proba_dict,
                    "source": "ml_model",
                }
            except Exception as e:
                print(f"[Error] Error during ML priority inference: {e}")

        # Heuristic fallback if model not loaded
        lower_text = ticket_text.lower()
        if any(
            w in lower_text
            for w in ["outage", "ransomware", "emergency", "fatal", "500 error", "down"]
        ):
            prio = SeverityLevel.CRITICAL.value
        elif any(
            w in lower_text for w in ["blocked", "cfo", "payroll", "slow", "failing"]
        ):
            prio = SeverityLevel.HIGH.value
        elif any(
            w in lower_text for w in ["issue", "error", "flicker", "jam", "audio"]
        ):
            prio = SeverityLevel.MEDIUM.value
        else:
            prio = SeverityLevel.LOW.value

        return {
            "priority": prio,
            "confidence": 0.70,
            "probabilities": {},
            "source": "heuristic_fallback",
        }

    def calculate_severity(
        self,
        ticket_text: str = "",
        business_impact: Optional[str] = None,
        affected_users: Optional[int] = None,
        service_criticality: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculates ITIL severity score and level based on business rules.
        If parameters are omitted, infers them directly from ticket_text.
        """
        return self.severity_engine.calculate_severity(
            ticket_text=ticket_text,
            business_impact=business_impact,
            affected_users=affected_users,
            service_criticality=service_criticality,
        )

    def evaluate_ticket(
        self,
        ticket_text: str,
        business_impact: Optional[str] = None,
        affected_users: Optional[int] = None,
        service_criticality: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes both priority prediction and severity scoring.
        Synthesizes composite incident urgency and returns structured data for API.
        Can be called with only ticket_text!
        """
        prio_result = self.predict_priority(ticket_text)
        sev_result = self.calculate_severity(
            ticket_text=ticket_text,
            business_impact=business_impact,
            affected_users=affected_users,
            service_criticality=service_criticality,
        )

        # Composite matrix: Standard ITIL Priority-Severity alignment
        recommended_priority = str(prio_result["priority"]).capitalize()
        sev_level = str(sev_result["severity"]).capitalize()

        if sev_level == "Critical":
            final_priority = SeverityLevel.CRITICAL.value
            composite_reasoning = (
                f"Priority elevated to Critical due to Severity {sev_level} override."
            )
        elif sev_level == "High" and recommended_priority in ["Low", "Medium"]:
            final_priority = SeverityLevel.HIGH.value
            composite_reasoning = (
                f"Priority elevated to High due to Severity {sev_level} floor."
            )
        elif sev_level == "Medium" and recommended_priority == "Low":
            final_priority = SeverityLevel.MEDIUM.value
            composite_reasoning = (
                f"Priority elevated to Medium due to Severity {sev_level} floor."
            )
        elif (
            sev_level in ["Medium", "Low"]
            and recommended_priority == "High"
            and sev_result["parameters"]["service_criticality"] in ["tier_3", "tier_4"]
        ):
            final_priority = SeverityLevel.MEDIUM.value
            composite_reasoning = f"Priority capped at Medium because service criticality is {sev_result['parameters']['service_criticality']}."
        else:
            final_priority = recommended_priority
            composite_reasoning = "Priority determined by ML classification."

        return {
            "ticket_text_snippet": ticket_text[:120]
            + ("..." if len(ticket_text) > 120 else ""),
            "priority": {
                "predicted_priority": final_priority,
                "raw_model_prediction": prio_result["priority"],
                "confidence": prio_result["confidence"],
                "class_probabilities": prio_result["probabilities"],
                "model_source": prio_result["source"],
            },
            "severity": {
                "level": sev_result["severity"],
                "score": sev_result["severity_score"],
                "confidence": sev_result["confidence"],
                "reasoning": sev_result["reasoning"],
                "inputs": sev_result["parameters"],
            },
            "sla": sev_result["sla"],
            "alignment_notes": composite_reasoning,
        }
