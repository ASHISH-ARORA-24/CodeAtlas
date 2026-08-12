# Q&A script for CodeAtlas.
# Takes a user question in plain English, searches ChromaDB for relevant
# code chunks, enriches with Neo4j graph context, and sends everything
# to Gemini Flash to generate a grounded answer.
#
# This is the final piece of the RAG pipeline:
#   ChromaDB (semantic search) + Neo4j (structural context) → Gemini (answer)
#
# Usage:
#   PYTHONPATH=. uv run python3 qa/ask.py <repo> "<question>"
#   PYTHONPATH=. uv run python3 qa/ask.py grade_calculator "how is the average calculated?"

import os
import sys

import chromadb
from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2
from dotenv import load_dotenv
from google import genai
from neo4j import GraphDatabase, Driver

# load credentials from .env
load_dotenv()

# number of ChromaDB chunks to retrieve per question
TOP_K = 3

# Gemini model to use — Flash is fast and free tier
GEMINI_MODEL = "gemini-flash-latest"

# Neo4j connection settings
NEO4J_URI      = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def search_chromadb(repo: str, question: str) -> list[dict]:
    """
    Searches ChromaDB for the most semantically similar chunks to the question.

    Converts the question to a vector using the same embedding model used
    at index time (all-MiniLM-L6-v2) and finds the top K closest chunks.

    Returns a list of dicts, one per result, with keys:
    - id: the chunk ID (e.g. grade_calculator::utils.py::calculate_average)
    - text: the full chunk text
    - metadata: type, name, file, last_modified
    - distance: how far the chunk vector is from the question vector (lower = more similar)
    """
    client = chromadb.PersistentClient(path="chroma_db/")
    collection = client.get_collection(
        name=repo,
        embedding_function=ONNXMiniLM_L6_V2(),
    )

    results = collection.query(
        query_texts=[question],
        n_results=min(TOP_K, collection.count()),
    )

    chunks = []
    for i in range(len(results["ids"][0])):
        chunks.append({
            "id": results["ids"][0][i],
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })

    return chunks


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


def ask_gemini(prompt: str) -> str:
    """
    Sends the prompt to Gemini Flash and returns the generated answer.

    Uses the google-genai SDK. The API key is read from .env.
    Gemini reads the code context in the prompt and generates a
    plain English answer grounded in the actual code.
    """
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return response.text


def ask(repo: str, question: str) -> None:
    """
    Orchestrates the full Q&A pipeline for one question.

    Steps:
    1. Search ChromaDB for relevant chunks
    2. Connect to Neo4j and enrich each chunk with graph context
    3. Build the prompt combining chunks + graph context + question
    4. Send to Gemini Flash and print the answer
    """
    print(f"\nQuestion : {question}")
    print(f"Repo     : {repo}")
    print(f"{'='*60}")

    # step 1 — find relevant chunks
    print("\nSearching ChromaDB...")
    chunks = search_chromadb(repo, question)

    if not chunks:
        print("No relevant chunks found. Has the repo been indexed?")
        return

    print(f"Found {len(chunks)} relevant chunks:")
    for chunk in chunks:
        similarity = round(1 - chunk["distance"], 4)
        print(f"  {chunk['metadata'].get('type', '?'):8} {chunk['metadata'].get('name', '?')} (similarity: {similarity})")

    # step 2 — enrich with Neo4j graph context
    print("\nFetching Neo4j context...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    neo4j_contexts = []
    try:
        for i, chunk in enumerate(chunks, start=1):
            context = get_neo4j_context(driver, chunk, repo)
            neo4j_contexts.append(context)

            # display what Neo4j found for this chunk
            chunk_name = chunk['metadata'].get('name', '?')
            if context:
                print(f"\n  [{i}] {chunk_name} — graph context:")
                for line in context.split('\n'):
                    print(f"      {line}")
            else:
                print(f"\n  [{i}] {chunk_name} — no graph context found")
    finally:
        driver.close()

    # step 3 — build prompt
    prompt = build_prompt(question, chunks, neo4j_contexts)

    # step 4 — ask Gemini
    print("\nAsking Gemini Flash...")
    answer = ask_gemini(prompt)

    print(f"\n{'='*60}")
    print("Answer:")
    print(f"{'='*60}")
    print(answer)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: PYTHONPATH=. uv run python3 qa/ask.py <repo> \"<question>\"")
        sys.exit(1)

    REPO     = sys.argv[1]
    QUESTION = sys.argv[2]
    ask(REPO, QUESTION)
