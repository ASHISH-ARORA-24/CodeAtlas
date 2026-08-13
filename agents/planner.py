# Planner for CodeAtlas.
# Converts a development task into a structured step-by-step plan using OpenAI.
#
# Usage:
#   PYTHONPATH=. uv run python3 agents/planner.py <project> "<task>"

import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI
from agents.state import create_initial_state

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL   = "gpt-4o-mini"

client = OpenAI(api_key=OPENAI_API_KEY)

PLANNER_SYSTEM_PROMPT = """
You are the planning component of CodeAtlas.

Your job is to create a structured software-development plan for completing the user's task.

The plan should normally cover:
1. Understand the requirement.
2. Investigate the relevant code.
3. Analyze dependencies and impact.
4. Identify affected files/components.
5. Implement the required code change.
6. Run relevant tests.
7. If tests fail, analyze the failure, fix the implementation, and run the tests again.

Important rules:
- Create task-specific steps.
- Do not invent file names or implementation details before investigation.
- Investigation should happen before modification.
- Testing must happen after code modification.
- Do not include unrelated work.

Return JSON only in this structure:
{
  "goal": "short description of the task",
  "steps": [
    {"id": 1, "action": "what should be done"}
  ]
}
"""


def create_plan(task: str) -> dict:
    """Asks OpenAI to convert a development task into a structured execution plan."""
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user",   "content": task},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: PYTHONPATH=. uv run python3 agents/planner.py <project> \"<task>\"")
        sys.exit(1)

    plan  = create_plan(sys.argv[2])
    state = create_initial_state(project=sys.argv[1], task=sys.argv[2], plan=plan)
    print(json.dumps(state, indent=2))
