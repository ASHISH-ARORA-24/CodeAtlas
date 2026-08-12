def create_initial_state(project: str, task: str, plan: dict) -> dict:
    return {
        "project": project,
        "task": task,
        "plan": plan,
        "current_step": 1,
        "files_found": [],
        "dependencies": [],
        "step_results": [],
        "status": "planned",
    }