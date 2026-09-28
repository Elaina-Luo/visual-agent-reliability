import json
import re


CLICK_KEYS = {"status", "x", "y"}
QWEN_CLICK_KEYS = {"status", "x"}
UNAVAILABLE_KEYS = {"status"}


def build_locator_prompt(goal, width, height, forbidden_regions=None):
    regions = forbidden_regions or []
    blocked = [
        {"x": item["x"], "y": item["y"], "radius": item["radius"]}
        for item in regions
    ]
    return f"""
You are a visual recovery locator for a desktop Settings application.

Original task:
{goal}

The Actor repeated a setting control that had already changed. Inspect only
the current screenshot. If an enabled Save changes, Apply, or visible
confirmation action is currently required to finish the task, return its click
coordinate. Do not click a setting toggle or any blocked region.

Screenshot size: width={width}, height={height}
Blocked regions: {json.dumps(blocked)}

Return exactly one JSON object and no explanation.
If a recovery action is visible:
{{"status":"click","x":integer,"y":integer}}

If no appropriate recovery action is visible:
{{"status":"unavailable"}}
""".strip()


def parse_locator_output(raw_output, viewport_width, viewport_height):
    if not isinstance(raw_output, str):
        raise ValueError("Locator output must be text.")

    matches = re.findall(r"\{.*?\}", raw_output, flags=re.DOTALL)
    if len(matches) != 1:
        raise ValueError("Locator output must contain exactly one JSON object.")
    try:
        decision = json.loads(matches[0])
    except json.JSONDecodeError as error:
        raise ValueError("Locator output contains invalid JSON.") from error
    if not isinstance(decision, dict):
        raise ValueError("Locator decision must be a JSON object.")

    if decision.get("status") == "unavailable":
        if set(decision) != UNAVAILABLE_KEYS:
            raise ValueError("Unavailable decision must only contain status.")
        return None
    if decision.get("status") != "click":
        raise ValueError("Locator status must be click or unavailable.")

    if set(decision) == CLICK_KEYS:
        x, y = decision["x"], decision["y"]
        if isinstance(x, list):
            if len(x) != 2 or x[1] != y:
                raise ValueError(
                    "Redundant locator coordinate pair must agree with y."
                )
            x = x[0]
    elif set(decision) == QWEN_CLICK_KEYS:
        pair = decision["x"]
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError("Locator coordinate pair must contain two items.")
        x, y = pair
    else:
        raise ValueError("Click decision must contain only status, x, and y.")

    if type(x) is not int or type(y) is not int:
        raise ValueError("Locator coordinates must be integers.")
    if not (0 <= x < viewport_width and 0 <= y < viewport_height):
        raise ValueError("Locator coordinates are outside the screenshot.")
    return {"type": "click", "x": x, "y": y}
