
from pathlib import Path
import pandas as pd

# Define project directories
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

# Define input and output files
input_file = DATA_DIR / "raw_documents.csv"
output_file = DATA_DIR / "cleaned_documents.csv"

# Load raw documents
df = pd.read_csv(input_file, encoding="utf-8-sig")

# Required columns
required_columns = [
    "document_id",
    "title",
    "category",
    "content",
    "source",
]

# Validate required columns
missing_columns = set(required_columns) - set(df.columns)

if missing_columns:
    raise ValueError(
        f"Missing required columns: {sorted(missing_columns)}"
    )

# Remove rows with missing required values
df = df.dropna(subset=required_columns).copy()

# Clean whitespace in all text columns
for column in required_columns:
    df[column] = df[column].astype(str).str.strip()
    df[column] = df[column].str.replace(
        r"\s+", " ", regex=True
    )

# Correct known spacing issues in document content
df["content"] = df["content"].str.replace(
    "thenetwork", "the network", regex=False
)
df["content"] = df["content"].str.replace(
    "Verifythe", "Verify the", regex=False
)
df["content"] = df["content"].str.replace(
    "process.Contact", "process. Contact", regex=False
)

# Remove rows containing empty required fields
for column in required_columns:
    df = df[df[column] != ""]

# Remove duplicate document IDs
df = df.drop_duplicates(
    subset=["document_id"],
    keep="first"
)

# Save cleaned documents
df.to_csv(
    output_file,
    index=False,
    encoding="utf-8"
)

# Display validation summary
print("Knowledge base preprocessing completed.")
print(f"Input file: {input_file}")
print(f"Output file: {output_file}")
print(f"Cleaned documents: {len(df)}")
print(
    "Duplicate IDs:",
    df["document_id"].duplicated().sum()
)
print(
    "Empty content:",
    (df["content"].str.strip() == "").sum()
)
