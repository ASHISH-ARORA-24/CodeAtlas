import json
import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"

client = OpenAI(
    api_key=OPENAI_API_KEY
)


JUDGE_SYSTEM_PROMPT = """
You are the evaluation judge for CodeAtlas.

Your job is to evaluate an AI coding agent's final answer.

You will receive:

1. The original task.
2. The expected outcome.
3. The execution trace.
4. The final answer produced by the agent.

Evaluate only using the supplied evidence.

Score the following from 0 to 5:

correctness:
Does the answer correctly address the task?

groundedness:
Are the claims supported by the execution trace,
retrieved files, tool calls, and test results?

task_completion:
Did the agent actually complete what the task required?

hallucination:
5 means no hallucinations.
0 means major unsupported or invented claims.

clarity:
Is the final answer clear and useful?

Return JSON only in this structure:

{
  "correctness": 0,
  "groundedness": 0,
  "task_completion": 0,
  "hallucination": 0,
  "clarity": 0,
  "overall_score": 0,
  "reason": "short explanation"
}
"""


def judge_agent_result(
    test_case: dict,
    trace: dict,
) -> dict:
    """
    Use another LLM to evaluate the quality of
    the CodeAtlas agent result.
    """

    evaluation_input = {
        "task": test_case["task"],
        "expected_outcome": test_case.get(
            "expected_outcome"
        ),
        "expected_files": test_case.get(
            "expected_files",
            [],
        ),
        "expected_symbols": test_case.get(
            "expected_symbols",
            [],
        ),
        "execution_trace": {
            "tools_called": trace.get(
                "tools_called",
                [],
            ),
            "files_read": trace.get(
                "files_read",
                [],
            ),
            "files_written": trace.get(
                "files_written",
                [],
            ),
            "test_results": trace.get(
                "test_results",
                [],
            ),
        },
        "final_answer": trace.get(
            "final_answer"
        ),
    }

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": JUDGE_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": json.dumps(
                    evaluation_input,
                    indent=2,
                ),
            },
        ],
        response_format={
            "type": "json_object"
        },
    )

    result_text = (
        response
        .choices[0]
        .message
        .content
    )

    return json.loads(
        result_text
    )