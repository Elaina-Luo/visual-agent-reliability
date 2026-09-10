def choose_recovery(status, retry_already_used):
    """Map a visual verification result to one bounded recovery decision."""
    if status == "complete":
        return "finish"
    if status == "no_effect" and not retry_already_used:
        return "retry"
    return "replan"
