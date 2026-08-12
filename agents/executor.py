import sys

from agents.code_agent import run_agent
from agents.planner import create_plan
from agents.state import create_initial_state
from agents.synthesizer import synthesize_result


def execute_current_step(state: dict) -> dict:
    """
    Execute the current planning step using the CodeAtlas coding agent.

    Flow:
        state
          ↓
        current_step
          ↓
        code_agent
          ↓
        investigate / modify / test
          ↓
        step result
    """

    current_step_id = state["current_step"]
    steps = state["plan"]["steps"]

    current_step = next(
        step
        for step in steps
        if step["id"] == current_step_id
    )

    project = state["project"]
    task = state["task"]
    step_action = current_step["action"]

    print()
    print(f"STEP {current_step_id}: {step_action}")

    agent_request = f"""
Original task:
{task}

Current planning step:
{step_action}

Execute this planning step using the available CodeAtlas tools.

You may:
- search code
- analyze dependencies
- read source files
- modify source files when required
- run tests

If this step requires a code change:
1. Inspect the relevant source code first.
2. Make the required change using write_file.
3. Run the relevant tests using run_tests.
4. If tests fail, analyze the failure.
5. Fix the implementation.
6. Run the tests again.
7. Continue until tests pass or the issue cannot be safely resolved.

Do not modify unrelated files.

Do not claim that a code change succeeded unless relevant tests pass.

Return the result of this planning step.
"""

    result = run_agent(
        project=project,
        question=agent_request,
        verbose=False,
    )

    print("Completed.")

    return {
        "step_id": current_step_id,
        "action": step_action,
        "result": result,
    }


def execute_plan(state: dict) -> dict:
    """
    Execute every planning step.

    This is the OUTER workflow loop.

    For each step:
        1. Execute current step
        2. Save result in state
        3. Move to next step

    The code_agent has its own INNER agent loop.
    """

    total_steps = len(
        state["plan"]["steps"]
    )

    state["status"] = "in_progress"

    while state["current_step"] <= total_steps:

        step_result = execute_current_step(
            state
        )

        state["step_results"].append(
            step_result
        )

        state["current_step"] += 1

    state["status"] = "completed"

    return state


def run_workflow(
    project: str,
    task: str,
) -> str:
    """
    Run the complete CodeAtlas coding workflow.

    Task
      ↓
    Planner
      ↓
    State
      ↓
    Execute plan steps
      ↓
    Investigate / Modify / Test / Fix
      ↓
    Final synthesis
    """

    print()
    print("=" * 70)
    print("CODEATLAS CODING WORKFLOW")
    print("=" * 70)

    print(f"Project : {project}")
    print(f"Task    : {task}")

    # ---------------------------------------------------------
    # 1. CREATE PLAN
    # ---------------------------------------------------------

    plan = create_plan(task)

    print()
    print("PLAN")

    for step in plan["steps"]:

        print(
            f"  {step['id']}. "
            f"{step['action']}"
        )

    # ---------------------------------------------------------
    # 2. CREATE STATE
    # ---------------------------------------------------------

    state = create_initial_state(
        project=project,
        task=task,
        plan=plan,
    )

    # ---------------------------------------------------------
    # 3. EXECUTE COMPLETE PLAN
    # ---------------------------------------------------------

    final_state = execute_plan(
        state
    )

    # ---------------------------------------------------------
    # 4. FINAL SYNTHESIS
    # ---------------------------------------------------------

    final_answer = synthesize_result(
        final_state
    )

    print()
    print("=" * 70)
    print("FINAL RESULT")
    print("=" * 70)

    print(final_answer)

    return final_answer


if __name__ == "__main__":

    if len(sys.argv) < 3:

        print(
            'Usage: PYTHONPATH=. uv run python3 '
            'agents/executor.py '
            '<project> "<task>"'
        )

        print()
        print("Example:")

        print(
            '  PYTHONPATH=. uv run python3 '
            'agents/executor.py '
            'codeatlas/ecommerce '
            '"Add logging when stock reservation fails"'
        )

        sys.exit(1)

    PROJECT = sys.argv[1]
    TASK = sys.argv[2]

    run_workflow(
        project=PROJECT,
        task=TASK,
    )