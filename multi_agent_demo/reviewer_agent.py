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


REVIEWER_SYSTEM_PROMPT = """
You are the Reviewer Agent in a multi-agent software engineering system.

Your responsibility is to independently review the proposed implementation
and testing assessment.

You do NOT modify code.

Use the available read-only tools when needed to verify claims.

Review:
- whether the proposed change addresses the task
- whether the correct files/symbols were selected
- whether the change is appropriately scoped
- whether dependencies or side effects were missed
- whether the testing assessment is sufficient
- whether any claim appears unsupported

Return JSON only in this format:

{
  "agent": "reviewer",
  "status": "approved | rejected",
  "result": {
    "assessment": "...",
    "risks": [],
    "missing_items": []
  },
  "request": null or "description of what must be corrected"
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


def run_reviewer_agent(
    project: str,
    task: str,
    coding_result: dict,
    testing_result: dict,
) -> dict:

    messages = [
        {
            "role": "system",
            "content": REVIEWER_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task": task,
                    "coding_result": coding_result,
                    "testing_result": testing_result,
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

    CODING_RESULT = {
        "file": "inventory_service/stock_manager.py",
        "symbol": "_validate_quantity",
        "current_behavior": (
            "Quantity validation is handled centrally."
        ),
        "proposed_change": (
            "Ensure quantities less than 1 raise ValueError "
            "before stock state changes."
        ),
    }

    TESTING_RESULT = {
        "tests_considered": [
            "negative quantity",
            "zero quantity",
            "positive quantity",
        ],
        "coverage": (
            "Validation boundary cases are covered."
        ),
        "assessment": (
            "The proposed change appears consistent with expected behavior."
        ),
    }

    result = run_reviewer_agent(
        project=PROJECT,
        task=TASK,
        coding_result=CODING_RESULT,
        testing_result=TESTING_RESULT,
    )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )