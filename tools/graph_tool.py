"""
Neo4j dependency tool for the CodeAtlas agent.

This tool looks up structural relationships for a code symbol
across all repositories belonging to a CodeAtlas project.
"""

import os
import sys

from dotenv import load_dotenv
from neo4j import GraphDatabase

from qa.ask import find_repos_in_project


load_dotenv()


NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")


def get_dependencies(project: str, symbol: str) -> list[dict]:
    """
    Find structural relationships for a symbol across all repositories
    belonging to a CodeAtlas project.

    Args:
        project:
            CodeAtlas project identifier.
            Example: "codeatlas/ecommerce"

        symbol:
            Function, method, or class name.
            Example: "reserve_stock"

    Returns:
        A list of matching symbols and their graph relationships.
    """

    repos = find_repos_in_project(project)

    if not repos:
        return []

    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
    )

    matches = []

    try:
        with driver.session() as session:

            # Find all matching symbols across repositories in this project.
            result = session.run(
                """
                MATCH (n)
                WHERE n.name = $symbol
                  AND n.repo IN $repos
                RETURN
                    labels(n) AS labels,
                    n.name AS name,
                    n.file AS file,
                    n.repo AS repo
                """,
                {
                    "symbol": symbol,
                    "repos": repos,
                },
            )

            symbols = [record.data() for record in result]

            for item in symbols:

                name = item["name"]
                file_name = item["file"]
                repo = item["repo"]
                labels = item["labels"]

                # ---------------------------------------------------------
                # Find functions/methods called BY this symbol
                # ---------------------------------------------------------
                outgoing_result = session.run(
                    """
                    MATCH (caller {
                        name: $name,
                        file: $file,
                        repo: $repo
                    })-[:CALLS]->(callee)

                    RETURN DISTINCT
                        callee.name AS name,
                        callee.file AS file,
                        callee.repo AS repo
                    """,
                    {
                        "name": name,
                        "file": file_name,
                        "repo": repo,
                    },
                )

                calls = [
                    record.data()
                    for record in outgoing_result
                ]

                # ---------------------------------------------------------
                # Find functions/methods that call THIS symbol
                # ---------------------------------------------------------
                incoming_result = session.run(
                    """
                    MATCH (caller)-[:CALLS]->(callee {
                        name: $name,
                        file: $file,
                        repo: $repo
                    })

                    RETURN DISTINCT
                        caller.name AS name,
                        caller.file AS file,
                        caller.repo AS repo
                    """,
                    {
                        "name": name,
                        "file": file_name,
                        "repo": repo,
                    },
                )

                called_by = [
                    record.data()
                    for record in incoming_result
                ]

                # ---------------------------------------------------------
                # If symbol is a method, find its owning class
                # ---------------------------------------------------------
                class_result = session.run(
                    """
                    MATCH (c:Class)-[:HAS_METHOD]->(m {
                        name: $name,
                        file: $file,
                        repo: $repo
                    })

                    RETURN DISTINCT
                        c.name AS class_name,
                        c.file AS file,
                        c.repo AS repo
                    """,
                    {
                        "name": name,
                        "file": file_name,
                        "repo": repo,
                    },
                )

                classes = [
                    record.data()
                    for record in class_result
                ]

                matches.append(
                    {
                        "project": project,
                        "repo": repo,
                        "file": file_name,
                        "symbol": name,
                        "labels": labels,
                        "calls": calls,
                        "called_by": called_by,
                        "classes": classes,
                    }
                )

    finally:
        driver.close()

    return matches


if __name__ == "__main__":

    if len(sys.argv) < 3:
        print(
            'Usage: PYTHONPATH=. uv run python3 '
            'tools/graph_tool.py <project> "<symbol>"'
        )

        print("\nExample:")
        print(
            '  PYTHONPATH=. uv run python3 '
            'tools/graph_tool.py codeatlas/ecommerce "reserve_stock"'
        )

        sys.exit(1)

    project = sys.argv[1]
    symbol = sys.argv[2]

    results = get_dependencies(project, symbol)

    if not results:
        print(f"\nNo graph information found for: {symbol}")
        sys.exit(0)

    print(f"\nFound {len(results)} matching symbol(s)\n")

    for result in results:

        print("=" * 60)

        print(f"Project : {result['project']}")
        print(f"Repo    : {result['repo']}")
        print(f"File    : {result['file']}")
        print(f"Symbol  : {result['symbol']}")
        print(f"Type    : {', '.join(result['labels'])}")

        print("\nCalls:")

        if result["calls"]:
            for dependency in result["calls"]:
                print(
                    f"  -> {dependency['name']} "
                    f"({dependency['file']}, "
                    f"repo: {dependency['repo']})"
                )
        else:
            print("  None")

        print("\nCalled by:")

        if result["called_by"]:
            for caller in result["called_by"]:
                print(
                    f"  <- {caller['name']} "
                    f"({caller['file']}, "
                    f"repo: {caller['repo']})"
                )
        else:
            print("  None")

        print("\nClass:")

        if result["classes"]:
            for class_info in result["classes"]:
                print(
                    f"  {class_info['class_name']} "
                    f"({class_info['file']})"
                )
        else:
            print("  None")

        print()