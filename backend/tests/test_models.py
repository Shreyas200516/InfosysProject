import pytest

from app.services.classifier import get_classifier
from app.services.knowledge import get_knowledge
from app.services.triage import get_triage


@pytest.mark.parametrize("text,expected", [
    ("VPN keeps disconnecting from home", "VPN"), ("Outlook is not syncing my emails", "Email"),
    ("printer shows offline", "Hardware"), ("I forgot my password and need a reset", "Access"),
    ("I received a phishing email", "Security"), ("Microsoft Teams keeps crashing", "Software"),
    ("office Wi-Fi keeps dropping", "Network")])
def test_category_samples(text, expected):
    assert get_classifier().predict(text)["category"] == expected


def test_security_rule_overrides_model():
    r = get_classifier().predict("my laptop shows a ransomware message")
    assert r["category"] == "Security"


@pytest.mark.parametrize("text,sev", [("VPN is down for the whole company, nobody can connect", "Critical"),
                                      ("Request new ergonomic mouse and wrist rest", "Low")])
def test_severity_rules(text, sev):
    assert get_triage().evaluate(text)["severity"] == sev


def test_retrieval_finds_right_article_and_rejects_offtopic():
    kb = get_knowledge()
    assert kb.search("Outlook is not syncing new emails since Monday")[0].title == "Outlook Email Not Syncing"
    assert kb.search("Microsoft Teams keeps crashing during meetings")[0].title.startswith("Microsoft Teams")
    assert kb.search("our staging kubernetes pod OOMKilled repeatedly") == []
    assert kb.search("how do I book a meeting room") == []
