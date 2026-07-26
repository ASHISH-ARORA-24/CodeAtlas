# CodeAtlas — Architecture Decision Records

This document records every significant technical decision made during the project.
For each decision we document: what we chose, what we rejected, and why.
This helps future readers (and future us) understand the reasoning behind the code.

---

## Decision 1 — Local Repo Storage Structure

**Chose:** `source/<owner>/<project>/<repo>/`
**Rejected:** `source/<owner>/<repo>/` (GitHub's two-level structure)
**Why:** The extra `project` level groups related repos together (e.g. all microservices of one platform). This maps directly to the Neo4j graph hierarchy and enables cross-repo questions like "what does the payment service call in the inventory service?"
**Revisit:** No change planned. This structure scales to Iteration 3 microservices without modification.

---

## Decision 2 — Embedding Model

**Chose:** Sentence Transformers (local, free)
**Rejected:** OpenAI Embeddings API, Gemini Embeddings API
**Why:** Completely free, runs on CPU with no API key needed. Quality is sufficient for a learning project. The same model must be used at index time and query time — and a local model gives us full control over this.
**Revisit:** In Iteration 3 (Azure deployment), switch to a cloud embedding model for scalability.

---

## Decision 3 — AI Q&A Model

**Chose:** Gemini Flash (free tier)
**Rejected:** OpenAI GPT, Claude API, local Ollama models
**Why:** Gemini Flash has a genuinely free tier (1500 requests/day) with no credit card required. At learning-project query volume this costs nothing. Local models (Ollama) are free but answer quality is poor enough to frustrate learning.
**Revisit:** In Iteration 3 (Azure deployment), switch to Azure OpenAI Service using the $200 free credit.

---

## Decision 4 — Crawler and Chunker as Separate Files

**Chose:** `crawlers/python_ast.py` and `chunkers/python_chunker.py` as two separate scripts with JSON as the contract between them
**Rejected:** One combined script that crawls and chunks in one go
**Why:** Each script has one job. The JSON file between them acts as a warehouse — the crawler writes to it, the chunker reads from it. This means the chunker never needs to know about source code or AST. It also means any crawler (Python, JavaScript, Go) can produce the same JSON format and the chunker works unchanged.
**Revisit:** No change planned. This pattern scales directly to the microservices architecture in Iteration 3 where crawler and chunker become separate services.

---

## Decision 5 — One JSON File per Python File

**Chose:** One JSON file per crawled Python file, stored in `output/<project>/`
**Rejected:** One JSON file per project containing all files
**Why:** A single JSON for a large project (50+ files, long functions) would be huge — slow to read, slow to write, and potentially crash on low-memory machines. One JSON per file keeps each file small and allows the chunker to process files one at a time without loading everything into memory.
**Revisit:** No change planned. This approach scales to large projects without modification.

---

## Decision 6 — Chunk Splitting Strategy

**Chose:** Option A — split by line count when a function exceeds MAX_CHUNK_TOKENS (400 tokens)
**Rejected:** Option B — split by logical AST blocks (if, for, while boundaries)
**Why:** Option A is simple and teaches the core concept — chunks have a size limit, long functions get split with sequence numbers (chunk 1 of 3, chunk 2 of 3, etc.). Option B is smarter but requires deep nested AST traversal inside function bodies, adding complexity before the full pipeline is even working. In practice, functions following our coding standards (one function, one purpose) will rarely exceed 400 tokens anyway.
**Revisit:** Iteration 2 — replace line-based splitting with AST-aware logical block splitting for better chunk quality on large functions.

---

## Decision 7 — Actual Source Code Stored in JSON

**Chose:** Store the actual source code of each function, method, and class inside the JSON file
**Rejected:** Have the chunker read the original source files directly using line numbers
**Why:** The JSON becomes fully self-contained. The chunker only needs the JSON — it never needs to know where the source files are. This also makes the JSON the common contract between crawlers and chunkers — a JavaScript crawler producing the same JSON format would work with the same chunker unchanged.
**Revisit:** No change planned. This is the right design at all iteration levels.
