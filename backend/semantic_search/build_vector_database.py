
from pathlib import Path

import chromadb
import pandas as pd
from sentence_transformers import SentenceTransformer


# 1. Define project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent

CSV_PATH = (
    PROJECT_ROOT
    / "knowledge_base_preparation"
    / "data"
    / "knowledge_base_chunks.csv"
)

DB_PATH = Path(__file__).resolve().parent / "chroma_db"

# 2. Load the knowledge-base dataset
print("Loading knowledge-base data...")

df = pd.read_csv(CSV_PATH)

required_columns = [
    "chunk_id",
    "document_id",
    "title",
    "category",
    "content",
    "source",
]

if not all(column in df.columns for column in required_columns):
    raise ValueError("The CSV is missing required columns.")

df = df.dropna(subset=["chunk_id", "content"])

if df.empty:
    raise ValueError("No valid knowledge-base chunks found.")

print(f"Loaded {len(df)} document chunks.")

# 3. Load the embedding model
print("Loading Sentence Transformer model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

# 4. Generate embeddings
print("Generating embeddings...")

texts = df["content"].astype(str).tolist()
embeddings = model.encode(texts, show_progress_bar=True)

# 5. Create a persistent ChromaDB database
print("Creating ChromaDB database...")

client = chromadb.PersistentClient(path=str(DB_PATH))

collection = client.get_or_create_collection(
    name="supportpilot_knowledge_base",
    metadata={"hnsw:space": "cosine"},
)

# 6. Store documents, embeddings and metadata
collection.upsert(
    ids=df["chunk_id"].astype(str).tolist(),
    embeddings=embeddings.tolist(),
    documents=texts,
    metadatas=[
        {
            "document_id": str(row["document_id"]),
            "title": str(row["title"]),
            "category": str(row["category"]),
            "source": str(row["source"]),
        }
        for _, row in df.iterrows()
    ],
)

# Remove obsolete chunks only after the current snapshot has been upserted.
existing_ids = collection.get(include=[]).get("ids", [])
current_ids = set(df["chunk_id"].astype(str).tolist())
stale_ids = [chunk_id for chunk_id in existing_ids if chunk_id not in current_ids]
if stale_ids:
    collection.delete(ids=stale_ids)

# 7. Verify database
print("\nVector database created successfully!")
print("Total stored chunks:", collection.count())
print("Database location:", DB_PATH)
