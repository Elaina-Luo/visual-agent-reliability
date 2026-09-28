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
