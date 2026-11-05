from pathlib import Path
import joblib


# Project folder
BASE_DIR = Path(__file__).resolve().parent.parent

# Model paths
CATEGORY_MODEL_PATH = BASE_DIR / "models" / "category_classifier.pkl"
PRIORITY_MODEL_PATH = BASE_DIR / "models" / "priority_classifier.pkl"


# Load trained models
category_model = joblib.load(CATEGORY_MODEL_PATH)
priority_model = joblib.load(PRIORITY_MODEL_PATH)

print("Models loaded successfully.")


# Sample support tickets
tickets = [
    "The office Wi-Fi is not connecting to my laptop.",
    "Microsoft Outlook keeps crashing when I open it.",
    "My laptop screen is not working.",
    "I cannot access my company account."
]


# Predict category and priority
for ticket in tickets:

    category = category_model.predict([ticket])[0]
    priority = priority_model.predict([ticket])[0]

    print("\n--------------------------------")
    print("Ticket:", ticket)
    print("Predicted Category:", category)
    print("Predicted Priority:", priority)