
from pathlib import Path
import json
import pandas as pd

# Define project directories
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

# Define generated files
json_file = DATA_DIR / "knowledge_base.json"
csv_file = DATA_DIR / "knowledge_base_chunks.csv"
jsonl_file = DATA_DIR / "knowledge_base_chunks.jsonl"

required_fields = [
    "document_id",
    "title",
    "category",
    "content",
    "source",
]

chunk_fields = [
    "chunk_id",
    "document_id",
    "title",
    "category",
    "content",
    "source",
]

errors = []

print("=" * 55)
print("SUPPORTPILOT KNOWLEDGE BASE VALIDATION")
print("=" * 55)

# 1. Check that all output files exist
for file_path in [json_file, csv_file, jsonl_file]:
    if file_path.exists():
        print(f"PASS: File exists - {file_path.name}")
    else:
        errors.append(f"Missing file: {file_path.name}")
        print(f"FAIL: File missing - {file_path.name}")

# Stop if a required file is missing
if errors:
    print("\nVALIDATION FAILED.")
    for error in errors:
        print("-", error)
    raise SystemExit(1)

# 2. Validate the knowledge base JSON
try:
    with open(json_file, "r", encoding="utf-8") as file:
        documents = json.load(file)

    if not isinstance(documents, list):
        errors.append("Knowledge base JSON must contain a list.")
    else:
        print(f"\nJSON documents loaded: {len(documents)}")

        for index, document in enumerate(documents, start=1):
            missing = set(required_fields) - set(document.keys())
            if missing:
                errors.append(
                    f"JSON document {index} missing fields: "
                    f"{sorted(missing)}"
                )
                continue

            for field in required_fields:
                if not str(document[field]).strip():
                    errors.append(
                        f"JSON document {index} has empty field: {field}"
                    )

        document_ids = [
            document.get("document_id")
            for document in documents
        ]

        if len(document_ids) != len(set(document_ids)):
            errors.append("Duplicate document IDs found in JSON.")
        else:
            print("PASS: JSON fields and document IDs")

except (json.JSONDecodeError, OSError) as exc:
    errors.append(f"Could not read knowledge_base.json: {exc}")

# 3. Validate the chunk CSV
try:
    chunks_df = pd.read_csv(csv_file, encoding="utf-8-sig")

    missing_fields = set(chunk_fields) - set(chunks_df.columns)

    if missing_fields:
        errors.append(
            f"CSV missing required columns: {sorted(missing_fields)}"
        )
    else:
        print(f"\nCSV chunks loaded: {len(chunks_df)}")

        if chunks_df.empty:
            errors.append("Chunk CSV contains no records.")

        if chunks_df["chunk_id"].duplicated().any():
            errors.append("Duplicate chunk IDs found in CSV.")
        else:
            print("PASS: Chunk IDs are unique")

        for field in chunk_fields:
            empty_mask = (
                chunks_df[field].isna()
                | chunks_df[field].astype(str).str.strip().eq("")
            )

            if empty_mask.any():
                errors.append(
                    f"CSV contains {int(empty_mask.sum())} "
                    f"empty values in '{field}'."
                )

        if not errors:
            print("PASS: CSV required fields are populated")

except (pd.errors.ParserError, OSError, UnicodeError) as exc:
    errors.append(f"Could not read knowledge_base_chunks.csv: {exc}")

# 4. Validate the JSONL file
try:
    jsonl_chunks = []

    with open(jsonl_file, "r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                errors.append(
                    f"JSONL contains an empty line at {line_number}."
                )
                continue

            try:
                chunk = json.loads(line)
                jsonl_chunks.append(chunk)

                if not isinstance(chunk, dict):
                    errors.append(
                        f"JSONL line {line_number} must contain an object."
                    )
                    continue

                missing = set(chunk_fields) - set(chunk.keys())

                if missing:
                    errors.append(
                        f"JSONL line {line_number} missing fields: "
                        f"{sorted(missing)}"
                    )
                    continue

                for field in chunk_fields:
                    if not str(chunk[field]).strip():
                        errors.append(
                            f"JSONL line {line_number} has empty field: "
                            f"{field}"
                        )

            except json.JSONDecodeError:
                errors.append(
                    f"Invalid JSON on JSONL line {line_number}."
                )

    print(f"\nJSONL chunks loaded: {len(jsonl_chunks)}")

    jsonl_ids = [
        chunk["chunk_id"]
        for chunk in jsonl_chunks
        if isinstance(chunk, dict) and "chunk_id" in chunk
    ]

    if len(jsonl_ids) != len(set(jsonl_ids)):
        errors.append("Duplicate chunk IDs found in JSONL.")
    else:
        print("PASS: JSONL chunk IDs are unique")

except OSError as exc:
    errors.append(f"Could not read knowledge_base_chunks.jsonl: {exc}")

# 5. Compare CSV and JSONL chunk counts and IDs
if "chunks_df" in locals() and "jsonl_chunks" in locals():
    if len(chunks_df) != len(jsonl_chunks):
        errors.append("CSV and JSONL chunk counts do not match.")
    else:
        print("PASS: CSV and JSONL chunk counts match")

    if "chunk_id" in chunks_df.columns:
        csv_ids = set(chunks_df["chunk_id"].dropna().astype(str))
        jsonl_id_set = set(str(value) for value in jsonl_ids)

        if csv_ids != jsonl_id_set:
            errors.append("CSV and JSONL chunk IDs do not match.")
        else:
            print("PASS: CSV and JSONL chunk IDs match")

# 6. Final result
print("\n" + "=" * 55)

if errors:
    print(f"VALIDATION FAILED: {len(errors)} issue(s) found.")
    for error in errors:
        print(f"- {error}")

    raise SystemExit(1)

print("ALL VALIDATION CHECKS PASSED!")
print(f"Documents: {len(documents)}")
print(f"Chunks: {len(chunks_df)}")
print(f"Unique chunk IDs: {chunks_df['chunk_id'].nunique()}")
print("Empty chunk content: 0")
print("=" * 55)
