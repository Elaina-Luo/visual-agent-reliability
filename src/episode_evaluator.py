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
    termination_signal_emitted = termination_reason in {
        "agent_finish",
        "verifier_complete",
    }
    agent_terminated_correctly = (
        termination_signal_emitted and task_state_success
    )

    return {
        "task_state_success": task_state_success,
        "termination_signal_emitted": termination_signal_emitted,
        "agent_terminated_correctly": agent_terminated_correctly,
        "success": agent_terminated_correctly,
    }
