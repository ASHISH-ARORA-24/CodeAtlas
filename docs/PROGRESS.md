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

### Chunk 5 — Smart Text Chunking for Embeddings
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
