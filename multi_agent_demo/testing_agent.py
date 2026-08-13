import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from tools.code_search import search_code
from tools.file_tool import read_file


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
]


TESTING_SYSTEM_PROMPT = """
You are the Testing Agent in a multi-agent software engineering system.

Your responsibility is to evaluate the proposed code change and determine
which tests are required.

You do NOT modify code.

Use the available tools to inspect relevant tests or source code when needed.

Do not invent test files or behavior.

Return JSON only in this format:

{
  "agent": "tester",
  "status": "tests_passed | tests_failed",
  "result": {
    "tests_considered": [],
    "coverage": "...",
    "assessment": "..."
  },
  "request": null or "description of what needs to be fixed"
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

    raise ValueError(
        f"Unknown tool: {tool_name}"
    )


def run_testing_agent(
    project: str,
    task: str,
    coding_result: dict,
) -> dict:

    messages = [
        {
            "role": "system",
            "content": TESTING_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task": task,
                    "coding_result": coding_result,
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

            # Tool errors should not crash the workflow — the agent gets the
            # error message and can decide how to proceed (e.g. try another path).
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

    CODING_RESULT = {
        "file": "inventory_service/stock_manager.py",
        "symbol": "_validate_quantity",
        "proposed_change": (
            "Reject quantities less than 1 before "
            "any stock state is modified."
        ),
    }

    result = run_testing_agent(
        project=PROJECT,
        task=TASK,
        coding_result=CODING_RESULT,
    )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )