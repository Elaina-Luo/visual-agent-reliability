import json
import re


VALID_VERIFICATION_STATUSES = {
    "complete",
    "changed",
    "no_effect",
    "uncertain",
}


def parse_verification(raw_output: str) -> dict:
    if not isinstance(raw_output, str):
        raise ValueError("Verifier output must be text.")

    matches = re.findall(r"\{.*?\}", raw_output, flags=re.DOTALL)
    if not matches:
        raise ValueError("No JSON object found in verifier output.")
    if len(matches) != 1:
        raise ValueError("Verifier output must contain exactly one JSON object.")

    try:
        verification = json.loads(matches[0])
    except json.JSONDecodeError as error:
        raise ValueError("Verifier output contains invalid JSON.") from error

    if not isinstance(verification, dict):
        raise ValueError("Verification must be a JSON object.")
    if set(verification) != {"status"}:
        raise ValueError("Verification must contain only status.")

    status = verification["status"]
    if status not in VALID_VERIFICATION_STATUSES:
        raise ValueError("Unknown verification status.")

    return {"status": status}
