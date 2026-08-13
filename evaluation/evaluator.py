# Evaluator for CodeAtlas agent.
# Runs test cases through the agent and scores the results
# using deterministic checks and an LLM judge.
#
# Usage:
#   PYTHONPATH=. uv run python3 evaluation/evaluator.py <project> <test_id>

import json
import sys
from pathlib import Path

from agents.code_agent import run_agent
from evaluation.llm_judge import judge_agent_result

TEST_CASES_FILE = Path(__file__).parent / "test_cases.json"


def load_test_cases() -> list:
    """Loads evaluation test cases from test_cases.json."""
    return json.loads(TEST_CASES_FILE.read_text(encoding="utf-8"))


def normalize_file(repo: str, file_name: str) -> str:
    """Converts repo + filename into repo/file.py format."""
    return f"{repo}/{file_name}"


def evaluate_trace(test_case: dict, trace: dict) -> dict:
    """Compares expected behavior with the actual agent trace using 4 deterministic checks."""
    expected_files  = set(test_case.get("expected_files", []))
    forbidden_files = set(test_case.get("forbidden_files", []))

    actual_read_files    = {normalize_file(f["repo"], f["file"]) for f in trace.get("files_read", [])}
    actual_written_files = {normalize_file(f["repo"], f["file"]) for f in trace.get("files_written", [])}
    actual_files         = actual_read_files | actual_written_files

    expected_files_found  = expected_files.issubset(actual_files)
    forbidden_touched     = actual_files & forbidden_files
    no_forbidden_files    = len(forbidden_touched) == 0
    unexpected_writes     = actual_written_files - expected_files
    no_unexpected_writes  = len(unexpected_writes) == 0

    test_results   = trace.get("test_results", [])
    must_pass_tests = test_case.get("must_pass_tests", False)
    tests_passed   = (
        len(test_results) > 0 and all(r.get("passed") is True for r in test_results)
        if must_pass_tests else True
    )

    checks = {
        "expected_files_found": expected_files_found,
        "no_forbidden_files":   no_forbidden_files,
        "tests_passed":         tests_passed,
        "no_unexpected_writes": no_unexpected_writes,
    }

    passed_checks = sum(1 for v in checks.values() if v)
    score = round((passed_checks / len(checks)) * 100, 2)

    return {
        "test_id":                test_case["id"],
        "task":                   test_case["task"],
        "score":                  score,
        "checks":                 checks,
        "expected_files":         sorted(expected_files),
        "actual_files":           sorted(actual_files),
        "actual_read_files":      sorted(actual_read_files),
        "actual_written_files":   sorted(actual_written_files),
        "forbidden_files_touched": sorted(forbidden_touched),
        "unexpected_writes":      sorted(unexpected_writes),
        "tool_call_count":        trace.get("tool_call_count", 0),
        "latency_seconds":        trace.get("latency_seconds"),
        "token_usage":            trace.get("token_usage", {}),
    }


def run_evaluation(project: str, test_case: dict) -> dict:
    """Runs one test case through CodeAtlas and evaluates it."""
    trace = run_agent(project=project, question=test_case["task"], verbose=False, return_trace=True)

    return {
        "deterministic": evaluate_trace(test_case=test_case, trace=trace),
        "llm_judge":     judge_agent_result(test_case=test_case, trace=trace),
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: PYTHONPATH=. uv run python3 evaluation/evaluator.py <project> <test_id>")
        sys.exit(1)

    PROJECT = sys.argv[1]
    TEST_ID = sys.argv[2]

    test_cases = load_test_cases()
    test_case  = next((c for c in test_cases if c["id"] == TEST_ID), None)

    if not test_case:
        print(f"Unknown test case: {TEST_ID}")
        sys.exit(1)

    print(json.dumps(run_evaluation(project=PROJECT, test_case=test_case), indent=2))
