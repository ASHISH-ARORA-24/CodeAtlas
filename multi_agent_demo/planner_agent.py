# Planner Agent for the multi-agent workflow.
#
# The planner is the strategic brain of the system. It has two jobs:
#   1. Decide WHICH specialist agents are needed for this task
#   2. Decide in WHAT ORDER they should run
#
# The planner does NOT know how any agent works internally — it only
# sees the agent registry (name + one-line description) provided by
# the orchestrator. This keeps the planner ignorant of implementation
# details, exactly like real production systems (LangGraph, Autogen).
#
# The planner does NOT modify code and does NOT call other agents
# directly. Only the orchestrator invokes agents.

import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL   = "gpt-4o-mini"

client = OpenAI(api_key=OPENAI_API_KEY)


PLANNER_SYSTEM_PROMPT = """
You are the Planner Agent in a multi-agent software engineering system.

Your job is to:
1. Understand the task.
2. Decide which specialist agents are needed and in what order.
3. If you lack technical information about the codebase, request it.

You will receive:
- the user's task
- a registry of available agents (name + short description)
- optionally: prior findings from another agent (e.g. analyst)

You do NOT know how any agent works internally. You only see their names
and one-line descriptions. Choose from the registry only.

You do NOT modify code and do NOT call other agents directly.

If you need technical information about the codebase before you can plan
sensibly, return status "need_information" with a clear request. The
orchestrator will route your request to an appropriate agent and
re-call you with the findings.

If you have enough context to plan, return status "plan_ready" with:
- workflow: ordered list of agent names from the registry
- reason:   short explanation for the chosen sequence
- steps:    human-readable list of what will happen

You MAY skip agents that are not needed for this task.
Examples:
  - Trivial code cleanup:      ["coder"]
  - Documentation-only change: ["coder", "reviewer"]
  - Standard feature change:   ["coder", "tester", "reviewer"]
  - Complex change:            ["coder", "tester", "reviewer"] with prior analyst findings

Do NOT include "planner" in the workflow — you are the planner.

Return JSON only in this format:
{
  "agent": "planner",
  "status": "need_information | plan_ready",
  "result": null or {
    "workflow": ["coder", "tester", "reviewer"],
    "reason":   "short explanation",
    "steps":    ["step 1", "step 2"]
  },
  "request": null or "description of information you need"
}
"""


def run_planner_agent(
    task: str,
    available_agents: dict | None = None,
    prior_findings: dict | None = None,
) -> dict:
    """
    Runs the planner.

    Args:
        task:             the user's task description
        available_agents: registry the planner picks from — {name: description}
        prior_findings:   optional prior context (e.g. analyst output on re-plan)

    Returns:
        Planner decision — either a workflow or a need_information request.
    """
    user_message = {
        "task": task,
        "available_agents": available_agents or {},
    }
    if prior_findings:
        user_message["prior_findings"] = prior_findings

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user",   "content": json.dumps(user_message, indent=2)},
        ],
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)


if __name__ == "__main__":
    # Quick sanity check: give the planner a task and see what it plans.
    REGISTRY = {
        "analyst":  "Investigates source code — finds files, symbols, dependencies, tests.",
        "coder":    "Designs the proposed code change based on the plan.",
        "tester":   "Evaluates testing requirements and coverage.",
        "reviewer": "Independently reviews the proposed change and testing assessment.",
    }

    result = run_planner_agent(
        task="Add validation for negative stock.",
        available_agents=REGISTRY,
    )
    print(json.dumps(result, indent=2))
