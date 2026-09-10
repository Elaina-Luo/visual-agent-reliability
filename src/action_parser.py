import json
import re


CLICK_KEYS = {"type", "x", "y"}
FINISH_KEYS = {"type"}


def parse_agent_action(
    raw_output: str,
    viewport_width: int,
    viewport_height: int,
) -> dict:
    if not isinstance(raw_output, str):
        raise ValueError("Model output must be text.")

    match = re.search(r"\{.*?\}", raw_output, flags=re.DOTALL)
    if match is None:
        raise ValueError("No JSON object found in model output.")

    try:
        action = json.loads(match.group())
    except json.JSONDecodeError as error:
        raise ValueError("Model output contains invalid JSON.") from error

    if not isinstance(action, dict):
        raise ValueError("Action must be a JSON object.")

    action_type = action.get("type")
    if action_type == "finish":
        if set(action) != FINISH_KEYS:
            raise ValueError("Finish action must only contain type.")
        return {"type": "finish"}

    if action_type != "click":
        raise ValueError("Action type must be click or finish.")

    if set(action) != CLICK_KEYS:
        raise ValueError("Click action must contain only type, x, and y.")

    x = action["x"]
    y = action["y"]
    if type(x) is not int or type(y) is not int:
        raise ValueError("Click coordinates must be integers.")

    if not (0 <= x < viewport_width and 0 <= y < viewport_height):
        raise ValueError(
            "Click coordinates are outside the screenshot viewport."
        )

    return {"type": "click", "x": x, "y": y}
