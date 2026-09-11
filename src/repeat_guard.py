DEFAULT_REPEAT_RADIUS = 12


def should_block_repeated_click(
    action,
    previous_executed_action,
    previous_verification_status,
    radius=DEFAULT_REPEAT_RADIUS,
):
    """Block an immediate near-identical click after visible change."""
    if previous_verification_status != "changed":
        return False
    if not previous_executed_action:
        return False
    if action.get("type") != "click":
        return False
    if previous_executed_action.get("type") != "click":
        return False

    delta_x = action["x"] - previous_executed_action["x"]
    delta_y = action["y"] - previous_executed_action["y"]
    return delta_x * delta_x + delta_y * delta_y <= radius * radius
