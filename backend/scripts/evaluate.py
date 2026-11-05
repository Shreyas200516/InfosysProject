"""Evaluation report: retrieval relevance, answer quality (grounding/citations), and latency.
    python -m scripts.evaluate        -> prints a report and writes docs/evaluation_results.json
"""
import json, statistics, time, warnings
from pathlib import Path

warnings.simplefilter("ignore")
from app import pipeline
from app.config import BACKEND_DIR
from app.db.repo import SQLiteRepository
from app.services.knowledge import get_knowledge

# (query, expected article title). Phrased like real tickets, not copied from the articles.
POSITIVE = [
    ("VPN keeps disconnecting every ten minutes when I work from home", "VPN Connection Failure"),
    ("Outlook has not received any new emails since Monday", "Outlook Email Not Syncing"),
    ("the printer on our floor shows offline and nothing prints", "Printer Showing Offline"),
    ("my account is locked after too many wrong password attempts", "Account Locked Out"),
    ("I clicked on a link in a fake invoice email", "Reporting a Phishing Email"),
    ("Microsoft Teams freezes and crashes during calls", "Microsoft Teams Crashing or Freezing"),
    ("my laptop does not turn on even when plugged in", "Laptop Will Not Power On"),
    ("the monitor shows no signal from the docking station", "Monitor Shows No Signal"),
    ("I do not get the MFA code on my phone", "Multi-Factor Authentication Code Not Arriving"),
    ("please give me access to the finance shared folder", "Requesting Access to a Shared Folder"),
    ("Windows update has been stuck at 30 percent since yesterday", "Windows Update Stuck or Failing"),
    ("the finance shared mailbox disappeared from my Outlook", "Shared Mailbox Missing in Outlook"),
    ("my mailbox is full and I cannot receive messages", "Mailbox Full"),
    ("need Adobe Acrobat installed on my laptop", "Software Installation Request"),
    ("I think my computer has ransomware, files are encrypted", "Suspected Malware or Ransomware"),
    ("VPN is extremely slow when I am remote", "VPN Slow Performance"),
]
NEGATIVE = ["our staging kubernetes pod OOMKilled repeatedly", "how do I book a meeting room for tomorrow",
            "SAP invoice posting error in finance module", "need a new office chair", "the coffee machine is broken"]


def main():
    kb = get_knowledge()
    top1 = top3 = 0
    misses = []
    for q, title in POSITIVE:
        got = [d.title for d in kb.search(q, top_k=3)]
        top1 += bool(got and got[0] == title); top3 += title in got
        if not got or got[0] != title:
            misses.append({"query": q, "expected": title, "got": got})
    false_accepts = [q for q in NEGATIVE if kb.search(q, top_k=3)]

    repo = SQLiteRepository(":memory:")
    times, grounded, cited, escal = [], 0, 0, 0
    for q, _ in POSITIVE:
        t0 = time.perf_counter()
        d = pipeline.process_ticket(repo, subject=q[:60], description=q, requester_name="Eval User", requester_email="eval@acme.com")
        times.append((time.perf_counter() - t0) * 1000)
        r = d["response"]
        grounded += bool(r["grounded"]); cited += bool(r["steps"] and r["sources"]); escal += d["ticket"]["status"] == "Escalated"
    n = len(POSITIVE)
    res = {
        "retrieval_mode": kb.mode, "positive_queries": n, "negative_queries": len(NEGATIVE),
        "hit_at_1": round(top1 / n, 3), "hit_at_3": round(top3 / n, 3), "false_accept_rate": round(len(false_accepts) / len(NEGATIVE), 3),
        "grounded_rate": round(grounded / n, 3), "steps_with_sources_rate": round(cited / n, 3), "escalation_rate": round(escal / n, 3),
        "pipeline_ms": {"p50": round(statistics.median(times), 1), "p95": round(sorted(times)[int(0.95 * (n - 1))], 1), "max": round(max(times), 1)},
        "retrieval_misses": misses, "false_accepts": false_accepts,
        "note": "Latency is for the offline engine (no network). Cloud-LLM latency adds the API round trip.",
    }
    out = BACKEND_DIR.parent / "docs" / "evaluation_results.json"
    out.parent.mkdir(exist_ok=True); out.write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
