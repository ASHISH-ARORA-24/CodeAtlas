# Human approval gate for sensitive tool actions.
# Prints the tool name and arguments, then asks the user to approve or deny.


def request_human_approval(tool_name: str, arguments: dict) -> bool:
    """
    Asks the human whether a sensitive tool action should proceed.
    Returns True if approved, False if denied.
    """
    print()
    print("=" * 70)
    print("HUMAN APPROVAL REQUIRED")
    print("=" * 70)
    print(f"Tool      : {tool_name}")
    print(f"Arguments : {arguments}")
    print()

    answer = input("Approve this action? (y/n): ").strip().lower()
    return answer in {"y", "yes"}
