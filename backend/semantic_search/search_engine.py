
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


# 1. Define database location
CURRENT_DIR = Path(__file__).resolve().parent
DB_PATH = CURRENT_DIR / "chroma_db"

# 2. Load embedding model
print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

# 3. Connect to ChromaDB
client = chromadb.PersistentClient(path=str(DB_PATH))

collection = client.get_collection(
    name="supportpilot_knowledge_base"
)


def search_documents(ticket_text, top_k=3):
    """
    Find the most relevant knowledge-base documents
    for a given support ticket.
    """

    if not ticket_text or not ticket_text.strip():
        raise ValueError("Ticket text cannot be empty.")

    # Convert ticket into an embedding
    query_embedding = model.encode(ticket_text).tolist()

    # Search for similar documents
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"]
    )

    retrieved_documents = []

    for i in range(len(results["ids"][0])):
        retrieved_documents.append({
            "chunk_id": results["ids"][0][i],
            "content": results["documents"][0][i],
            "title": results["metadatas"][0][i]["title"],
            "category": results["metadatas"][0][i]["category"],
            "source": results["metadatas"][0][i]["source"],
            "distance": results["distances"][0][i]
        })

    return retrieved_documents


# 4. Run a sample search
if __name__ == "__main__":

    ticket = "My laptop is unable to connect to the office Wi-Fi."

    print("\nSearching for relevant documents...")
    results = search_documents(ticket)

    print("\nTicket:", ticket)
    print("\nTop matching documents:")

    for rank, doc in enumerate(results, start=1):
        print(f"\nResult {rank}")
        print("Title:", doc["title"])
        print("Category:", doc["category"])
        print("Content:", doc["content"])
        print("Distance:", round(doc["distance"], 4))
