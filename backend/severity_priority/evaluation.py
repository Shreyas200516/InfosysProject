import pandas as pd
try:
    from .priority_severity_service import PrioritySeverityService
except ImportError:  # run as a plain script
    from priority_severity_service import PrioritySeverityService

# Path to your dataset
DATASET_PATH = r"cleaned_dataset.csv"

df = pd.read_csv(DATASET_PATH)
service = PrioritySeverityService()

for _, row in df.head(5).iterrows():
    result = service.evaluate_ticket(ticket_text=row["ticket_text"])
    print(f"Ticket: {row['ticket_text']}")
    print(
        f"Priority: {result['priority']['predicted_priority']} | Severity: {result['severity']['level']}\n"
    )
