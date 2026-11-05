
from pathlib import Path
import pandas as pd

# 1. Locate the project folder and dataset
BASE_DIR = Path(__file__).resolve().parent.parent

input_path = BASE_DIR / "dataset" / "general_dataset.csv"
output_path = BASE_DIR / "dataset" / "cleaned_dataset.csv"

# 2. Load the original dataset
df = pd.read_csv(input_path)

print("Original dataset shape:", df.shape)

# 3. Handle missing subject and body values
df["subject"] = df["subject"].fillna("")
df["body"] = df["body"].fillna("")

# 4. Remove unnecessary spaces
df["subject"] = df["subject"].astype(str).str.strip()
df["body"] = df["body"].astype(str).str.strip()

# 5. Combine subject and body into ticket_text
df["ticket_text"] = (
    df["subject"] + " " + df["body"]
).str.strip()

# 6. Remove rows with no usable ticket text
df = df[df["ticket_text"].ne("")].copy()

# 7. Check that target labels are available
df = df.dropna(subset=["type", "priority"])

# 8. Check for duplicate ticket text
duplicate_texts = df["ticket_text"].duplicated().sum()
print("Repeated ticket texts:", duplicate_texts)

# Keep repeated ticket texts for now.
# We should inspect them before deciding whether to remove them.

# 9. Select columns needed for SupportPilot
df = df[
    [
        "ticket_text",
        "type",
        "priority",
        "language",
        "queue",
        "answer"
    ]
].copy()

# 10. Save the cleaned dataset
df.to_csv(output_path, index=False, encoding="utf-8")

# 11. Display the results
print("\nData cleaning completed!")
print("Cleaned dataset path:", output_path)
print("Cleaned dataset shape:", df.shape)

print("\nFirst 5 cleaned tickets:")
print(df[["ticket_text", "type", "priority"]].head().to_string())

print("\nMissing values in selected columns:")
print(df.isnull().sum())