import json
from pathlib import Path

from agents.code_agent import run_agent
from evaluation.llm_judge import judge_agent_result

TEST_CASES_FILE = (
    Path(__file__).parent / "test_cases.json"
)


def load_test_cases() -> list:
    """
    Load evaluation test cases.
    """

    return json.loads(
        TEST_CASES_FILE.read_text(
            encoding="utf-8"
        )
    )


def normalize_file(
    repo: str,
    file_name: str,
) -> str:
    """
    Convert trace file information into:

        repo/file.py

    Example:

        inventory_service
        stock_manager.py

    becomes:

        inventory_service/stock_manager.py
    """

    return f"{repo}/{file_name}"


def evaluate_trace(
    test_case: dict,
    trace: dict,
) -> dict:
    """
    Compare expected behavior with the actual agent trace.
    """

    expected_files = set(
        test_case.get(
            "expected_files",
            [],
        )
    )

    forbidden_files = set(
        test_case.get(
            "forbidden_files",
            [],
        )
    )

    actual_read_files = {
        normalize_file(
            item["repo"],
            item["file"],
        )
        for item in trace.get(
            "files_read",
            [],
        )
    }

    actual_written_files = {
        normalize_file(
            item["repo"],
            item["file"],
        )
        for item in trace.get(
            "files_written",
            [],
        )
    }

    # All files the agent actually interacted with.
    actual_files = (
        actual_read_files
        | actual_written_files
    )

    # ---------------------------------------------------------
    # 1. EXPECTED FILES FOUND
    # ---------------------------------------------------------

    expected_files_found = (
        expected_files.issubset(
            actual_files
        )
    )

    # ---------------------------------------------------------
    # 2. FORBIDDEN FILES TOUCHED
    # ---------------------------------------------------------

    forbidden_files_touched = (
        actual_files
        & forbidden_files
    )

    no_forbidden_files = (
        len(
            forbidden_files_touched
        )
        == 0
    )

    # ---------------------------------------------------------
    # 3. TEST RESULT
    # ---------------------------------------------------------

    must_pass_tests = (
        test_case.get(
            "must_pass_tests",
            False,
        )
    )

    test_results = trace.get(
        "test_results",
        [],
    )

    if must_pass_tests:

        tests_passed = (
            len(test_results) > 0
            and all(
                result.get("passed")
                is True
                for result in test_results
            )
        )

    else:

        tests_passed = True

    # ---------------------------------------------------------
    # 4. UNEXPECTED WRITES
    #
    # For modification tasks, files written outside the
    # expected file list are suspicious.
    # ---------------------------------------------------------

    unexpected_writes = (
        actual_written_files
        - expected_files
    )

    no_unexpected_writes = (
        len(
            unexpected_writes
        )
        == 0
    )

    # ---------------------------------------------------------
    # 5. TOOL CALL COUNT
    #
    # For now this is informational only.
    # Later we can define thresholds.
    # ---------------------------------------------------------

    tool_call_count = trace.get(
        "tool_call_count",
        0,
    )

    # ---------------------------------------------------------
    # 6. BASIC SCORE
    #
    # 4 deterministic checks:
    #
    # expected file found
    # no forbidden files
    # tests passed
    # no unexpected writes
    # ---------------------------------------------------------

    checks = {
        "expected_files_found":
            expected_files_found,

        "no_forbidden_files":
            no_forbidden_files,

        "tests_passed":
            tests_passed,

        "no_unexpected_writes":
            no_unexpected_writes,
    }

    passed_checks = sum(
        1
        for value in checks.values()
        if value
    )

    total_checks = len(
        checks
    )

    score = round(
        (
            passed_checks
            / total_checks
        )
        * 100,
        2,
    )

    return {
        "test_id":
            test_case["id"],

        "task":
            test_case["task"],

        "score":
            score,

        "checks":
            checks,

        "expected_files":
            sorted(
                expected_files
            ),

        "actual_files":
            sorted(
                actual_files
            ),

        "actual_read_files":
            sorted(
                actual_read_files
            ),

        "actual_written_files":
            sorted(
                actual_written_files
            ),

        "forbidden_files_touched":
            sorted(
                forbidden_files_touched
            ),

        "unexpected_writes":
            sorted(
                unexpected_writes
            ),

        "tool_call_count":
            tool_call_count,

        "latency_seconds":
            trace.get(
                "latency_seconds"
            ),

        "token_usage":
            trace.get(
                "token_usage",
                {},
            ),
    }


def run_evaluation(
    project: str,
    test_case: dict,
) -> dict:
    """
    Run one test case through CodeAtlas and evaluate it.
    """

    trace = run_agent(
        project=project,
        question=test_case["task"],
        verbose=False,
        return_trace=True,
    )

    deterministic_result = evaluate_trace(
        test_case=test_case,
        trace=trace,
    )

    llm_result = judge_agent_result(
        test_case=test_case,
        trace=trace,
    )

    return {
        "deterministic":
            deterministic_result,

        "llm_judge":
            llm_result,
    }


if __name__ == "__main__":

    import sys

    if len(sys.argv) < 3:

        print(
            "Usage:"
        )

        print(
            "PYTHONPATH=. uv run python3 "
            "evaluation/evaluator.py "
            '<project> <test_id>'
        )

        print()

        print(
            "Example:"
        )

        print(
            "PYTHONPATH=. uv run python3 "
            "evaluation/evaluator.py "
            "codeatlas/ecommerce "
            "understand_reserve_stock"
        )

        sys.exit(1)

    PROJECT = sys.argv[1]
    TEST_ID = sys.argv[2]

    test_cases = load_test_cases()

    test_case = next(
        (
            case
            for case in test_cases
            if case["id"] == TEST_ID
        ),
        None,
    )

    if not test_case:

        print(
            f"Unknown test case: "
            f"{TEST_ID}"
        )

        sys.exit(1)

    result = run_evaluation(
        project=PROJECT,
        test_case=test_case,
    )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )