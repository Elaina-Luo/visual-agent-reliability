"""Shared raw visual-verifier path for clean B/C (no fusion or stop gate)."""

import time

from src.verifier_parser import parse_verification


def verify_action(verifier, before_image, after_image, goal, action):
    started = time.perf_counter()
    raw_output = None
    latency = None
    status = "uncertain"
    error = None
    try:
        raw_output, latency = verifier.verify(
            before_image=before_image,
            after_image=after_image,
            goal=goal,
            requested_action=dict(action),
        )
        status = parse_verification(raw_output)["status"]
    except Exception as exception:
        error = f"{type(exception).__name__}: {exception}"
    return {
        "raw_output": raw_output,
        "status": status,
        "latency_seconds": latency,
        "wall_latency_seconds": time.perf_counter() - started,
        "error": error,
    }
