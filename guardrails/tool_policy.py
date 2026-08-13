from enum import Enum


class AuthorizationDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


# Tools currently available in CodeAtlas
ALLOWED_TOOLS = {
    "search_code",
    "get_dependencies",
    "read_file",
    "run_tests",
    "save_memory",
}

DENIED_TOOLS = {
    "delete_file",
    "delete_repository",
    "execute_shell",
}

APPROVAL_REQUIRED_TOOLS = {
    "write_file",
    # GitHub SDLC tools will be added here when implemented (Iteration 5):
    # "create_pull_request", "push_branch", "merge_branch"
}


def authorize_tool(tool_name: str) -> dict:
    """
    Decide whether the requested tool is authorized.

    Possible decisions:
        allow
        deny
        require_approval
    """

    if tool_name in DENIED_TOOLS:
        return {
            "decision": AuthorizationDecision.DENY.value,
            "reason": (
                f"Tool '{tool_name}' is blocked "
                "by CodeAtlas security policy."
            ),
        }

    if tool_name in APPROVAL_REQUIRED_TOOLS:
        return {
            "decision": AuthorizationDecision.REQUIRE_APPROVAL.value,
            "reason": (
                f"Tool '{tool_name}' requires human approval."
            ),
        }

    if tool_name in ALLOWED_TOOLS:
        return {
            "decision": AuthorizationDecision.ALLOW.value,
            "reason": (
                f"Tool '{tool_name}' is allowed."
            ),
        }

    # Anything we did not explicitly allow is blocked.
    return {
        "decision": AuthorizationDecision.DENY.value,
        "reason": (
            f"Unknown tool '{tool_name}' is denied by default."
        ),
    }


if __name__ == "__main__":

    import json
    import sys

    if len(sys.argv) < 2:
        print(
            "Usage: PYTHONPATH=. uv run python3 "
            "guardrails/tool_policy.py <tool_name>"
        )
        sys.exit(1)

    TOOL_NAME = sys.argv[1]

    result = authorize_tool(TOOL_NAME)

    print(
        json.dumps(
            result,
            indent=2,
        )
    )