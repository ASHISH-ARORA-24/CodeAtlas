# CodeAtlas — Progress

This document is updated after every logical chunk is completed. It serves as the living record of what has been built, what was learned, and what is still pending.

---

## Current Phase: Iteration 1 — Simple Scripts

**Goal:** Get the end-to-end flow working with the simplest possible code. No framework, no structure. Just understand the concepts.

**End-to-end flow:**
1. Repos are manually placed under `source/<owner>/<project>/<repo>/`
2. AST crawler reads each Python file and extracts functions, classes, methods
3. Split code into smart chunks (one chunk per function/method)
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

### Chunk 2 — Sample Repos and AST Crawler
- **Status:** ✅ Done
- **What we did:** Created sample repos under `source/codeatlas/sample/calculator/` with two files — `calculator.py` (standalone functions) and `calculator_v1.py` (class-based). Built `crawlers/python_ast.py` that reads any Python file and extracts structured information using Python's built-in `ast` module. Fixed two real issues discovered by testing: `self` appearing as a parameter, and methods having no connection to their class.
- **Key learnings:**
  - `ast.parse()` converts raw Python source code into a tree of nodes
  - Each node type represents a piece of code — `FunctionDef`, `ClassDef`, `Import`, `Return`, etc.
  - `ast.walk()` visits every node in the entire tree regardless of nesting — useful for global search but wrong when you need to know parent-child relationships
  - Iterating `tree.body` gives only top-level statements; iterating `class_node.body` gives only that class's methods — this is how we know where a function belongs
  - `self` is not a real parameter — it is Python's reference to the class instance and must be filtered out
  - `ast.get_docstring()` safely extracts docstrings from both functions and classes
  - `ast.unparse()` converts an annotation node back into a readable string (e.g. `float`, `list[str]`)
  - Parse the AST tree once and pass it to multiple extractors — avoid parsing the same file twice
  - The crawler command: `uv run crawlers/python_ast.py <file_path>`

### Chunk 3 — Complete Crawler with Imports, Calls, and Multi-file Support
- **Status:** ✅ Done
- **What we did:** Extended the AST crawler to accept a project folder path instead of a single file. Added `find_python_files` to walk the folder recursively, `extract_imports` to capture file-level dependencies, `extract_function_calls` to capture what each function calls inside its body, and `crawl_file` to return one structured dict per file — the final Neo4j-ready output. Created the `grade_calculator` sample project with functions, a class, imports, calls, and an intentional orphan function (`get_today_date`).
- **Key learnings:**
  - `pathlib.Path.rglob("*.py")` recursively finds all Python files in a folder
  - Two AST import node types: `ast.Import` (plain) and `ast.ImportFrom` (from-imports) — `ImportFrom` is the most valuable for graph edges
  - `ast.Call` nodes represent function calls inside a function body — `node.func.id` for simple calls, `node.func.attr` for method calls
  - The crawler now returns a structured dict per file: `{file, path, imports, functions, classes}` — ready to be stored in Neo4j
  - An orphan function is one that is defined but never called — detectable by comparing defined vs called function sets
  - Orphan detection is an analysis concern, not a crawler concern — it happens at the Neo4j query stage
  - The crawler command: `uv run --package codeatlas python3 crawlers/python_ast.py <project_path>`
  - Neo4j relationships the crawler enables: `File→IMPORTS→File`, `File→CONTAINS→Function`, `Class→HAS_METHOD→Method`, `Function→CALLS→Function`

### Chunk 4 — Module-Level Variables and Calls
- **Status:** ✅ Done
- **What we did:** Added `extract_module_level_variables` and `extract_module_level_calls` to the crawler. These capture everything at the top level of a file that is outside any function or class — global constants, global objects, and any direct calls. All of these are tagged to the file itself in Neo4j. Also added module-level variables and calls to `main.py` of the grade_calculator sample to test and demonstrate the feature.
- **Key learnings:**
  - `ast.Assign` captures simple assignments: `DEFAULT_PASS_MARK = 50`
  - `ast.AnnAssign` captures annotated assignments: `count: int = 0`
  - Module-level calls are found by walking all top-level nodes that are not `FunctionDef`, `ClassDef`, or `Import`
  - Everything at module level is tagged to the file: `File → HAS_VARIABLE → var`, `File → CALLS → function`
  - Known limitation: `self.attr = ClassName()` inside `__init__` — the crawler captures the call to `ClassName` but cannot link `self.attr` to that type automatically (type inference problem)
  - Known limitation: function parameters typed as a class (e.g. `profile: StudentProfile`) — the type hint is captured, but the link between calls inside that function and the class is not automatic. It is queryable in Neo4j using the type hint.
  - Known limitation: Python built-ins (`sum`, `len`, `print`) appear as calls but have no corresponding nodes — filtered at the Neo4j query stage

### Chunk 5 — crawl_project.py with JSON output and incremental crawling
- **Status:** ✅ Done
- **What we did:** Built `crawlers/crawl_project.py` which orchestrates the full crawling pipeline — finds all Python files, calls `crawl_file()` from `python_ast.py`, mirrors the source folder structure under `output/`, and saves one JSON file per Python file. Added incremental crawling using file timestamps — unchanged files are skipped on subsequent runs. Added `attach_timestamp_to_result` to reflect the file-level timestamp onto every function, class, and method in the JSON. Also updated `python_ast.py` to include actual source code of each function and class using `ast.get_source_segment()` so the JSON is fully self-contained.
- **Key learnings:**
  - The pipeline pattern: `python_ast.py` extracts, `crawl_project.py` orchestrates and saves — each has one job
  - Output folder mirrors source folder exactly: `source/x/y/z.py` → `output/x/y/z.json`
  - One JSON file per Python file — avoids memory issues on large projects
  - `_project.json` is the index file — records owner, project, repo, crawl date, and list of output files
  - Incremental crawling: compare file's `st_mtime` (last modified time) against stored timestamp in JSON — skip if unchanged
  - Deleting the output folder forces a full re-crawl — the script handles both fresh start and incremental update with the same logic
  - File timestamp is reflected onto all functions, classes, and methods from that file — OS only tracks timestamps at file level, not per function
  - `ast.get_source_segment(source_code, node)` extracts the exact source code for any AST node
  - JSON is fully self-contained — the chunker only needs the JSON, never the original source files
  - Command: `PYTHONPATH=. uv run --package codeatlas python3 crawlers/crawl_project.py <project_path>`

### Chunk 6 — python_chunker.py with ChromaDB vector storage
- **Status:** ✅ Done
- **What we did:** Built `chunkers/python_chunker.py` which reads the JSON files produced by `crawl_project.py` and stores rich text chunks in ChromaDB as vector embeddings. Supports incremental updates — files with unchanged timestamps are skipped, stale chunks for deleted functions are removed automatically. Explicitly declared the embedding model (`all-MiniLM-L6-v2`) so it never changes accidentally. Documented the model choice in `DECISIONS.md`.
- **Key learnings:**
  - ChromaDB does three things in one call: takes text, converts to vector, saves both — we never call the embedding model manually
  - `collection.upsert()` adds a new chunk or updates an existing one if the ID already exists — no duplicates
  - Chunk ID format: `repo::file::name` (e.g. `grade_calculator::utils.py::calculate_average`) — unique and stable across runs
  - For class methods the ID includes the class: `grade_calculator::utils.py::StudentProfile::get_summary`
  - A class produces N+1 chunks — one for the class itself, one per method
  - Stale chunk detection: get existing IDs from ChromaDB for the file, compare with new IDs, delete the difference
  - The embedding model must be explicitly declared and must be the same at index time and query time — implicit defaults are dangerous
  - `all-MiniLM-L6-v2` is a general-purpose model — good for Iteration 1, upgrade to a code-aware model in Iteration 2
  - ChromaDB collection = one per repo — like a table in a relational database
  - `chroma_db/` folder is added to `.gitignore` — database files are never committed
  - Command: `PYTHONPATH=. uv run python3 chunkers/python_chunker.py <project_path>`

### Chunk 7 — Build Knowledge Graph in Neo4j
- **Status:** 🔲 Pending

### Chunk 6 — Generate Embeddings and Store in ChromaDB
- **Status:** 🔲 Pending

### Chunk 7 — Build Knowledge Graph in Neo4j
- **Status:** 🔲 Pending

### Chunk 8 — Question Answering with Gemini Flash
- **Status:** 🔲 Pending

### Chunk 7 — Wire Everything Together (End-to-End Script)
- **Status:** 🔲 Pending

---

## Iteration 2 — Structured Python Project
- **Status:** 🔲 Not started

## Iteration 3 — Microservices on Azure
- **Status:** 🔲 Not started
