# Q&A script for CodeAtlas.
# Takes a user question in plain English, searches ChromaDB for relevant
# code chunks across an entire project, enriches with Neo4j graph context,
# and sends everything to Gemini Flash to generate a grounded answer.
#
# This is the final piece of the RAG pipeline:
#   ChromaDB (semantic search across all repos) + Neo4j (structural context) → Gemini (answer)
#
# Usage:
#   PYTHONPATH=. uv run python3 qa/ask.py <project> "<question>"
#   PYTHONPATH=. uv run python3 qa/ask.py codeatlas/sample "how is the average calculated?"
#   PYTHONPATH=. uv run python3 qa/ask.py codeatlas/ecommerce "how does order reservation work?"
#
# The project identifier is a path like "owner/project" or "owner/project/repo".
# If multiple repos exist in the project, searches all of them in parallel.

import os
import sys

import chromadb
from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2
from dotenv import load_dotenv
from openai import OpenAI
from neo4j import GraphDatabase, Driver

# load credentials from .env
load_dotenv()

# number of ChromaDB chunks to retrieve per question
TOP_K = 3

# OpenAI model to use
OPENAI_MODEL = "gpt-4o-mini"

# Neo4j connection settings
NEO4J_URI      = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

openai_client = OpenAI(api_key=OPENAI_API_KEY)


def find_repos_in_project(project_path: str) -> list[str]:
    """
    Finds all repo names (ChromaDB collections) for a given project.

    Scans the output folder for _project.json files that match the project path.
    Returns a list of unique repo names found.

    Example: project_path="codeatlas/ecommerce" finds all repos in
    output/codeatlas/ecommerce/ folders (inventory_service, order_service, etc.)
    """
    from pathlib import Path
    import json

    output_root = Path("output")
    repos = set()

    # scan output folder for _project.json files
    for project_json in output_root.rglob("_project.json"):
        try:
            with open(project_json, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            # check if this project matches the requested one
            # project_path can be "owner/project" or "owner/project/repo"
            path_parts = project_path.split("/")
            meta_owner = metadata.get("owner", "")
            meta_project = metadata.get("project", "")
            meta_repo = metadata.get("repo", "")

            # match owner/project
            if len(path_parts) >= 2:
                if meta_owner == path_parts[0] and meta_project == path_parts[1]:
                    repos.add(meta_repo)

            # match owner/project/repo (specific repo)
            if len(path_parts) >= 3:
                if meta_owner == path_parts[0] and meta_project == path_parts[1] and meta_repo == path_parts[2]:
                    repos.add(meta_repo)
        except Exception:
            # skip files that can't be parsed
            pass

    return sorted(list(repos))


def search_chromadb(project_path: str, question: str) -> list[dict]:
    """
    Searches ChromaDB across all repos in a project for the most semantically
    similar chunks to the question.

    Finds all ChromaDB collections for the project, queries each with the question,
    and combines results. Returns the top K results overall, sorted by similarity.

    Returns a list of dicts, one per result, with keys:
    - id: the chunk ID (e.g. grade_calculator::utils.py::calculate_average)
    - text: the full chunk text
    - metadata: type, name, file, repo, last_modified
    - distance: how far the chunk vector is from the question vector (lower = more similar)
    """
    repos = find_repos_in_project(project_path)

    if not repos:
        return []

    client = chromadb.PersistentClient(path="chroma_db/")
    embedding_function = ONNXMiniLM_L6_V2()

    all_chunks = []

    # search each repo's collection
    for repo in repos:
        try:
            collection = client.get_collection(
                name=repo,
                embedding_function=embedding_function,
            )

            results = collection.query(
                query_texts=[question],
                n_results=min(TOP_K, collection.count()),
            )

            for i in range(len(results["ids"][0])):
                all_chunks.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                    "repo": repo,
                })
        except Exception:
            # collection might not exist, skip
            pass

    # sort by distance (lower = more similar) and take top K overall
    all_chunks.sort(key=lambda x: x["distance"])
    return all_chunks[:TOP_K]


def get_neo4j_context(driver: Driver, chunk: dict, repo: str) -> str:
    """
    Queries Neo4j for the structural context of a chunk.

    For a function chunk — finds what it calls and what calls it.
    For a method chunk — finds its class, what it calls, what calls it.
    For a class chunk — finds its methods.

    Returns a plain English string summarising the graph relationships.
    This string is added to the prompt so Gemini understands the structure.
    """
    chunk_type = chunk["metadata"].get("type", "")
    name = chunk["metadata"].get("name", "")
    file_name = chunk["metadata"].get("file", "")
    context_lines = []

    with driver.session() as session:

        if chunk_type in ("function", "method"):
            # what does this function/method call?
            result = session.run(
                """
                MATCH (caller {name: $name, file: $file, repo: $repo})-[:CALLS]->(callee)
                RETURN callee.name AS callee, callee.file AS callee_file
                """,
                {"name": name, "file": file_name, "repo": repo},
            )
            callees = [f"{r['callee']} (in {r['callee_file']})" for r in result]
            if callees:
                context_lines.append(f"{name} calls: {', '.join(callees)}")

            # what calls this function/method?
            result = session.run(
                """
                MATCH (caller)-[:CALLS]->(callee {name: $name, file: $file, repo: $repo})
                RETURN caller.name AS caller, caller.file AS caller_file
                """,
                {"name": name, "file": file_name, "repo": repo},
            )
            callers = [f"{r['caller']} (in {r['caller_file']})" for r in result]
            if callers:
                context_lines.append(f"{name} is called by: {', '.join(callers)}")

            # if it is a method, what class does it belong to?
            if chunk_type == "method":
                class_name = chunk["metadata"].get("class", "")
                if class_name:
                    context_lines.append(f"{name} is a method of class {class_name}")

        elif chunk_type == "class":
            # what methods does this class have?
            result = session.run(
                """
                MATCH (c:Class {name: $name, file: $file, repo: $repo})-[:HAS_METHOD]->(m:Method)
                RETURN m.name AS method
                """,
                {"name": name, "file": file_name, "repo": repo},
            )
            methods = [r["method"] for r in result]
            if methods:
                context_lines.append(f"{name} has methods: {', '.join(methods)}")

        # which file contains this node?
        context_lines.append(f"{name} is defined in {file_name}")

    return "\n".join(context_lines) if context_lines else ""


def build_prompt(question: str, chunks: list[dict], neo4j_contexts: list[str]) -> str:
    """
    Builds the full prompt to send to Gemini.

    Combines:
    - A system instruction telling Gemini its role
    - The retrieved code chunks as context
    - The Neo4j structural context for each chunk
    - The user's question

    The richer the context, the better Gemini's answer.
    This is the core of RAG — Retrieval Augmented Generation.
    """
    prompt_lines = [
        "You are an expert software engineer helping a developer understand a codebase.",
        "Answer the question using ONLY the code context provided below.",
        "If the answer is not in the context, say so clearly.",
        "",
        "=== CODE CONTEXT ===",
        "",
    ]

    for i, (chunk, neo4j_context) in enumerate(zip(chunks, neo4j_contexts), start=1):
        prompt_lines.append(f"--- Context {i} ---")
        prompt_lines.append(chunk["text"])
        if neo4j_context:
            prompt_lines.append("")
            prompt_lines.append("Graph relationships:")
            prompt_lines.append(neo4j_context)
        prompt_lines.append("")

    prompt_lines.extend([
        "=== QUESTION ===",
        "",
        question,
        "",
        "=== ANSWER ===",
    ])

    return "\n".join(prompt_lines)


def ask_openai(prompt: str) -> str:
    """
    Sends the prompt to OpenAI GPT-4o mini and returns the generated answer.

    Uses the openai SDK. The API key is read from .env.
    OpenAI reads the code context in the prompt and generates a
    plain English answer grounded in the actual code.
    """
    response = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def ask(project_path: str, question: str) -> None:
    """
    Orchestrates the full Q&A pipeline for one question.

    Steps:
    1. Find all repos in the project
    2. Search ChromaDB across all repos for relevant chunks
    3. Connect to Neo4j and enrich each chunk with graph context
    4. Build the prompt combining chunks + graph context + question
    5. Send to Gemini Flash and print the answer

    project_path should be "owner/project" or "owner/project/repo" format.
    """
    print(f"\nQuestion : {question}")
    print(f"Project  : {project_path}")
    print(f"{'='*60}")

    # step 1 — find relevant chunks across all repos in the project
    print("\nSearching ChromaDB across project repos...")
    chunks = search_chromadb(project_path, question)

    if not chunks:
        print("No relevant chunks found. Has the project been indexed?")
        return

    print(f"Found {len(chunks)} relevant chunks:")
    for chunk in chunks:
        similarity = round(1 - chunk["distance"], 4)
        repo_display = chunk.get("repo", "?")
        print(f"  {chunk['metadata'].get('type', '?'):8} {chunk['metadata'].get('name', '?')} (repo: {repo_display}, similarity: {similarity})")

    # step 2 — enrich with Neo4j graph context
    print("\nFetching Neo4j context...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    neo4j_contexts = []
    try:
        for i, chunk in enumerate(chunks, start=1):
            # get repo from chunk metadata (added by search_chromadb)
            repo = chunk.get("repo", "unknown")
            context = get_neo4j_context(driver, chunk, repo)
            neo4j_contexts.append(context)

            # display what Neo4j found for this chunk
            chunk_name = chunk['metadata'].get('name', '?')
            if context:
                print(f"\n  [{i}] {chunk_name} ({repo}) — graph context:")
                for line in context.split('\n'):
                    print(f"      {line}")
            else:
                print(f"\n  [{i}] {chunk_name} ({repo}) — no graph context found")
    finally:
        driver.close()

    # step 3 — build prompt
    prompt = build_prompt(question, chunks, neo4j_contexts)

    # step 4 — ask OpenAI
    print("\nAsking OpenAI GPT-4o mini...")
    answer = ask_openai(prompt)

    print(f"\n{'='*60}")
    print("Answer:")
    print(f"{'='*60}")
    print(answer)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: PYTHONPATH=. uv run python3 qa/ask.py <project> \"<question>\"")
        print("\nExamples:")
        print("  PYTHONPATH=. uv run python3 qa/ask.py codeatlas/sample \"question\"")
        print("  PYTHONPATH=. uv run python3 qa/ask.py codeatlas/ecommerce \"question\"")
        sys.exit(1)

    PROJECT_PATH = sys.argv[1]
    QUESTION     = sys.argv[2]
    ask(PROJECT_PATH, QUESTION)
