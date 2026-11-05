"""Create demo tickets (spread over the last 14 days) so the dashboard has data.
    python -m scripts.seed_demo [count]
Uses whichever database is configured (Supabase if set, else SQLite)."""
import random
import sys
from datetime import datetime, timedelta, timezone

from app import pipeline
from app.db.repo import get_repo

SAMPLES = [
    ("VPN keeps disconnecting", "The VPN drops every ten minutes when I work from home."),
    ("Cannot connect to office Wi-Fi", "My laptop shows connected but there is no internet on the corporate wireless network."),
    ("Outlook not syncing", "Outlook has not received new emails since Monday morning."),
    ("Printer offline on 3rd floor", "The shared printer shows offline and nothing prints."),
    ("Account locked", "My account is locked after too many password attempts, I need it unlocked."),
    ("MFA code not arriving", "I do not receive the multi-factor authentication code on my phone."),
    ("Teams crashing in meetings", "Microsoft Teams freezes and crashes during video calls."),
    ("Need Adobe Acrobat installed", "Please install Adobe Acrobat on my laptop for contract review."),
    ("Phishing email received", "I clicked a link in a fake invoice email, what should I do?"),
    ("Laptop will not power on", "My laptop does not turn on even with the charger connected."),
    ("Monitor no signal", "The monitor on my desk shows no signal from the docking station."),
    ("VPN is down for the whole company", "Nobody in the company can connect to the VPN, around 800 users affected."),
    ("Kubernetes pod OOMKilled", "Our staging pod is OOMKilled repeatedly after the deployment."),
    ("Shared mailbox missing", "The finance shared mailbox disappeared from my Outlook."),
    ("Need access to finance folder", "Please give me access to the finance shared folder for quarter close."),
    ("Windows update stuck", "Windows update has been stuck at 30 percent since yesterday."),
]
NAMES = [("Asha Rao", "asha.rao@acme.com", "Finance"), ("Dev Patel", "dev.patel@acme.com", "Engineering"), ("Meera Nair", "meera.nair@acme.com", "HR"),
         ("Karan Shah", "karan.shah@acme.com", "Sales"), ("Isha Iyer", "isha.iyer@acme.com", "Operations")]


def main(n: int = 40) -> None:
    repo, rng = get_repo(), random.Random(7)
    pool = (SAMPLES * (n // len(SAMPLES) + 1))[:n]  # every sample appears, including the ones that escalate
    rng.shuffle(pool)
    for subj, desc in pool:
        name, email, dept = rng.choice(NAMES)
        d = pipeline.process_ticket(repo, subject=subj, description=desc, requester_name=name, requester_email=email, department=dept)
        when = (datetime.now(timezone.utc) - timedelta(days=rng.randint(0, 13), hours=rng.randint(0, 20))).isoformat()
        repo.update("tickets", d["ticket"]["ticket_id"], {"created_at": when, "updated_at": when})
    print(f"Seeded {n} tickets into {repo.backend}.")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 40)
