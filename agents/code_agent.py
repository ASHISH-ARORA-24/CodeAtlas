# CodeAtlas AI Agent.
#
# Accepts a project and a question. Decides which tools to call,
# executes them, and returns a grounded answer.
#
# Uses OpenAI function calling — the LLM decides which tool to use
# and with what arguments. Python executes the real tool and sends
# the result back to the LLM.
#
# Usage:
#   PYTHONPATH=. uv run python3 agents/code_agent.py <project> "<question>"
#   PYTHONPATH=. uv run python3 agents/code_agent.py codeatlas/ecommerce "what does StockManager.reserve_stock do?"

import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

from tools.code_search import search_code
from tools.graph_tool import get_dependencies
from tools.file_tool import read_file

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL   = "gpt-4o-mini"

client = OpenAI(api_key=OPENAI_API_KEY)


# ---------------------------------------------------------
# 1. TOOL SCHEMAS
#
# These JSON schemas are sent to OpenAI along with every request.
# OpenAI uses them to decide which tool to call and with what arguments.
#
# Important: project is NOT in any schema because the agent already
# knows the project. The LLM only decides parameters it cannot know
# in advance — query, symbol, repo, file_path.
# ---------------------------------------------------------

TOOLS = [
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
                        "description": "Function, method, or class name. Example: reserve_stock",
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
                "Use this when you need complete file content, not just a chunk."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Repository name. Example: inventory_service",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "File path relative to the repository root. Example: stock_manager.py",
                    },
                },
                "required": ["repo", "file_path"],
            },
        },
    },
]


# ---------------------------------------------------------
# 2. TOOL EXECUTION
#
# OpenAI decides WHAT tool to call and with WHAT arguments.
# This function actually runs the tool and returns the result.
#
# Project is injected here — the LLM never needs to choose it.
# ---------------------------------------------------------

def execute_tool(project: str, tool_name: str, arguments: dict):
    """
    Executes the tool requested by OpenAI and returns the result.

    project is injected silently — it never appears in the tool schema
    because it is already known for the entire agent session.
    """
    if tool_name == "search_code":
        return search_code(project=project, query=arguments["query"])

    if tool_name == "get_dependencies":
        return get_dependencies(project=project, symbol=arguments["symbol"])

    if tool_name == "read_file":
        return read_file(
            project=project,
            repo=arguments["repo"],
            file_path=arguments["file_path"],
        )

    raise ValueError(f"Unknown tool: {tool_name}")


# ---------------------------------------------------------
# 3. AGENT LOOP
#
# This is the core of how an agent works:
#
#   1. Send question + tool schemas to OpenAI
#   2. OpenAI returns either a tool call or a final answer
#   3. If tool call → execute tool → send result back to OpenAI
#   4. Repeat until OpenAI returns a final answer (no tool call)
#
# The full conversation history is kept in `messages` so OpenAI
# always sees everything that happened — question, tool calls,
# tool results — when making its next decision.
# ---------------------------------------------------------

def run_agent(project: str, question: str) -> str:
    """
    Runs the CodeAtlas agent for one question.

    Keeps the full conversation in messages so OpenAI has complete
    context at every step of the loop.
    """
    print()
    print("=" * 70)
    print("CODEATLAS AGENT  (OpenAI GPT-4o mini)")
    print("=" * 70)
    print(f"Project  : {project}")
    print(f"Question : {question}")

    # The system message tells OpenAI its role and constraints.
    # This is sent with every request — it is always in context.
    system_message = {
        "role": "system",
        "content": (
            "You are the CodeAtlas software engineering agent. "
            "You help developers understand source code stored inside "
            "a CodeAtlas project. "
            "You have tools for semantic code search, graph dependency "
            "analysis, and exact source-file reading. "
            "Use tools when needed. "
            "Do not assume facts about the codebase — ground your answer "
            "in tool results only. "
            "If you do not yet have enough information, call another tool."
        ),
    }

    # Conversation history — grows with every turn of the loop.
    # OpenAI needs the full history to understand context.
    messages = [
        system_message,
        {"role": "user", "content": question},
    ]

    # Agent loop — runs until OpenAI gives a final answer with no tool call.
    while True:

        # Send the full conversation to OpenAI.
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=TOOLS,
            # "auto" lets OpenAI decide whether to call a tool or answer directly.
            tool_choice="auto",
        )

        message = response.choices[0].message

        # Add OpenAI's response to conversation history so it is included
        # in the next request — this is how OpenAI knows what it already did.
        messages.append(message)

        # Check if OpenAI wants to call any tools.
        if not message.tool_calls:
            # No tool calls = OpenAI has enough information to answer.
            print()
            print("=" * 70)
            print("FINAL ANSWER")
            print("=" * 70)
            print(message.content)
            return message.content

        # OpenAI requested one or more tools — execute each one.
        for tool_call in message.tool_calls:
            print("===============================================")
            print("====> tool_call : ", tool_call)
            print("===============================================")
            tool_name  = tool_call.function.name
            arguments  = json.loads(tool_call.function.arguments)

            print()
            print("-" * 70)
            print(f"Agent selected tool : {tool_name}")
            print(f"Arguments           : {arguments}")
            print("-" * 70)

            try:
                tool_result = execute_tool(
                    project=project,
                    tool_name=tool_name,
                    arguments=arguments,
                )
            except Exception as exc:
                tool_result = {"error": str(exc)}

            # Display the tool result (truncated if very long).
            preview = json.dumps(tool_result, indent=2, default=str)
            print("Tool result:")
            if len(preview) > 3000:
                print(preview[:3000])
                print("\n... truncated ...")
            else:
                print(preview)

            # Send the tool result back to OpenAI.
            # OpenAI needs both the tool_call_id and the result to
            # understand which tool was called and what it returned.
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(tool_result, default=str),
            })

        # Loop again — OpenAI now sees the tool results and decides
        # whether to call another tool or give the final answer.


if __name__ == "__main__":

    if len(sys.argv) < 3:
        print("Usage: PYTHONPATH=. uv run python3 agents/code_agent.py <project> \"<question>\"")
        print()
        print("Example:")
        print("  PYTHONPATH=. uv run python3 agents/code_agent.py codeatlas/ecommerce \"what does StockManager.reserve_stock do?\"")
        sys.exit(1)

    PROJECT  = sys.argv[1]
    QUESTION = sys.argv[2]

    run_agent(project=PROJECT, question=QUESTION)
