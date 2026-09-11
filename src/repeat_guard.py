DEFAULT_REPEAT_RADIUS = 12


def active_forbidden_click_region(
    previous_executed_action,
    previous_verification_status,
    radius=DEFAULT_REPEAT_RADIUS,
):
    """Describe the click region that the Actor must not repeat."""
    if previous_verification_status != "changed":
        return None
    if not previous_executed_action:
        return None
    if previous_executed_action.get("type") != "click":
        return None

    return {
        "x": previous_executed_action["x"],
        "y": previous_executed_action["y"],
        "radius": radius,
        "reason": "previous_click_caused_visible_change",
    }


def format_forbidden_region_prompt(forbidden_click_region):
    if not forbidden_click_region:
        return ""

    return f"""

HARD REPLANNING CONSTRAINT:
- Do not click within {forbidden_click_region['radius']} pixels of
  ({forbidden_click_region['x']}, {forbidden_click_region['y']}).
- That previous click already caused a visible change. Repeating it can undo
  progress and the system will block it.
- Inspect the current screenshot and choose a different control needed to
  finish and save the goal.
"""


def should_block_repeated_click(
    action,
    previous_executed_action,
    previous_verification_status,
    radius=DEFAULT_REPEAT_RADIUS,
):
    """Block an immediate near-identical click after visible change."""
    forbidden_region = active_forbidden_click_region(
        previous_executed_action,
        previous_verification_status,
        radius,
    )
    if forbidden_region is None or action.get("type") != "click":
        return False

    delta_x = action["x"] - forbidden_region["x"]
    delta_y = action["y"] - forbidden_region["y"]
    return delta_x * delta_x + delta_y * delta_y <= radius * radius
