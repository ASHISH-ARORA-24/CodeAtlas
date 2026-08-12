import json
from pathlib import Path


# ---------------------------------------------------------
# MEMORY FILE
#
# This JSON file is our simple persistent memory database.
# Later we can replace this with PostgreSQL, vector DB, etc.
# ---------------------------------------------------------

MEMORY_FILE = Path(__file__).parent / "project_memory.json"


def load_memory() -> dict:
    """
    Load all memories from project_memory.json.

    Example return:

    {
        "codeatlas/ecommerce": [
            {
                "key": "test_framework",
                "value": "pytest"
            }
        ]
    }
    """

    if not MEMORY_FILE.exists():
        return {}

    content = MEMORY_FILE.read_text(
        encoding="utf-8"
    )

    # Empty file = empty memory.
    if not content.strip():
        return {}

    return json.loads(content)


def save_memory(
    project: str,
    key: str,
    value: str,
) -> dict:
    """
    Save one reusable piece of project knowledge.

    Example:

        save_memory(
            project="codeatlas/ecommerce",
            key="test_framework",
            value="pytest",
        )
    """

    memory = load_memory()

    # If this project has never been seen before,
    # create its memory list.
    if project not in memory:
        memory[project] = []

    project_memories = memory[project]

    # -----------------------------------------------------
    # If the key already exists, update it.
    #
    # Example:
    # test_framework = unittest
    #
    # later becomes:
    # test_framework = pytest
    #
    # We don't want duplicate memories.
    # -----------------------------------------------------

    existing_memory = next(
        (
            item
            for item in project_memories
            if item["key"] == key
        ),
        None,
    )

    if existing_memory:

        existing_memory["value"] = value

        status = "updated"

    else:

        project_memories.append(
            {
                "key": key,
                "value": value,
            }
        )

        status = "created"

    # -----------------------------------------------------
    # Persist memory to disk.
    # -----------------------------------------------------

    MEMORY_FILE.write_text(
        json.dumps(
            memory,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "project": project,
        "key": key,
        "value": value,
        "status": status,
    }


def get_memories(
    project: str,
) -> list:
    """
    Return all long-term memories for a project.

    Example:

        get_memories("codeatlas/ecommerce")

    might return:

        [
            {
                "key": "test_framework",
                "value": "pytest"
            },
            {
                "key": "naming_convention",
                "value": "snake_case"
            }
        ]
    """

    memory = load_memory()

    return memory.get(
        project,
        [],
    )


# ---------------------------------------------------------
# SIMPLE COMMAND-LINE TEST
# ---------------------------------------------------------

if __name__ == "__main__":

    import sys

    if len(sys.argv) < 2:

        print("Examples:")
        print()
        print(
            'PYTHONPATH=. uv run python3 '
            'memory/memory_store.py '
            'get codeatlas/ecommerce'
        )

        print()
        print(
            'PYTHONPATH=. uv run python3 '
            'memory/memory_store.py '
            'save codeatlas/ecommerce '
            'test_framework pytest'
        )

        sys.exit(1)

    command = sys.argv[1]

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    if command == "get":

        if len(sys.argv) < 3:
            print("Project required.")
            sys.exit(1)

        project = sys.argv[2]

        result = get_memories(
            project
        )

        print(
            json.dumps(
                result,
                indent=2,
            )
        )

    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    elif command == "save":

        if len(sys.argv) < 5:
            print(
                "Usage: save "
                "<project> <key> <value>"
            )
            sys.exit(1)

        project = sys.argv[2]
        key = sys.argv[3]
        value = sys.argv[4]

        result = save_memory(
            project=project,
            key=key,
            value=value,
        )

        print(
            json.dumps(
                result,
                indent=2,
            )
        )

    else:

        print(
            f"Unknown command: {command}"
        )