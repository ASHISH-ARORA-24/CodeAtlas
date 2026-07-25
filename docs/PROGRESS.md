# CodeAtlas — Progress

This document is updated after every logical chunk is completed. It serves as the living record of what has been built, what was learned, and what is still pending.

---

## Current Phase: Iteration 1 — Simple Scripts

**Goal:** Get the end-to-end flow working with the simplest possible code. No framework, no structure. Just understand the concepts.

**End-to-end flow:**
1. Download a public GitHub repo
2. Parse the code files
3. Split code into chunks
4. Convert chunks to embeddings and store in ChromaDB
5. Build a knowledge graph in Neo4j from code relationships
6. Accept a user question
7. Search ChromaDB for relevant chunks
8. Query Neo4j for structural context
9. Send everything to Gemini Flash and return the answer

---

## Chunks

### Chunk 1 — Project Setup and Discussion
- **Status:** ✅ Done
- **What we did:** Discussed the full concept of CodeAtlas, decided on the tech stack, understood what embeddings are, why the same model must be used for storing and searching, and why we combine vector search with a knowledge graph. Also decided on the local repo folder structure.
- **Key learnings:**
  - An embedding is a list of numbers representing the *meaning* of text
  - Similar meaning = similar numbers = close in vector space
  - The same embedding model must be used at index time and query time
  - Vector search handles semantic similarity; graph handles structural relationships
  - We use Gemini Flash (free tier) for Q&A, Sentence Transformers (local) for embeddings
  - Local repos are stored as `source/<owner>/<project>/<repo>/`
  - The `project` level groups related repos (e.g. all microservices of one platform)
  - This structure maps directly to the Neo4j graph hierarchy: `Owner → Project → Repo → File → Function/Class`
  - This enables cross-repo questions like "what does service A call in service B?"

### Chunk 2 — Download a GitHub Repo
- **Status:** 🔲 Pending

### Chunk 3 — Parse and Chunk Code Files
- **Status:** 🔲 Pending

### Chunk 4 — Generate Embeddings and Store in ChromaDB
- **Status:** 🔲 Pending

### Chunk 5 — Build Knowledge Graph in Neo4j
- **Status:** 🔲 Pending

### Chunk 6 — Question Answering with Gemini Flash
- **Status:** 🔲 Pending

### Chunk 7 — Wire Everything Together (End-to-End Script)
- **Status:** 🔲 Pending

---

## Iteration 2 — Structured Python Project
- **Status:** 🔲 Not started

## Iteration 3 — Microservices on Azure
- **Status:** 🔲 Not started
