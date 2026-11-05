
# SupportPilot - Semantic Search Engine

## Overview
The Semantic Search Engine retrieves relevant IT troubleshooting documents based on the meaning of a user's support ticket.

## Technologies Used
- Python
- Sentence Transformers
- ChromaDB
- Pandas

## Embedding Model
all-MiniLM-L6-v2

## Project Structure
```text
semantic_search/
├── build_vector_database.py
├── search_engine.py
├── test_search.py
└── chroma_db/
```

## Implementation

1. Read prepared knowledge-base chunks from the CSV file.
2. Generate text embeddings using Sentence Transformers.
3. Store document embeddings in ChromaDB.
4. Convert incoming support tickets into embeddings.
5. Retrieve the top three most relevant documents using semantic similarity.

## How to Run

### Step 1: Install dependencies
```bash
py -m pip install pandas sentence-transformers chromadb
```

### Step 2: Build the vector database
```bash
py semantic_search/build_vector_database.py
```

### Step 3: Run semantic search
```bash
py semantic_search/search_engine.py
```

### Step 4: Run test cases
```bash
py semantic_search/test_search.py
```

## Testing Results

Tested with eight IT support ticket scenarios:
- Wi-Fi connection issues
- Outlook email synchronization
- Password reset
- Slow computer
- Printer issues
- VPN connection
- Application crashing
- Audio issues

All eight test cases retrieved the expected document as the top result.

## Deliverable
A working semantic document retrieval module for the SupportPilot project.
