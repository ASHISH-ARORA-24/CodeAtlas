# CodeAtlas Coding Workflow.
#
# Outer loop: Planner → State → Execute each step → Synthesize
# Inner loop: Each step runs the code_agent (reason → act → observe)
#
# Usage:
#   PYTHONPATH=. uv run python3 agents/executor.py <project> "<task>"

import sys

from agents.code_agent import run_agent
from agents.planner import create_plan
from agents.state import create_initial_state
from agents.synthesizer import synthesize_result


def execute_current_step(state: dict) -> dict:
    """
    Executes the current planning step using the CodeAtlas coding agent.
    The agent decides which tools to call — search, read, write, test.
    """
    current_step_id = state["current_step"]
    current_step = next(s for s in state["plan"]["steps"] if s["id"] == current_step_id)

    project    = state["project"]
    task       = state["task"]
    step_action = current_step["action"]

    print()
    print(f"STEP {current_step_id}: {step_action}")

    agent_request = f"""
Original task:
{task}

Current planning step:
{step_action}

Execute this planning step using the available CodeAtlas tools.
You may search code, analyze dependencies, read source files, modify source files, and run tests.

If this step requires a code change:
1. Inspect the relevant source code first.
2. Make the required change using write_file.
3. Run the relevant tests using run_tests.
4. If tests fail, analyze the failure, fix the implementation, and run tests again.
5. Continue until tests pass or the issue cannot be safely resolved.

Do not modify unrelated files.
Do not claim that a code change succeeded unless relevant tests pass.
Return the result of this planning step.
"""

    result = run_agent(project=project, question=agent_request, verbose=False)

    print("Completed.")

    return {"step_id": current_step_id, "action": step_action, "result": result}


def execute_plan(state: dict) -> dict:
    """
    Executes every step in the plan sequentially.
    Updates state after each step and advances to the next.
    """
    total_steps = len(state["plan"]["steps"])
    state["status"] = "in_progress"

    while state["current_step"] <= total_steps:
        step_result = execute_current_step(state)
        state["step_results"].append(step_result)
        state["current_step"] += 1

    state["status"] = "completed"
    return state


def run_workflow(project: str, task: str) -> str:
    """
    Runs the complete CodeAtlas coding workflow end-to-end.
    Plan → State → Execute steps → Synthesize final result.
    """
    print()
    print("=" * 70)
    print("CODEATLAS PLANNING WORKFLOW")
    print("=" * 70)
    print(f"Project : {project}")
    print(f"Task    : {task}")

    plan = create_plan(task)

    print()
    print("PLAN")
    for step in plan["steps"]:
        print(f"  {step['id']}. {step['action']}")

    state = create_initial_state(project=project, task=task, plan=plan)
    final_state = execute_plan(state)
    final_answer = synthesize_result(final_state)

    print()
    print("=" * 70)
    print("FINAL RECOMMENDATION")
    print("=" * 70)
    print(final_answer)

    return final_answer


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: PYTHONPATH=. uv run python3 agents/executor.py <project> \"<task>\"")
        sys.exit(1)

    run_workflow(project=sys.argv[1], task=sys.argv[2])
