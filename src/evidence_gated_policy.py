from src.visual_change import DEFAULT_CHANGED_FRACTION_THRESHOLD


def evidence_gated_status(
    vlm_status,
    pixel_change_fraction,
    changed_fraction_threshold=DEFAULT_CHANGED_FRACTION_THRESHOLD,
):
    """A semantic complete label cannot override deterministic no-change."""
    changed = pixel_change_fraction >= changed_fraction_threshold
    if not changed:
        return "no_effect"
    if vlm_status == "complete":
        return "completion_candidate"
    return "changed"


def should_retry_no_effect(status, retry_already_used, action_budget_remaining):
    return (
        status == "no_effect"
        and not retry_already_used
        and action_budget_remaining > 0
    )


def can_replan(blocked_replans, max_blocked_replans):
    return blocked_replans < max_blocked_replans


def update_completion_sequence(sequence, action, status):
    """Track consecutive candidates from distinct executed click actions."""
    if status != "completion_candidate" or action.get("type") != "click":
        return []
    candidate = {"x": action["x"], "y": action["y"]}
    if sequence and sequence[-1] == candidate:
        return [candidate]
    return [*sequence[-1:], candidate]


def completion_evidence_confirmed(sequence, required_candidates=2):
    return len(sequence) >= required_candidates


def can_retry_invalid(invalid_replans, max_invalid_replans):
    return invalid_replans < max_invalid_replans
