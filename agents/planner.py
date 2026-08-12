import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI
from agents.state import create_initial_state

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"

client = OpenAI(api_key=OPENAI_API_KEY)


PLANNER_SYSTEM_PROMPT = """
You are the planning component of CodeAtlas.

Your job is to create a software-development investigation plan
before any code is modified.

The plan should:
1. Understand the requirement.
2. Investigate relevant code.
3. Analyze dependencies and impact.
4. Identify affected files/components.
5. Define implementation steps.

Do not modify code.
Do not invent file names or implementation details before investigation.

Return JSON only in this structure:

{
  "goal": "short description of the task",
  "steps": [
    {
      "id": 1,
      "action": "what should be done"
    }
  ]
}
"""


def create_plan(task: str) -> dict:

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": PLANNER_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": task,
            },
        ],
        response_format={"type": "json_object"},
    )

    plan_text = response.choices[0].message.content

    return json.loads(plan_text)


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print(
            'Usage: PYTHONPATH=. uv run python3 '
            'agents/planner.py "<task>"'
        )
        sys.exit(1)

    TASK = sys.argv[1]

    plan = create_plan(TASK)

    state = create_initial_state(
        project="codeatlas/ecommerce",
        task=TASK,
        plan=plan,
    )

    print(json.dumps(state, indent=2))