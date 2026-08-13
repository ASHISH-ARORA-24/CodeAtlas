# Long-term memory store for CodeAtlas.
# Persists reusable project knowledge to a JSON file.
# Can be replaced with PostgreSQL or a vector DB later without changing the API.

import json
import sys
from pathlib import Path

MEMORY_FILE = Path(__file__).parent / "project_memory.json"


def load_memory() -> dict:
    """Loads all memories from project_memory.json. Returns empty dict if file doesn't exist."""
    if not MEMORY_FILE.exists():
        return {}
    content = MEMORY_FILE.read_text(encoding="utf-8")
    return json.loads(content) if content.strip() else {}


def save_memory(project: str, key: str, value: str) -> dict:
    """
    Saves one reusable piece of project knowledge.
    Updates the value if the key already exists — no duplicate keys.
    """
    memory = load_memory()

    if project not in memory:
        memory[project] = []

    existing = next((m for m in memory[project] if m["key"] == key), None)

    if existing:
        existing["value"] = value
        status = "updated"
    else:
        memory[project].append({"key": key, "value": value})
        status = "created"

    MEMORY_FILE.write_text(json.dumps(memory, indent=2), encoding="utf-8")

    return {"project": project, "key": key, "value": value, "status": status}


def get_memories(project: str) -> list:
    """Returns all long-term memories for a project."""
    return load_memory().get(project, [])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  PYTHONPATH=. uv run python3 memory/memory_store.py get <project>")
        print("  PYTHONPATH=. uv run python3 memory/memory_store.py save <project> <key> <value>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "get":
        if len(sys.argv) < 3:
            print("Project required.")
            sys.exit(1)
        print(json.dumps(get_memories(sys.argv[2]), indent=2))

    elif command == "save":
        if len(sys.argv) < 5:
            print("Usage: save <project> <key> <value>")
            sys.exit(1)
        print(json.dumps(save_memory(project=sys.argv[2], key=sys.argv[3], value=sys.argv[4]), indent=2))

    else:
        print(f"Unknown command: {command}")
