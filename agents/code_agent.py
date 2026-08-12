# CodeAtlas AI Agent.
#
# Supports:
# - semantic code search
# - dependency analysis
# - exact file reading
# - source-code modification
# - test execution
# - long-term project memory retrieval
#
# Usage:
#   PYTHONPATH=. uv run python3 agents/code_agent.py <project> "<question>"

import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

from tools.code_search import search_code
from tools.graph_tool import get_dependencies
from tools.file_tool import read_file
from tools.write_file import write_file
from tools.run_tests import run_tests

from memory.memory_store import get_memories, save_memory


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"

client = OpenAI(api_key=OPENAI_API_KEY)


# ---------------------------------------------------------
# 1. TOOL SCHEMAS
# ---------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": (
                "Save stable and reusable project knowledge "
                "to long-term memory. "
                "Do not save temporary workflow information."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": (
                            "Short name for the memory. "
                            "Example: retry_library"
                        ),
                    },
                    "value": {
                        "type": "string",
                        "description": (
                            "Reusable information to remember. "
                            "Example: tenacity"
                        ),
                    },
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": (
                "Search source code semantically across all repositories "
                "inside the selected CodeAtlas project. "
                "Use this when you need to find where functionality, "
                "classes, methods, or functions are implemented."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural-language code search query.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dependencies",
            "description": (
                "Get callers, callees, class ownership and structural "
                "relationships for a code symbol using the Neo4j knowledge graph. "
                "Use this for dependency, impact, caller or callee questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": (
                            "Function, method, or class name. "
                            "Example: reserve_stock"
                        ),
                    }
                },
                "required": ["symbol"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read the exact source code of a file inside one repository "
                "belonging to the selected CodeAtlas project. "
                "Use this when you need complete file content."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": (
                            "Repository name. Example: inventory_service"
                        ),
                    },
                    "file_path": {
                        "type": "string",
                        "description": (
                            "File path relative to repository root. "
                            "Example: stock_manager.py"
                        ),
                    },
                },
                "required": ["repo", "file_path"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Overwrite an existing source file inside a repository "
                "belonging to the selected CodeAtlas project. "
                "Use this only when source code needs to be modified. "
                "The complete new file content must be provided."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": (
                            "Repository name. Example: inventory_service"
                        ),
                    },
                    "file_path": {
                        "type": "string",
                        "description": (
                            "Existing file path relative to repository root."
                        ),
                    },
                    "content": {
                        "type": "string",
                        "description": (
                            "Complete replacement content for the file."
                        ),
                    },
                },
                "required": [
                    "repo",
                    "file_path",
                    "content",
                ],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": (
                "Run pytest inside a repository and return whether tests "
                "passed or failed together with stdout and stderr. "
                "Use this after modifying code to validate the change."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": (
                            "Repository whose tests should be executed."
                        ),
                    },
                    "test_command": {
                        "type": "string",
                        "description": (
                            "Pytest command to execute. "
                            "Example: pytest -q"
                        ),
                    },
                },
                "required": ["repo"],
            },
        },
    },
]


# ---------------------------------------------------------
# 2. TOOL EXECUTION
# ---------------------------------------------------------

def execute_tool(
    project: str,
    tool_name: str,
    arguments: dict,
):

    if tool_name == "search_code":
        return search_code(
            project=project,
            query=arguments["query"],
        )

    if tool_name == "get_dependencies":
        return get_dependencies(
            project=project,
            symbol=arguments["symbol"],
        )

    if tool_name == "read_file":
        return read_file(
            project=project,
            repo=arguments["repo"],
            file_path=arguments["file_path"],
        )

    if tool_name == "write_file":
        return write_file(
            project=project,
            repo=arguments["repo"],
            file_path=arguments["file_path"],
            content=arguments["content"],
        )

    if tool_name == "run_tests":
        return run_tests(
            project=project,
            repo=arguments["repo"],
            test_command=arguments.get(
                "test_command",
                "pytest -q",
            ),
        )
    if tool_name == "save_memory":
        return save_memory(
            project=project,
            key=arguments["key"],
            value=arguments["value"],
        )

    raise ValueError(
        f"Unknown tool: {tool_name}"
    )


# ---------------------------------------------------------
# 3. AGENT LOOP
# ---------------------------------------------------------

def run_agent(
    project: str,
    question: str,
    verbose: bool = False,
) -> str:

    if verbose:
        print()
        print("=" * 70)
        print("CODEATLAS CODING AGENT")
        print("=" * 70)
        print(f"Project  : {project}")
        print(f"Question : {question}")

    # -----------------------------------------------------
    # 4. LOAD LONG-TERM MEMORY
    #
    # Memory survives across executions.
    # State does not.
    # Messages/context are only for this run_agent().
    # -----------------------------------------------------

    memories = get_memories(project)

    memory_text = "\n".join(
        f"- {item['key']}: {item['value']}"
        for item in memories
    )

    if not memory_text:
        memory_text = "No stored project memory."

    if verbose:
        print()
        print("LONG-TERM MEMORY")
        print(memory_text)

    # -----------------------------------------------------
    # SYSTEM MESSAGE
    # -----------------------------------------------------

    system_message = {
        "role": "system",
        "content": (
            "You are the CodeAtlas software engineering agent. "

            "You operate inside one CodeAtlas project and can understand "
            "and modify source code using the tools available to you. "

            "You have tools for semantic code search, dependency analysis, "
            "exact source-file reading, source-file modification, "
            "and test execution. "

            "Ground all decisions in tool results. "
            "Do not assume facts about the codebase. "

            "Before modifying a file, inspect the relevant source code. "

            "When implementing a development task, investigate the relevant "
            "code and dependencies before making changes. "

            "Use write_file only when the task requires a source-code change. "

            "After modifying code, run the relevant tests using run_tests. "

            "If tests fail, analyze the test output, inspect relevant files "
            "if necessary, correct the implementation, and run tests again. "

            "Continue the reason-act-observe loop until the tests pass "
            "or the problem cannot be safely resolved. "

            "Do not claim that an implementation succeeded unless relevant "
            "tests pass. "

            "Do not modify unrelated files. "

            "\n\nRelevant long-term project memory:\n"
            f"{memory_text}\n\n"

            "Treat long-term memory as useful prior knowledge, not guaranteed truth. "
            "If current source code or tool results contradict memory, trust the "
            "current source code and tool results."
            "When you discover stable and reusable project knowledge that may help "
            "future tasks, you may save it using save_memory. "

            "Examples of useful memory include testing frameworks, naming conventions, "
            "logging conventions, retry libraries, architectural patterns, and standard "
            "repository practices. "

            "Do not save temporary workflow state, current step numbers, transient errors, "
            "temporary branch names, one-off test failures, or speculative conclusions. "

            "Only save memory when the information is supported by current tool results. "
        ),
    }

    # -----------------------------------------------------
    # Context for THIS agent execution
    # -----------------------------------------------------

    messages = [
        system_message,
        {
            "role": "user",
            "content": question,
        },
    ]

    # -----------------------------------------------------
    # AGENT LOOP
    # -----------------------------------------------------

    while True:

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        message = response.choices[0].message

        # Remember this response for THIS run.
        messages.append(message)

        # No tool call = agent finished.
        if not message.tool_calls:

            if verbose:
                print()
                print("=" * 70)
                print("FINAL ANSWER")
                print("=" * 70)
                print(message.content)

            return message.content

        # Execute requested tools.
        for tool_call in message.tool_calls:

            tool_name = tool_call.function.name

            arguments = json.loads(
                tool_call.function.arguments
            )

            if verbose:
                print()
                print("-" * 70)
                print(
                    f"Agent selected tool : "
                    f"{tool_name}"
                )
                print(
                    f"Arguments           : "
                    f"{arguments}"
                )
                print("-" * 70)

            try:

                tool_result = execute_tool(
                    project=project,
                    tool_name=tool_name,
                    arguments=arguments,
                )

            except Exception as exc:

                tool_result = {
                    "error": str(exc)
                }

            if verbose:

                preview = json.dumps(
                    tool_result,
                    indent=2,
                    default=str,
                )

                print("Tool result:")

                if len(preview) > 3000:
                    print(
                        preview[:3000]
                    )
                    print(
                        "\n... truncated ..."
                    )
                else:
                    print(preview)

            # Tool result becomes observation.
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(
                        tool_result,
                        default=str,
                    ),
                }
            )


if __name__ == "__main__":

    if len(sys.argv) < 3:

        print(
            'Usage: PYTHONPATH=. uv run python3 '
            'agents/code_agent.py '
            '<project> "<question>"'
        )

        print()
        print("Example:")

        print(
            '  PYTHONPATH=. uv run python3 '
            'agents/code_agent.py '
            'codeatlas/ecommerce '
            '"What test framework does this project use?"'
        )

        sys.exit(1)

    PROJECT = sys.argv[1]
    QUESTION = sys.argv[2]

    run_agent(
        project=PROJECT,
        question=QUESTION,
        verbose=True,
    )