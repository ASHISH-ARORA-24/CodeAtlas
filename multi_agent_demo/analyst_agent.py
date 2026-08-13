import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from tools.code_search import search_code
from tools.file_tool import read_file
from tools.graph_tool import get_dependencies


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"

client = OpenAI(
    api_key=OPENAI_API_KEY
)


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": (
                "Search source code semantically across repositories "
                "inside the selected CodeAtlas project."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string"
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read the exact source code of a file inside a repository."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string"
                    },
                    "file_path": {
                        "type": "string"
                    },
                },
                "required": [
                    "repo",
                    "file_path",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dependencies",
            "description": (
                "Find callers, callees and structural dependencies "
                "for a code symbol."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string"
                    }
                },
                "required": ["symbol"],
            },
        },
    },
]


ANALYST_SYSTEM_PROMPT = """
You are the Analyst Agent in a multi-agent software engineering system.

Your responsibility is to investigate the codebase and provide grounded
technical findings.

You do NOT modify code.

Use the available tools when needed.

Investigate:
- relevant files
- relevant classes/functions/methods
- dependencies and callers
- likely impact
- relevant tests

Do not invent files or code.

When you have enough information, return JSON only:

{
  "agent": "analyst",
  "status": "analysis_ready",
  "result": {
    "relevant_files": [],
    "relevant_symbols": [],
    "dependencies": [],
    "tests_to_consider": [],
    "summary": "..."
  },
  "request": null
}
"""


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

    if tool_name == "read_file":

        return read_file(
            project=project,
            repo=arguments["repo"],
            file_path=arguments["file_path"],
        )

    if tool_name == "get_dependencies":

        return get_dependencies(
            project=project,
            symbol=arguments["symbol"],
        )

    raise ValueError(
        f"Unknown tool: {tool_name}"
    )


def run_analyst_agent(
    project: str,
    task: str,
    request: str,
) -> dict:

    messages = [
        {
            "role": "system",
            "content": ANALYST_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task": task,
                    "analysis_request": request,
                },
                indent=2,
            ),
        },
    ]

    while True:

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            response_format={
                "type": "json_object"
            },
        )

        message = response.choices[0].message

        messages.append(
            message
        )

        if not message.tool_calls:

            return json.loads(
                message.content
            )

        for tool_call in message.tool_calls:

            tool_name = (
                tool_call.function.name
            )

            arguments = json.loads(
                tool_call.function.arguments
            )

            # Tool errors should not crash the workflow — surface them to the LLM.
            try:
                tool_result = execute_tool(
                    project=project,
                    tool_name=tool_name,
                    arguments=arguments,
                )
            except Exception as exc:
                tool_result = {"error": str(exc)}

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

    PROJECT = "codeatlas/ecommerce"

    TASK = "Add validation for negative stock."

    REQUEST = (
        "Investigate the relevant code, files, "
        "dependencies, and tests for this task."
    )

    result = run_analyst_agent(
        project=PROJECT,
        task=TASK,
        request=REQUEST,
    )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )