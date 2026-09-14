from src.episode_evaluator import task_state_succeeded


def classify_settings_transition(before_state, after_state, task):
    """Return an evaluator-only oracle label for a Settings transition."""
    if task_state_succeeded(after_state, task):
        return "complete"

    target_key = task["target_key"]
    target_value = task["target_value"]
    before_target = before_state["draft"][target_key] == target_value
    after_target = after_state["draft"][target_key] == target_value

    if before_target != after_target:
        return "progress" if after_target else "regression"

    target_section = task["section"]
    before_in_section = before_state["active_section"] == target_section
    after_in_section = after_state["active_section"] == target_section
    if before_in_section != after_in_section:
        return "progress" if after_in_section else "regression"

    before_confirmation = before_state["confirmation_visible"]
    after_confirmation = after_state["confirmation_visible"]
    if before_confirmation != after_confirmation:
        if after_confirmation and after_target:
            return "progress"
        if before_confirmation and not after_confirmation:
            return "regression"

    if before_state == after_state:
        return "no_effect"
    return "irrelevant"
