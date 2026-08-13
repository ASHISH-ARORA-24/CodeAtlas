# Synthesizer for CodeAtlas.
# Takes the completed workflow state and produces a final engineering recommendation.

import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL   = "gpt-4o-mini"

client = OpenAI(api_key=OPENAI_API_KEY)


def synthesize_result(state: dict) -> str:
    """Creates one final conclusion from the complete workflow state."""
    task         = state["task"]
    plan         = state["plan"]
    step_results = state["step_results"]

    prompt = f"""
Original task:
{task}

Plan:
{json.dumps(plan, indent=2)}

Investigation results:
{json.dumps(step_results, indent=2)}

Using ONLY the investigation results above, produce a final engineering recommendation.

Explain:
1. What was discovered.
2. Which files/components are relevant.
3. What change is recommended.
4. What dependencies or impact should be considered.
5. Any uncertainty or missing information.

Do not claim that code was modified. Do not invent facts that were not discovered.
"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are the final analysis component of CodeAtlas. "
                    "Synthesize workflow findings into a concise, grounded software engineering recommendation."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )

    return response.choices[0].message.content
