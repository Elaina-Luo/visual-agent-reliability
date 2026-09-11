import json
import re


def parse_completion_gate(raw_output: str) -> dict:
    if not isinstance(raw_output, str):
        raise ValueError("Completion Gate output must be text.")

    matches = re.findall(r"\{.*?\}", raw_output, flags=re.DOTALL)
    if not matches:
        raise ValueError("No JSON object found in Completion Gate output.")
    if len(matches) != 1:
        raise ValueError(
            "Completion Gate output must contain exactly one JSON object."
        )

    try:
        decision = json.loads(matches[0])
    except json.JSONDecodeError as error:
        raise ValueError(
            "Completion Gate output contains invalid JSON."
        ) from error

    if not isinstance(decision, dict):
        raise ValueError("Completion Gate decision must be a JSON object.")
    if set(decision) != {"pending_action"}:
        raise ValueError(
            "Completion Gate decision must contain only pending_action."
        )
    if type(decision["pending_action"]) is not bool:
        raise ValueError("pending_action must be a JSON boolean.")

    return {"pending_action": decision["pending_action"]}


def gate_completion(transition_status, pending_action):
    """Require the visual stop gate to approve a complete candidate."""
    if transition_status != "complete":
        return transition_status
    if pending_action:
        return "changed"
    return "complete"
