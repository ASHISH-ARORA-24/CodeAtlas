import sys

from agents.code_agent import run_agent
from agents.planner import create_plan
from agents.state import create_initial_state
from agents.synthesizer import synthesize_result


def execute_current_step(state: dict) -> dict:
    """
    Executes the current planning step using the existing CodeAtlas agent.

    Flow:
        state
          ↓
        current_step
          ↓
        code_agent
          ↓
        findings
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

Investigate this step using the available CodeAtlas tools.

Do not modify code.

Return your findings for this planning step.
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
    Executes all planning steps.

    This is the OUTER workflow loop.

    For every step:
        1. Execute current step
        2. Store result in state
        3. Increment current_step

    When all steps finish:
        status = completed
    """

    total_steps = len(state["plan"]["steps"])

    state["status"] = "in_progress"

    while state["current_step"] <= total_steps:

        step_result = execute_current_step(state)

        # Store findings from this planning step.
        state["step_results"].append(step_result)

        # Move workflow to next step.
        state["current_step"] += 1

    state["status"] = "completed"

    return state


def run_workflow(project: str, task: str) -> str:
    """
    Runs the complete Iteration 2 workflow.

    Task
      ↓
    Planner
      ↓
    State
      ↓
    Execute all plan steps
      ↓
    Final synthesis
      ↓
    Final recommendation
    """

    print()
    print("=" * 70)
    print("CODEATLAS PLANNING WORKFLOW")
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
    # 2. CREATE INITIAL STATE
    # ---------------------------------------------------------

    state = create_initial_state(
        project=project,
        task=task,
        plan=plan,
    )

    # ---------------------------------------------------------
    # 3. EXECUTE PLAN
    # ---------------------------------------------------------

    final_state = execute_plan(state)

    # ---------------------------------------------------------
    # 4. FINAL SYNTHESIS
    # ---------------------------------------------------------

    final_answer = synthesize_result(
        final_state
    )

    print()
    print("=" * 70)
    print("FINAL RECOMMENDATION")
    print("=" * 70)
    print(final_answer)

    return final_answer


if __name__ == "__main__":

    if len(sys.argv) < 3:

        print(
            'Usage: PYTHONPATH=. uv run python3 '
            'agents/executor.py <project> "<task>"'
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