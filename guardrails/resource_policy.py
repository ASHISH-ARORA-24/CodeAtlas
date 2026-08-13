# Resource access policy for CodeAtlas.
# Controls which files the agent is allowed to read or write.

from pathlib import Path

SOURCE_ROOT = Path("source").resolve()

SENSITIVE_FILENAMES = {
    ".env", ".env.local", ".env.production", ".env.development",
    "credentials.json", "secrets.json", "id_rsa", "id_ed25519",
}

SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}

SENSITIVE_WORDS    = ["secret", "credential", "private_key", "token"]


def authorize_file_access(project: str, repo: str, file_path: str, operation: str) -> dict:
    """
    Validates whether read or write access to a file is allowed.

    Checks: project exists, repo exists inside project, no path traversal,
    no sensitive filenames, no sensitive suffixes, no sensitive path words,
    and write-specific rules (file must already exist).
    """
    project_root   = (SOURCE_ROOT / project).resolve()
    repo_root      = (project_root / repo).resolve()
    requested_file = (repo_root / file_path).resolve()

    if not project_root.exists():
        return {"decision": "deny", "reason": f"Project does not exist: {project}"}

    if not repo_root.exists():
        return {"decision": "deny", "reason": f"Repository '{repo}' does not exist inside project '{project}'."}

    try:
        requested_file.relative_to(repo_root)
    except ValueError:
        return {"decision": "deny", "reason": "Requested file is outside the approved repository."}

    filename = requested_file.name.lower()

    if filename in SENSITIVE_FILENAMES:
        return {"decision": "deny", "reason": f"Access to sensitive file '{filename}' is blocked."}

    if requested_file.suffix.lower() in SENSITIVE_SUFFIXES:
        return {"decision": "deny", "reason": f"Access to sensitive file type '{requested_file.suffix}' is blocked."}

    if any(word in str(requested_file).lower() for word in SENSITIVE_WORDS):
        return {"decision": "deny", "reason": "Requested path appears to contain sensitive information."}

    if operation == "write":
        if not requested_file.exists():
            return {"decision": "deny", "reason": "Creating new files is not allowed in the current guardrail policy."}
        if not requested_file.is_file():
            return {"decision": "deny", "reason": "Write target must be an existing file."}

    if operation == "read":
        if not requested_file.exists():
            return {"decision": "deny", "reason": "Requested file does not exist."}
        if not requested_file.is_file():
            return {"decision": "deny", "reason": "Read target must be a file."}

    return {"decision": "allow", "reason": f"{operation} access is allowed for {repo}/{file_path}"}
