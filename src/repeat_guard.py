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


def remember_changed_click(regions, action, verification_status, radius=DEFAULT_REPEAT_RADIUS):
    """Keep every visibly changed click region, without near-duplicates."""
    remembered = list(regions)
    if verification_status != "changed" or action.get("type") != "click":
        return remembered
    candidate = {
        "x": action["x"],
        "y": action["y"],
        "radius": radius,
        "reason": "previous_click_caused_visible_change",
    }
    if not click_in_forbidden_regions(action, remembered):
        remembered.append(candidate)
    return remembered


def click_in_forbidden_regions(action, regions):
    if action.get("type") != "click":
        return False
    return any(
        (action["x"] - region["x"]) ** 2
        + (action["y"] - region["y"]) ** 2
        <= region["radius"] ** 2
        for region in regions
    )


def format_forbidden_regions_prompt(regions):
    if not regions:
        return ""
    coordinates = ", ".join(
        f"({region['x']}, {region['y']}, radius {region['radius']})"
        for region in regions
    )
    return f"""

HARD RECOVERY CONSTRAINTS:
- Do not click any previously changed region: {coordinates}.
- Those controls already changed. Clicking them again can undo progress.
- Inspect the current screenshot for remaining goal requirements.
- If the requested setting already matches the goal, find Save, Apply, or a
  visible confirmation action. Do not change an unrelated setting.
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
