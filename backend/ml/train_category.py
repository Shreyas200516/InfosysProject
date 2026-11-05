"""
Category classifier (TF-IDF + Logistic Regression).

Why this exists: the team's `train_category_model.py` trained on the dataset's `type`
column (Incident / Request / Problem / Change) and never saved a model. The PDF asks for
IT categories (network, VPN, software, hardware, access, email, security), which the
dataset does not label. So:

  * Training data = hand-written IT ticket phrasings (short, employee-style) wrapped in
    varied openers/closers, PLUS English tickets from the team's cleaned dataset that
    match strong keywords for exactly one category (weak labels).
  * Evaluation is on HELD-OUT PHRASINGS (templates never seen in training), so the score
    is not just memorised wording. It is still not a benchmark on real labelled tickets:
    replace the data with real labelled IT tickets when available and re-run.

Run:  python -m ml.train_category
"""
from __future__ import annotations

import json
import random
import re
import warnings
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score, precision_score, recall_score
from sklearn.pipeline import Pipeline

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
MODEL_PATH = HERE / "models" / "category_classifier.joblib"
REPORT_PATH = HERE / "models" / "category_report.json"
DATASET = HERE / "data" / "cleaned_dataset.csv"

PHRASES: dict[str, list[str]] = {
    "Network": [
        "the office Wi-Fi keeps dropping every few minutes", "no internet connection on my desktop",
        "cannot connect to the corporate wireless network", "ethernet port is dead and I get no network",
        "DNS resolution fails for internal websites", "network is extremely slow in the whole building",
        "my laptop gets an IP address conflict error", "cannot reach the shared network drive",
        "the router on our floor is not responding", "packet loss and high latency on video calls",
        "wifi shows connected but no internet access", "unable to access any website from the office LAN",
        "network switch on the 3rd floor is down", "limited connectivity warning on the network adapter",
        "gateway timeout when opening internal portals", "Wi-Fi password is rejected on the guest network",
    ],
    "VPN": [
        "VPN keeps disconnecting every ten minutes", "cannot connect to the company VPN from home",
        "VPN client shows authentication failed", "GlobalProtect stuck on connecting",
        "VPN connects but I cannot reach internal servers", "Cisco AnyConnect error 'secure gateway not responding'",
        "VPN tunnel drops when I switch networks", "remote access VPN certificate has expired",
        "VPN is very slow when working remotely", "unable to install the VPN client on my new laptop",
        "VPN says the connection attempt timed out", "split tunnel VPN not routing traffic to the intranet",
        "my VPN login works on mobile but not on laptop", "VPN profile missing after the update",
        "FortiClient VPN fails at 98 percent", "VPN concentrator seems unreachable for our team",
    ],
    "Email": [
        "Outlook is not syncing new emails", "I cannot send emails and they stay in the outbox",
        "my mailbox is full and I cannot receive messages", "Outlook keeps asking for my password again and again",
        "shared mailbox is missing from my Outlook", "emails sent to me are bouncing back",
        "calendar invites are not showing up in Outlook", "spam filter is blocking legitimate customer emails",
        "attachments will not open in Outlook", "email signature disappeared after the update",
        "cannot add my email account on my phone", "distribution list is not delivering emails",
        "Outlook search returns no results", "out of office reply is not being sent",
        "Exchange mailbox is not loading in the webmail", "mail delivery delayed by several hours",
    ],
    "Software": [
        "Microsoft Excel crashes when I open large files", "application freezes on start and has to be force closed",
        "need Adobe Acrobat installed on my laptop", "software update failed with error code 0x80070005",
        "Teams keeps crashing during meetings", "cannot install the new CRM client",
        "Word shows a licence not found message", "the application throws a runtime error on launch",
        "Chrome is very slow and keeps showing aw snap", "my IDE will not start after the last update",
        "request to install Visual Studio Code", "Zoom cannot share my screen",
        "the accounting software shows a database error", "Windows update is stuck at 30 percent",
        "PowerPoint file is corrupted and will not open", "program crashes with a blue error dialog",
    ],
    "Hardware": [
        "my laptop screen is flickering", "the keyboard stopped working on my laptop",
        "printer shows offline and will not print", "laptop battery drains within an hour",
        "monitor has no signal from the docking station", "mouse is not being detected",
        "headset microphone not working", "my laptop will not power on at all",
        "USB ports have stopped working", "the printer jams on every page",
        "webcam is not detected in video calls", "laptop fan is extremely loud and the device is hot",
        "external hard drive is not recognised", "need a replacement charger for my laptop",
        "docking station does not charge the laptop", "touchpad is unresponsive",
    ],
    "Access": [
        "I forgot my password and need a reset", "my account is locked after too many attempts",
        "cannot log in to my Windows account", "need access to the finance shared folder",
        "request permissions for the SharePoint site", "multi-factor authentication code is not arriving",
        "password reset link has expired", "I lost my authenticator device and cannot sign in",
        "new employee needs an account and system access", "single sign-on fails with an access denied page",
        "need admin rights to install approved software", "my access to the HR portal was removed by mistake",
        "unable to log in to the VPN portal because account is disabled", "please unlock my Active Directory account",
        "need to be added to the engineering group", "login keeps looping back to the sign-in page",
    ],
    "Security": [
        "I received a suspicious phishing email", "my laptop shows a ransomware message",
        "antivirus detected malware on my computer", "I clicked a link in a fake invoice email",
        "possible data breach, customer files were exposed", "unknown login attempts from another country on my account",
        "lost company laptop, need it remotely wiped", "my USB drive was flagged as infected",
        "suspicious pop-ups and browser redirects started today", "someone is impersonating our CEO by email",
        "security alert for unusual activity on my account", "files on the server are encrypted and unreadable",
        "device was stolen and contains confidential data", "report a vulnerability in the customer portal",
        "firewall blocked a legitimate application and flagged a threat", "password was found in a data leak",
    ],
}
OPENERS = ["", "", "Hi team, ", "Hello, ", "Urgent: ", "Hi IT, ", "Good morning, ", "Please help: ", "Issue: ", "Since this morning "]
CLOSERS = ["", "", " Please help.", " Thanks in advance.", " This is blocking my work.", " Started yesterday.", " Can someone look into this?", " It happens on my laptop."]


# Broader vocabulary for training only (subject x symptom). The held-out PHRASES above are never used for training.
SUBJECTS: dict[str, list[str]] = {
    "Network": ["Wi-Fi", "the internet connection", "the office network", "LAN cable", "the wireless access point", "DNS", "the router", "network drive access", "bandwidth", "the guest wifi", "proxy settings", "the switch in our room"],
    "VPN": ["VPN", "the VPN client", "the remote access tunnel", "the VPN gateway", "GlobalProtect", "AnyConnect", "the VPN login", "my VPN session", "site-to-site VPN", "the VPN certificate"],
    "Email": ["Outlook", "my mailbox", "email", "the calendar in Outlook", "webmail", "my inbox", "the shared mailbox", "incoming mail", "outgoing mail", "email attachments", "my mail profile"],
    "Software": ["Excel", "the application", "Microsoft Teams", "Photoshop", "the CRM software", "my browser", "the installer", "Windows update", "Word", "the desktop app", "the licence for the program", "the ERP client"],
    "Hardware": ["my laptop", "the printer", "my monitor", "the keyboard", "the mouse", "the docking station", "my headset", "the scanner", "my laptop battery", "the webcam", "the projector", "my external drive"],
    "Access": ["my password", "my account", "my login", "the shared folder permissions", "multi-factor authentication", "my user ID", "single sign-on", "my access rights", "the authenticator app", "my Active Directory account", "the HR portal login"],
    "Security": ["a phishing email", "malware", "a suspicious attachment", "my antivirus", "a ransomware note", "a data leak", "a stolen laptop", "an unknown login alert", "a virus warning", "a fake invoice link", "a security incident", "unauthorised access to files"],
}
SYMPTOMS = ["is not working", "keeps failing", "stopped working today", "shows an error", "is very slow", "will not open", "needs urgent attention", "is broken since the update", "gives me a warning", "has a problem", "needs to be fixed", "is behaving strangely"]
SECURITY_SYMPTOMS = ["was reported by me", "needs to be investigated", "just appeared on my computer", "is worrying me", "was received this morning", "happened today"]


def bank(cat: str, n: int, rng: random.Random) -> list[str]:
    out = []
    for _ in range(n):
        subj = rng.choice(SUBJECTS[cat])
        sym = rng.choice(SECURITY_SYMPTOMS if cat == "Security" else SYMPTOMS)
        text = f"{rng.choice(OPENERS)}{subj} {sym}.{rng.choice(CLOSERS)}"
        out.append(re.sub(r"\s+", " ", text).strip())
    return out

WEAK_KEYWORDS = {
    "VPN": r"\bvpn\b", "Email": r"\b(outlook|mailbox|e-?mail sync|exchange server)\b",
    "Network": r"\b(wi-?fi|router|ethernet|dns|network switch|wireless network|lan)\b",
    "Security": r"\b(phishing|ransomware|malware|breach|virus)\b",
    "Access": r"\b(password reset|forgot (my )?password|account locked|locked out|mfa|two-factor)\b",
    "Hardware": r"\b(printer|monitor|keyboard|laptop screen|docking station|webcam|battery)\b",
    "Software": r"\b(software crash|application crash|install(ation)? (of|the) software|update failed|crashes when)\b",
}


def synth(phrases: list[str], n: int, rng: random.Random) -> list[str]:
    out = []
    for _ in range(n):
        p = rng.choice(phrases)
        text = f"{rng.choice(OPENERS)}{p}.{rng.choice(CLOSERS)}"
        out.append(re.sub(r"\s+", " ", text).strip())
    return out


def weak_labelled_real(limit_per_class: int = 40) -> pd.DataFrame:
    if not DATASET.exists():
        return pd.DataFrame(columns=["text", "category"])
    df = pd.read_csv(DATASET)
    df = df[df["language"] == "en"].copy()
    df["text"] = df["ticket_text"].astype(str).str.slice(0, 600)
    rows = []
    for _, r in df.iterrows():
        hits = [c for c, rx in WEAK_KEYWORDS.items() if re.search(rx, r["text"].lower())]
        if len(hits) == 1:
            rows.append((r["text"], hits[0]))
    out = pd.DataFrame(rows, columns=["text", "category"])
    return out.groupby("category", group_keys=False).head(limit_per_class)


def main() -> dict:
    rng = random.Random(42)
    train_rows, test_rows = [], []
    for cat, phrases in PHRASES.items():
        shuffled = phrases[:]
        rng.shuffle(shuffled)
        tr, te = shuffled[:12], shuffled[12:]  # 12 phrasings train, 4 unseen phrasings test
        train_rows += [(t, cat) for t in synth(tr, 260, rng)]
        train_rows += [(t, cat) for t in bank(cat, 300, rng)]
        test_rows += [(t, cat) for t in synth(te, 60, rng)]

    real = weak_labelled_real()
    if len(real):
        real = real.sample(frac=1, random_state=42)
        cut = int(len(real) * 0.8)
        train_rows += list(real.iloc[:cut].itertuples(index=False, name=None))
        test_rows += list(real.iloc[cut:].itertuples(index=False, name=None))

    train = pd.DataFrame(train_rows, columns=["text", "category"])
    test = pd.DataFrame(test_rows, columns=["text", "category"])

    model = Pipeline([
        ("tfidf", TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=(1, 2), sublinear_tf=True, min_df=1)),
        ("clf", LogisticRegression(max_iter=2000, C=8.0, class_weight="balanced")),
    ])
    model.fit(train["text"], train["category"])
    pred = model.predict(test["text"])

    metrics = {
        "accuracy": round(accuracy_score(test["category"], pred), 4),
        "precision_weighted": round(precision_score(test["category"], pred, average="weighted", zero_division=0), 4),
        "recall_weighted": round(recall_score(test["category"], pred, average="weighted", zero_division=0), 4),
        "f1_weighted": round(f1_score(test["category"], pred, average="weighted", zero_division=0), 4),
        "train_rows": len(train), "test_rows": len(test), "weak_labelled_real_rows": int(len(real)),
        "caveat": "Test set = unseen hand-written phrasings + weakly-labelled real tickets. Not a benchmark on human-labelled production tickets.",
        "report": classification_report(test["category"], pred, zero_division=0, output_dict=True),
    }
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    REPORT_PATH.write_text(json.dumps(metrics, indent=2))
    print(classification_report(test["category"], pred, zero_division=0))
    print({k: v for k, v in metrics.items() if k != "report"})
    return metrics


if __name__ == "__main__":
    main()
