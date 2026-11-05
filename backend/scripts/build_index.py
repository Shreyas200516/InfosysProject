"""Build the ChromaDB vector index from the combined knowledge base.
Run once (needs internet the first time to download the all-MiniLM-L6-v2 embedding model):
    python -m scripts.build_index
"""
import csv
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from app.config import BACKEND_DIR, settings

CSV_PATH = BACKEND_DIR / "data" / "knowledge_base_combined.csv"
COLLECTION = "supportpilot_knowledge_base"  # same name the team's retriever expects


def main() -> None:
    rows = [r for r in csv.DictReader(CSV_PATH.open(encoding="utf-8-sig", newline="")) if r["content"].strip()]
    print(f"Embedding {len(rows)} chunks from {CSV_PATH.name} ...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode([r["content"] for r in rows], show_progress_bar=True).tolist()
    Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)
    col = chromadb.PersistentClient(path=settings.chroma_path).get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    col.upsert(ids=[r["chunk_id"] for r in rows], embeddings=embeddings, documents=[r["content"] for r in rows],
               metadatas=[{k: r[k] for k in ("document_id", "title", "category", "source")} for r in rows])
    stale = [i for i in col.get(include=[]).get("ids", []) if i not in {r["chunk_id"] for r in rows}]
    if stale:
        col.delete(ids=stale)
    print(f"Done. {col.count()} chunks in {settings.chroma_path}")


if __name__ == "__main__":
    main()
