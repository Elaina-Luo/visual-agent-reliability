def task_state_succeeded(state, task):
    """Return whether the environment reached the requested saved state."""
    return (
        state["saved"][task["target_key"]] == task["target_value"]
        and state["has_unapplied_changes"] is False
        and state["confirmation_visible"] is False
    )


def evaluate_episode(state, task, termination_reason):
    """Separate task completion from the Agent's decision to stop."""
    task_state_success = task_state_succeeded(state, task)
    agent_terminated_correctly = termination_reason == "agent_finish"

    return {
        "task_state_success": task_state_success,
        "agent_terminated_correctly": agent_terminated_correctly,
        "success": task_state_success and agent_terminated_correctly,
    }
