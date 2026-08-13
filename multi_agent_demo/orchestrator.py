# Multi-agent orchestrator for CodeAtlas.
#
# Architecture (plan-and-execute pattern):
#
#   User task
#      ↓
#   Orchestrator (owns the agent registry)
#      ↓  passes {task, available_agents}
#   Planner (picks which stages are needed + order)
#      ↓  returns workflow like ["coder", "tester", "reviewer"]
#   Orchestrator walks the workflow list
#      ↓
#   Each agent runs its own inner tool loop
#      ↓
#   If any agent returns need_information → orchestrator routes to
#   analyst → returns findings → re-calls the requesting agent
#      ↓
#   Finish
#
# Why this design:
# - Only the planner decides "which stages are needed" — one place for that logic
# - Only the orchestrator knows which agents exist and how to invoke them
# - Agents remain completely ignorant of each other
# - Orchestrator is dumb: it executes a plan and handles one detour rule
#
# Usage:
#   PYTHONPATH=. uv run python3 multi_agent_demo/orchestrator.py <project> "<task>"

import json
import sys

from multi_agent_demo.planner_agent  import run_planner_agent
from multi_agent_demo.analyst_agent  import run_analyst_agent
from multi_agent_demo.coding_agent   import run_coding_agent
from multi_agent_demo.testing_agent  import run_testing_agent
from multi_agent_demo.reviewer_agent import run_reviewer_agent


# Agent registry — describes each agent for the planner AND wires up how
# to invoke it. Each entry has:
#   description:  what the planner sees when choosing agents
#   invoke:       callable that runs the agent, given (project, task, state)
#   result_key:   where in shared state to store the agent's output
#
# Adding a new agent = adding one entry to this dict. No if/else to grow.
AGENTS = {
    "analyst": {
        "description": "Investigates source code — finds relevant files, symbols, dependencies, and tests.",
        "invoke": lambda project, task, state: run_analyst_agent(
            project=project,
            task=task,
            request=state.get("info_request", "Investigate relevant code, files, dependencies, and tests."),
        ),
        "result_key": "analysis",
    },
    "coder": {
        "description": "Designs the proposed code change based on the plan.",
        "invoke": lambda project, task, state: run_coding_agent(
            project=project, task=task, plan=state["plan"],
        ),
        "result_key": "coding_result",
    },
    "tester": {
        "description": "Evaluates testing requirements and coverage for the proposed change.",
        "invoke": lambda project, task, state: run_testing_agent(
            project=project, task=task, coding_result=state["coding_result"],
        ),
        "result_key": "testing_result",
    },
    "reviewer": {
        "description": "Independently reviews the proposed change and testing assessment.",
        "invoke": lambda project, task, state: run_reviewer_agent(
            project=project,
            task=task,
            coding_result=state["coding_result"],
            testing_result=state["testing_result"],
        ),
        "result_key": "review_result",
    },
}


# What the planner sees — just names + descriptions, no implementation details.
AGENT_REGISTRY = {name: cfg["description"] for name, cfg in AGENTS.items()}


def call_agent(name: str, project: str, task: str, state: dict) -> dict:
    """Dispatcher — dict lookup, no if/else."""
    return AGENTS[name]["invoke"](project, task, state)


def store_result(agent_name: str, agent_output: dict, state: dict) -> None:
    """Store the agent's output under its configured state key."""
    state[AGENTS[agent_name]["result_key"]] = agent_output.get("result")


def route_info_request(requesting_agent: str, agent_output: dict, project: str, task: str, state: dict) -> None:
    """
    Handles the ONE detour pattern we support: an agent asks for information,
    orchestrator routes to analyst, findings go back to the requesting agent.

    Analyst is the only info-provider in the current system, so routing is
    trivial. If more info-providers are added later, this function grows
    into a small router (or delegates to another LLM).
    """
    request = agent_output.get("request", "Investigate the relevant code.")

    print(f"  ↪ {requesting_agent} needs information — routing to analyst")
    print(f"    Request: {request}")

    # Pass the specific request to the analyst via state
    state["info_request"] = request

    analyst_output = run_analyst_agent(project=project, task=task, request=request)
    store_result("analyst", analyst_output, state)


def run_orchestrator(project: str, task: str) -> dict:
    """
    Runs the full multi-agent workflow.

    Flow:
    1. Ask planner for a workflow (planner may need information first)
    2. Walk the workflow list, calling each agent in order
    3. Any agent that returns need_information triggers an analyst detour,
       then the requesting agent is re-called with the analysis available
    4. Return the accumulated state
    """
    print()
    print("=" * 70)
    print("MULTI-AGENT ORCHESTRATOR")
    print("=" * 70)
    print(f"Project : {project}")
    print(f"Task    : {task}")

    # Shared state — every agent's output lives here
    state: dict = {}

    # ---------------------------------------------------------
    # STEP 1: Ask the planner what workflow this task needs
    # ---------------------------------------------------------
    print("\n--- PLANNER ---")
    plan_output = run_planner_agent(task=task, available_agents=AGENT_REGISTRY)
    print(f"  Status: {plan_output['status']}")

    # If planner needs info first, detour through analyst and re-plan
    if plan_output["status"] == "need_information":
        route_info_request("planner", plan_output, project, task, state)
        plan_output = run_planner_agent(
            task=task,
            available_agents=AGENT_REGISTRY,
            prior_findings=state.get("analysis"),
        )
        print(f"  Re-planned status: {plan_output['status']}")

    if plan_output["status"] != "plan_ready":
        print(f"\n✗ Planner could not produce a plan: {plan_output}")
        return {"status": "failed", "reason": "planner_failure", "state": state}

    plan = plan_output["result"]
    state["plan"] = plan
    workflow = plan["workflow"]

    print(f"\n  Workflow : {' → '.join(workflow)}")
    print(f"  Reason   : {plan.get('reason', 'n/a')}")

    # ---------------------------------------------------------
    # STEP 2: Execute the workflow — each agent in order
    # ---------------------------------------------------------
    for agent_name in workflow:
        # Skip if planner accidentally includes an unknown agent
        if agent_name not in AGENT_REGISTRY:
            print(f"\n✗ Planner referenced unknown agent: {agent_name} — skipping")
            continue

        print(f"\n--- {agent_name.upper()} ---")
        agent_output = call_agent(agent_name, project, task, state)

        # Detour: this agent needs information → analyst → re-call
        if agent_output.get("status") == "need_information":
            route_info_request(agent_name, agent_output, project, task, state)
            # Re-call the requesting agent now that analyst findings are in state
            agent_output = call_agent(agent_name, project, task, state)

        print(f"  Status: {agent_output.get('status')}")
        store_result(agent_name, agent_output, state)

    # ---------------------------------------------------------
    # STEP 3: Done
    # ---------------------------------------------------------
    print()
    print("=" * 70)
    print("WORKFLOW COMPLETE")
    print("=" * 70)

    return {"status": "completed", "state": state}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: PYTHONPATH=. uv run python3 multi_agent_demo/orchestrator.py <project> \"<task>\"")
        print("\nExample:")
        print("  PYTHONPATH=. uv run python3 multi_agent_demo/orchestrator.py codeatlas/ecommerce \"Add validation for negative stock\"")
        sys.exit(1)

    result = run_orchestrator(project=sys.argv[1], task=sys.argv[2])

    print()
    print("FINAL STATE")
    print(json.dumps(result, indent=2, default=str))
