"""Ticket category classifier: TF-IDF + Logistic Regression, with a safety net for security terms."""
from __future__ import annotations

import re
import warnings
from functools import lru_cache
from typing import Any

import joblib

from ..config import settings

CATEGORIES = ["Network", "VPN", "Email", "Software", "Hardware", "Access", "Security"]
# Security incidents must never be missed because a statistical model was unsure.
SECURITY_RX = re.compile(r"\b(phishing|ransomware|malware|virus|breach|data leak|stolen|suspicious|compromised|hacked|encrypted files|unauthori[sz]ed)\b", re.I)


class CategoryClassifier:
    def __init__(self, model_path: str | None = None):
        self.model_path = model_path or settings.category_model_path
        self.model = None
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.model = joblib.load(self.model_path)
        except Exception as exc:  # model missing -> keyword fallback keeps the API alive
            print(f"[classifier] could not load {self.model_path}: {exc}. Run `python -m ml.train_category`.")

    @property
    def ready(self) -> bool:
        return self.model is not None

    def predict(self, text: str) -> dict[str, Any]:
        text = (text or "").strip()
        if self.model is None:
            return self._keyword_fallback(text)
        probs = self.model.predict_proba([text])[0]
        classes = list(self.model.classes_)
        ranked = sorted(zip(classes, probs), key=lambda x: -x[1])
        label, conf = ranked[0]
        source = "ml_model"
        if SECURITY_RX.search(text) and label != "Security":
            label, conf, source = "Security", max(conf, 0.75), "security_rule_override"
        if conf < settings.category_min_confidence and source == "ml_model":
            label = "General IT"
        return {
            "category": label, "confidence": round(float(conf), 4), "source": source,
            "probabilities": {c: round(float(p), 4) for c, p in ranked[:4]},
        }

    @staticmethod
    def _keyword_fallback(text: str) -> dict[str, Any]:
        t = text.lower()
        rules = [("Security", SECURITY_RX.pattern), ("VPN", r"\bvpn\b"), ("Email", r"outlook|email|mailbox"),
                 ("Network", r"wi-?fi|network|internet|dns"), ("Access", r"password|login|locked|access|mfa"),
                 ("Hardware", r"printer|laptop|monitor|keyboard|mouse|screen"), ("Software", r"install|crash|update|application|excel|teams")]
        for cat, rx in rules:
            if re.search(rx, t, re.I):
                return {"category": cat, "confidence": 0.6, "source": "keyword_fallback", "probabilities": {cat: 0.6}}
        return {"category": "General IT", "confidence": 0.3, "source": "keyword_fallback", "probabilities": {}}


@lru_cache(maxsize=1)
def get_classifier() -> CategoryClassifier:
    return CategoryClassifier()
