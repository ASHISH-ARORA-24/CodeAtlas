#!/usr/bin/env bash

set -u

PROJECT="codeatlas/ecommerce"

PASS_COUNT=0
FAIL_COUNT=0

run_check() {
    local name="$1"
    shift

    echo
    echo "======================================================================"
    echo "CHECK: $name"
    echo "======================================================================"

    if "$@"; then
        echo
        echo "RESULT: PASS - $name"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo
        echo "RESULT: FAIL - $name"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
}

echo
echo "======================================================================"
echo "CODEATLAS SMOKE TEST"
echo "======================================================================"
echo "Project: $PROJECT"
echo

# ---------------------------------------------------------------------
# 1. MEMORY STORE
# ---------------------------------------------------------------------

run_check \
    "Memory retrieval" \
    env PYTHONPATH=. uv run python3 memory/memory_store.py \
    get "$PROJECT"


# ---------------------------------------------------------------------
# 2. TOOL AUTHORIZATION GUARDRAILS
# ---------------------------------------------------------------------

run_check \
    "Guardrail - allowed tool" \
    env PYTHONPATH=. uv run python3 -c \
    'from guardrails.tool_policy import authorize_tool; r=authorize_tool("search_code"); print(r); assert r["decision"] == "allow"'


run_check \
    "Guardrail - denied tool" \
    env PYTHONPATH=. uv run python3 -c \
    'from guardrails.tool_policy import authorize_tool; r=authorize_tool("execute_shell"); print(r); assert r["decision"] == "deny"'


# ---------------------------------------------------------------------
# 3. RESOURCE / FILE GUARDRAILS
# ---------------------------------------------------------------------

run_check \
    "Resource guardrail - approved file" \
    env PYTHONPATH=. uv run python3 -c \
    'from guardrails.resource_policy import authorize_file_access; r=authorize_file_access("codeatlas/ecommerce","inventory_service","stock_manager.py","read"); print(r); assert r["decision"] == "allow"'


run_check \
    "Resource guardrail - path traversal blocked" \
    env PYTHONPATH=. uv run python3 -c \
    'from guardrails.resource_policy import authorize_file_access; r=authorize_file_access("codeatlas/ecommerce","inventory_service","../../../../.env","read"); print(r); assert r["decision"] == "deny"'


run_check \
    "Resource guardrail - sensitive file blocked" \
    env PYTHONPATH=. uv run python3 -c \
    'from guardrails.resource_policy import authorize_file_access; r=authorize_file_access("codeatlas/ecommerce","inventory_service",".env","read"); print(r); assert r["decision"] == "deny"'


# ---------------------------------------------------------------------
# 4. BASIC CODE AGENT
# ---------------------------------------------------------------------

run_check \
    "Code agent - read-only reasoning" \
    env PYTHONPATH=. uv run python3 agents/code_agent.py \
    "$PROJECT" \
    "Explain what StockManager.reserve_stock does."


# ---------------------------------------------------------------------
# 5. EVALUATION TRACE
# ---------------------------------------------------------------------

run_check \
    "Code agent - structured trace" \
    env PYTHONPATH=. uv run python3 -c \
    'from agents.code_agent import run_agent; r=run_agent(project="codeatlas/ecommerce", question="Explain what StockManager.reserve_stock does.", verbose=False, return_trace=True); print(r); assert "final_answer" in r; assert "tools_called" in r; assert "events" in r; assert "latency_seconds" in r; assert "token_usage" in r; assert "estimated_cost_usd" in r'


# ---------------------------------------------------------------------
# 6. DETERMINISTIC + LLM EVALUATION
# ---------------------------------------------------------------------

run_check \
    "Evaluation - understand_reserve_stock" \
    env PYTHONPATH=. uv run python3 evaluation/evaluator.py \
    "$PROJECT" \
    understand_reserve_stock


# ---------------------------------------------------------------------
# 7. OBSERVABILITY / TRACE REPORT
# ---------------------------------------------------------------------

run_check \
    "Observability trace report" \
    env PYTHONPATH=. uv run python3 observability/trace_reporter.py \
    "$PROJECT" \
    "Explain what StockManager.reserve_stock does."


# ---------------------------------------------------------------------
# 8. PROJECT TESTS
# ---------------------------------------------------------------------

run_check \
    "Inventory service tests" \
    env PYTHONPATH=. uv run python3 tools/run_tests.py \
    "$PROJECT" \
    inventory_service


# ---------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------

echo
echo "======================================================================"
echo "SMOKE TEST SUMMARY"
echo "======================================================================"
echo "PASS: $PASS_COUNT"
echo "FAIL: $FAIL_COUNT"
echo

if [ "$FAIL_COUNT" -eq 0 ]; then
    echo "CODEATLAS STATUS: ALL CHECKS PASSED"
    exit 0
else
    echo "CODEATLAS STATUS: SOME CHECKS FAILED"
    exit 1
fi