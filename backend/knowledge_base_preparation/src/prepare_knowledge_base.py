
from pathlib import Path
import json
import pandas as pd
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Define project directories
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

# Input file
input_file = DATA_DIR / "cleaned_documents.csv"

# Load cleaned documents
df = pd.read_csv(input_file, encoding="utf-8-sig")

required_columns = [
    "document_id",
    "title",
    "category",
    "content",
    "source",
]

# Validate input columns
missing_columns = set(required_columns) - set(df.columns)

if missing_columns:
    raise ValueError(
        f"Missing required columns: {sorted(missing_columns)}"
    )

# Remove rows with missing required values
df = df.dropna(subset=required_columns).copy()

# Normalize text fields and correct known spacing issues
for column in required_columns:
    df[column] = df[column].astype(str).str.strip()
    df[column] = df[column].str.replace(
        r"\s+", " ", regex=True
    )

df["content"] = df["content"].str.replace(
    "thenetwork", "the network", regex=False
)
df["content"] = df["content"].str.replace(
    "Verifythe", "Verify the", regex=False
)
df["content"] = df["content"].str.replace(
    "process.Contact", "process. Contact", regex=False
)

# Remove rows with empty required values
for column in required_columns:
    df = df[df[column] != ""]

# Remove duplicate document IDs
df = df.drop_duplicates(
    subset=["document_id"],
    keep="first"
)

# Configure text splitter
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=80,
    separators=["\n\n", "\n", ". ", " ", ""]
)

knowledge_base = []
all_chunks = []

# Process each document
for _, row in df.iterrows():
    document = {
        "document_id": str(row["document_id"]),
        "title": str(row["title"]),
        "category": str(row["category"]),
        "content": str(row["content"]),
        "source": str(row["source"]),
    }

    knowledge_base.append(document)

    # Split document content into smaller chunks
    chunks = splitter.split_text(document["content"])

    for index, chunk_text in enumerate(chunks, start=1):
        chunk = {
            "chunk_id": (
                f"{document['document_id']}_CHUNK{index:03d}"
            ),
            "document_id": document["document_id"],
            "title": document["title"],
            "category": document["category"],
            "content": chunk_text,
            "source": document["source"],
        }

        all_chunks.append(chunk)

# Save the complete knowledge base as JSON
with open(
    DATA_DIR / "knowledge_base.json",
    "w",
    encoding="utf-8"
) as file:
    json.dump(
        knowledge_base,
        file,
        indent=2,
        ensure_ascii=False
    )

# Save chunks as CSV
chunks_df = pd.DataFrame(all_chunks)

chunks_df.to_csv(
    DATA_DIR / "knowledge_base_chunks.csv",
    index=False,
    encoding="utf-8"
)

# Save chunks as JSON Lines
with open(
    DATA_DIR / "knowledge_base_chunks.jsonl",
    "w",
    encoding="utf-8"
) as file:
    for chunk in all_chunks:
        file.write(
            json.dumps(chunk, ensure_ascii=False) + "\n"
        )

# Display results
print("Knowledge base preparation completed.")
print(f"Original documents: {len(knowledge_base)}")
print(f"Generated chunks: {len(all_chunks)}")
print(
    f"Unique chunk IDs: {chunks_df['chunk_id'].nunique()}"
)
print(
    f"Empty chunks: {chunks_df['content'].isna().sum()}"
)
print("\nOutput files created:")
print("- data/knowledge_base.json")
print("- data/knowledge_base_chunks.csv")
print("- data/knowledge_base_chunks.jsonl")
