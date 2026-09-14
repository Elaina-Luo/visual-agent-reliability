import argparse
import json
from pathlib import Path

from PIL import Image

from src.progress_audit import classify_settings_transition
from src.progress_verifier_parser import parse_progress_verification
from src.qwen_progress_verifier import QwenProgressVerifier
from src.qwen_settings_agent import DEFAULT_MODEL_ID, QwenSettingsAgent


def load_rgb(path):
    with Image.open(path) as image:
        return image.convert("RGB")


def evaluate_trace(result_path, verifier):
    episode = json.loads(result_path.read_text(encoding="utf-8"))
    artifact_dir = result_path.parent
    task = episode["task"]
    records = []

    for trace_record in episode["trace"]:
        before_name = trace_record.get("observation_before")
        after_name = trace_record.get("observation_after")
        action = trace_record.get("action")
        if not before_name or not after_name or not action:
            continue

        before_image = load_rgb(artifact_dir / before_name)
        after_image = load_rgb(artifact_dir / after_name)
        raw_output = None
        latency_seconds = None
        try:
            raw_output, latency_seconds = verifier.verify(
                before_image=before_image,
                after_image=after_image,
                goal=task["goal"],
                requested_action=action,
            )
        except Exception as exception:
            predicted_status = "uncertain"
            error = f"{type(exception).__name__}: {exception}"
        else:
            try:
                parsed = parse_progress_verification(raw_output)
                predicted_status = parsed["status"]
                error = None
            except ValueError as exception:
                predicted_status = "uncertain"
                error = f"{type(exception).__name__}: {exception}"

        before_state = trace_record.get("evaluator_state_before")
        after_state = trace_record.get("evaluator_state_after")
        audit_status = None
        if before_state is not None and after_state is not None:
            # Evaluator state is used only after model inference for offline
            # scoring. It is never included in the Verifier prompt.
            audit_status = classify_settings_transition(
                before_state,
                after_state,
                task,
            )

        records.append({
            "step": trace_record["step"],
            "action": action,
            "before_screenshot": before_name,
            "after_screenshot": after_name,
            "raw_output": raw_output,
            "predicted_status": predicted_status,
            "audit_status": audit_status,
            "correct": (
                predicted_status == audit_status
                if audit_status is not None
                else None
            ),
            "latency_seconds": latency_seconds,
            "error": error,
        })

    scored = [record for record in records if record["correct"] is not None]
    correct_count = sum(record["correct"] for record in scored)
    return {
        "source_result": str(result_path),
        "model_id": verifier.model_id,
        "mode": "shadow_only_no_policy_control",
        "task": task,
        "evaluated_transitions": len(records),
        "scored_transitions": len(scored),
        "correct_transitions": correct_count,
        "accuracy": correct_count / len(scored) if scored else None,
        "total_latency_seconds": sum(
            record["latency_seconds"] or 0.0 for record in records
        ),
        "records": records,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result_path = args.result.resolve()
    output_path = (
        args.output.resolve()
        if args.output
        else result_path.with_name("progress_shadow.json")
    )

    print("Source episode:", result_path)
    print("Mode: shadow only; no actions or recovery decisions")
    print("Loading model:", args.model_id)
    actor = QwenSettingsAgent(args.model_id)
    verifier = QwenProgressVerifier(actor)
    result = evaluate_trace(result_path, verifier)

    output_path.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    for record in result["records"]:
        print(
            f"Step {record['step']}: "
            f"predicted={record['predicted_status']} "
            f"audit={record['audit_status']} "
            f"correct={record['correct']}"
        )
    print("Accuracy:", result["accuracy"])
    print("Saved:", output_path)


if __name__ == "__main__":
    main()
