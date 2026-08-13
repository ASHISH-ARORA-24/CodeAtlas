import json
import sys

from agents.code_agent import run_agent


def print_trace_report(trace: dict) -> None:
    """
    Print a human-readable observability report
    from a CodeAtlas execution trace.
    """

    print()
    print("=" * 70)
    print("CODEATLAS TRACE")
    print("=" * 70)

    print()
    print(f"Task: {trace.get('task', '')}")

    events = trace.get(
        "events",
        [],
    )

    print()
    print("TIMELINE")
    print()

    step_number = 1

    for event in events:

        event_type = event.get(
            "type"
        )

        # -----------------------------------------------------
        # Ignore start/end marker events in the timeline.
        # -----------------------------------------------------

        if event_type in {
            "agent_start",
            "agent_end",
            "llm_call_start",
            "tool_call_start",
        }:
            continue

        # -----------------------------------------------------
        # LLM CALL
        # -----------------------------------------------------

        if event_type == "llm_call_end":

            duration_ms = event.get(
                "duration_ms",
                0,
            )

            total_tokens = event.get(
                "total_tokens",
                0,
            )

            cost = event.get(
                "estimated_cost_usd",
                0,
            )

            print(
                f"{step_number}. LLM Call"
            )

            print(
                f"   Duration : "
                f"{duration_ms:.2f} ms"
            )

            print(
                f"   Tokens   : "
                f"{total_tokens}"
            )

            print(
                f"   Cost     : "
                f"${cost:.8f}"
            )

            print()

            step_number += 1

        # -----------------------------------------------------
        # TOOL CALL
        # -----------------------------------------------------

        elif event_type == "tool_call_end":

            tool_name = event.get(
                "tool",
                "unknown"
            )

            duration_ms = event.get(
                "duration_ms",
                0,
            )

            success = event.get(
                "success",
                False,
            )

            status = (
                "SUCCESS"
                if success
                else "FAILED"
            )

            print(
                f"{step_number}. {tool_name}"
            )

            print(
                f"   Duration : "
                f"{duration_ms:.2f} ms"
            )

            print(
                f"   Status   : "
                f"{status}"
            )

            print()

            step_number += 1

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------

    print("-" * 70)
    print("SUMMARY")
    print("-" * 70)

    latency = trace.get(
        "latency_seconds",
        0,
    )

    tool_calls = trace.get(
        "tool_call_count",
        0,
    )

    token_usage = trace.get(
        "token_usage",
        {},
    )

    prompt_tokens = token_usage.get(
        "prompt_tokens",
        0,
    )

    completion_tokens = token_usage.get(
        "completion_tokens",
        0,
    )

    total_tokens = token_usage.get(
        "total_tokens",
        0,
    )

    total_cost = trace.get(
        "estimated_cost_usd",
        0,
    )

    failed_tools = sum(
        1
        for event in events
        if (
            event.get("type")
            == "tool_call_end"
            and not event.get(
                "success",
                False,
            )
        )
    )

    llm_calls = sum(
        1
        for event in events
        if event.get("type")
        == "llm_call_end"
    )

    print()
    print(
        f"Total Duration : "
        f"{latency:.3f} sec"
    )

    print(
        f"LLM Calls      : "
        f"{llm_calls}"
    )

    print(
        f"Tool Calls     : "
        f"{tool_calls}"
    )

    print(
        f"Input Tokens   : "
        f"{prompt_tokens}"
    )

    print(
        f"Output Tokens  : "
        f"{completion_tokens}"
    )

    print(
        f"Total Tokens   : "
        f"{total_tokens}"
    )

    print(
        f"Estimated Cost : "
        f"${total_cost:.8f}"
    )

    print(
        f"Tool Failures  : "
        f"{failed_tools}"
    )

    print()
    print("=" * 70)


def run_with_trace_report(
    project: str,
    task: str,
) -> dict:
    """
    Run CodeAtlas with tracing enabled and
    immediately print a human-readable report.
    """

    trace = run_agent(
        project=project,
        question=task,
        verbose=False,
        return_trace=True,
    )

    print_trace_report(
        trace
    )

    return trace


if __name__ == "__main__":

    if len(sys.argv) < 3:

        print(
            'Usage: PYTHONPATH=. uv run python3 '
            'observability/trace_reporter.py '
            '<project> "<task>"'
        )

        print()
        print("Example:")

        print(
            'PYTHONPATH=. uv run python3 '
            'observability/trace_reporter.py '
            'codeatlas/ecommerce '
            '"Explain what StockManager.reserve_stock does."'
        )

        sys.exit(1)

    PROJECT = sys.argv[1]
    TASK = sys.argv[2]

    run_with_trace_report(
        project=PROJECT,
        task=TASK,
    )