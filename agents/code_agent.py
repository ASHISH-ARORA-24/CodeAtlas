import json
import os
import sys

from dotenv import load_dotenv
from google import genai
from google.genai import types

from tools.code_search import search_code
from tools.graph_tool import get_dependencies
from tools.file_tool import read_file


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-flash-latest"

client = genai.Client(api_key=GEMINI_API_KEY)


# ---------------------------------------------------------
# 1. TOOL DECLARATIONS
#
# These descriptions are sent to Gemini.
# Gemini uses them to decide which tool it needs.
# ---------------------------------------------------------

search_code_declaration = types.FunctionDeclaration(
    name="search_code",
    description=(
        "Search source code semantically across all repositories "
        "inside the selected CodeAtlas project. "
        "Use this when you need to find where functionality, "
        "classes, methods, or functions are implemented."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural-language code search query."
            }
        },
        "required": ["query"],
    },
)


get_dependencies_declaration = types.FunctionDeclaration(
    name="get_dependencies",
    description=(
        "Get callers, callees, class ownership and structural "
        "relationships for a code symbol using Neo4j. "
        "Use this for dependency, impact, caller or callee questions."
    ),
    parameters={
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": (
                    "Function, method, or class name. "
                    "Example: reserve_stock"
                )
            }
        },
        "required": ["symbol"],
    },
)


read_file_declaration = types.FunctionDeclaration(
    name="read_file",
    description=(
        "Read the exact source code of a file inside one repository "
        "belonging to the selected CodeAtlas project. "
        "Use this when exact implementation details are needed."
    ),
    parameters={
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "description": "Repository name."
            },
            "file_path": {
                "type": "string",
                "description": (
                    "Path to the file relative to the repository."
                )
            },
        },
        "required": ["repo", "file_path"],
    },
)


TOOLS = [
    types.Tool(
        function_declarations=[
            search_code_declaration,
            get_dependencies_declaration,
            read_file_declaration,
        ]
    )
]


# ---------------------------------------------------------
# 2. TOOL EXECUTION
#
# Gemini decides WHAT tool it wants.
# Python executes the real tool.
#
# Important:
# Gemini does NOT choose the project.
# We inject the project ourselves.
# ---------------------------------------------------------

def execute_tool(project: str, tool_name: str, arguments: dict):

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

    raise ValueError(f"Unknown tool: {tool_name}")


# ---------------------------------------------------------
# 3. AGENT
# ---------------------------------------------------------

def run_agent(project: str, question: str):

    print()
    print("=" * 70)
    print("CODEATLAS GEMINI AGENT")
    print("=" * 70)
    print(f"Project  : {project}")
    print(f"Question : {question}")

    system_instruction = (
        "You are the CodeAtlas software engineering agent. "
        "You help developers understand source code stored inside "
        "a CodeAtlas project. "

        "You have tools for semantic code search, graph dependency "
        "analysis and exact source-file reading. "

        "Use tools when needed. "
        "Do not assume facts about the codebase. "
        "Ground your answer in tool results. "

        "When multiple symbols have the same name, use repository, "
        "file and class context to distinguish them. "

        "If you do not yet have enough information, call another tool."
    )

    # Conversation history.
    #
    # We manually keep the complete conversation because we want to
    # SEE and understand the agent loop.
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=question)
            ],
        )
    ]

    # -----------------------------------------------------
    # 4. AGENT LOOP
    # -----------------------------------------------------

    while True:

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=TOOLS,
            ),
        )

        candidate = response.candidates[0]
        model_content = candidate.content

        # Keep Gemini's response in conversation history.
        contents.append(model_content)

        # Find function calls requested by Gemini.
        function_calls = []

        for part in model_content.parts:
            if part.function_call:
                function_calls.append(part.function_call)

        # -------------------------------------------------
        # No function calls = Gemini has finished.
        # -------------------------------------------------

        if not function_calls:

            print()
            print("=" * 70)
            print("FINAL ANSWER")
            print("=" * 70)
            print(response.text)

            return response.text

        # -------------------------------------------------
        # Gemini requested one or more tools.
        # -------------------------------------------------

        function_response_parts = []

        for function_call in function_calls:

            tool_name = function_call.name

            arguments = dict(
                function_call.args or {}
            )

            print()
            print("-" * 70)
            print(f"Agent selected tool: {tool_name}")
            print(f"Arguments: {arguments}")
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

            print("Tool result:")

            preview = json.dumps(
                tool_result,
                indent=2,
                default=str,
            )

            if len(preview) > 4000:
                print(preview[:4000])
                print("\n... console output truncated ...")
            else:
                print(preview)

            # -------------------------------------------------
            # Send tool result BACK to Gemini.
            # -------------------------------------------------

            function_response_parts.append(
                types.Part.from_function_response(
                    name=tool_name,
                    response={
                        "result": tool_result
                    },
                )
            )

        # Add all tool results to conversation.
        contents.append(
            types.Content(
                role="user",
                parts=function_response_parts,
            )
        )

        # Loop again.
        #
        # Gemini now receives:
        #
        # question
        #     +
        # previous tool request
        #     +
        # actual tool result
        #
        # and decides what to do next.


if __name__ == "__main__":

    if len(sys.argv) < 3:

        print(
            'Usage: PYTHONPATH=. uv run python3 '
            'agents/code_agent.py <project> "<question>"'
        )

        print()

        print(
            'Example:\n'
            '  PYTHONPATH=. uv run python3 '
            'agents/code_agent.py '
            'codeatlas/ecommerce '
            '"what does StockManager.reserve_stock do?"'
        )

        sys.exit(1)

    PROJECT = sys.argv[1]
    QUESTION = sys.argv[2]

    run_agent(
        project=PROJECT,
        question=QUESTION,
    )