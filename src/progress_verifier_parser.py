import json
import re


VALID_PROGRESS_STATUSES = {
    "complete",
    "progress",
    "regression",
    "irrelevant",
    "no_effect",
    "uncertain",
}


def parse_progress_verification(raw_output: str) -> dict:
    if not isinstance(raw_output, str):
        raise ValueError("Progress Verifier output must be text.")

    matches = re.findall(r"\{.*?\}", raw_output, flags=re.DOTALL)
    if not matches:
        raise ValueError(
            "No JSON object found in Progress Verifier output."
        )
    if len(matches) != 1:
        raise ValueError(
            "Progress Verifier output must contain exactly one JSON object."
        )

    try:
        verification = json.loads(matches[0])
    except json.JSONDecodeError as error:
        raise ValueError(
            "Progress Verifier output contains invalid JSON."
        ) from error

    if not isinstance(verification, dict):
        raise ValueError("Progress verification must be a JSON object.")
    if set(verification) != {"status"}:
        raise ValueError(
            "Progress verification must contain only status."
        )

    status = verification["status"]
    if status not in VALID_PROGRESS_STATUSES:
        raise ValueError("Unknown progress verification status.")

    return {"status": status}
