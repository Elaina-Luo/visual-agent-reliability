"""Run a completion-only prompt on frozen shadow-verification screenshots."""

import argparse
import json
from pathlib import Path

from PIL import Image

from src.completion_gate import parse_completion_gate
from src.completion_gate_prompt import (
    COMPLETION_GATE_PROMPT_VERSIONS,
    EVIDENCE_PROMPT_VERSION,
)
from src.completion_verifier_benchmark import (
    reference_state_for_record,
    summarize_completion_records,
)
from src.episode_evaluator import task_state_succeeded
from src.settings_ablation_summary import load_episode_results


DEFAULT_COMPLETION_MODEL_ID = "Qwen/Qwen2.5-VL-3B-Instruct"


def load_rgb(path):
    with Image.open(path) as image:
        return image.convert("RGB")


def build_samples(run_dir, arms=("B",)):
    run_dir = Path(run_dir)
    allowed_arms = set(arms)
    samples = []
    for result in load_episode_results(run_dir):
        if result.get("ablation_arm") not in allowed_arms:
            continue
        episode_dir = (run_dir / result["_result_path"]).parent
        for index, record in enumerate(result.get("trace", [])):
            if not record.get("verification"):
                continue
            image_name = record.get("observation_after") or record.get("observation")
            if not image_name:
                continue
            samples.append({
                "sample_id": (
                    f"{result['ablation_arm']}:{result['fault_mode']}:"
                    f"{result['task']['task_id']}:"
                    f"{record.get('step', index + 1)}"
                ),
                "image_path": episode_dir / image_name,
                "result": result,
                "trace_record": record,
            })
    return samples


def _load_checkpoint(output_path, source_run_id, model_id, prompt_version):
    if not output_path.exists():
        return []
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    expected = {
        "source_run_id": source_run_id,
        "model_id": model_id,
        "prompt_version": prompt_version,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ValueError(f"Checkpoint {key} does not match this run")
    return payload.get("records", [])


def _result_payload(run_dir, gate, records):
    return {
        "source_run_id": Path(run_dir).name,
        "model_id": gate.model_id,
        "prompt_version": gate.prompt_version,
        "mode": "offline_shadow_no_policy_control",
        "reference": "hidden evaluator state immediately after each action",
        "metrics": summarize_completion_records(records),
        "total_latency_seconds": sum(
            row.get("latency_seconds") or 0.0 for row in records
        ),
        "records": records,
    }


def evaluate_samples(run_dir, gate, output_path, resume=False, arms=("B",)):
    run_dir = Path(run_dir)
    output_path = Path(output_path)
    samples = build_samples(run_dir, arms=arms)
    if not samples:
        raise ValueError(
            "No B-arm verification samples found. The run directory must "
            "contain settings_clean_B episode result.json files and screenshots."
        )
    missing_images = [
        sample["image_path"]
        for sample in samples
        if not sample["image_path"].is_file()
    ]
    if missing_images:
        raise FileNotFoundError(
            f"Missing {len(missing_images)} benchmark screenshots; "
            f"first missing path: {missing_images[0]}"
        )
    records = (
        _load_checkpoint(
            output_path, run_dir.name, gate.model_id, gate.prompt_version
        )
        if resume
        else []
    )
    completed_ids = {row["sample_id"] for row in records}

    for sample in samples:
        if sample["sample_id"] in completed_ids:
            continue
        image = load_rgb(sample["image_path"])
        raw_output = None
        latency_seconds = None
        try:
            raw_output, latency_seconds = gate.check(
                image=image,
                goal=sample["result"]["task"]["goal"],
            )
            pending_action = parse_completion_gate(raw_output)["pending_action"]
            error = None
        except Exception as exception:
            pending_action = True
            error = f"{type(exception).__name__}: {exception}"

        # Hidden state is read only after inference and never enters the prompt.
        state = reference_state_for_record(
            sample["trace_record"], sample["result"]
        )
        reference_complete = task_state_succeeded(
            state, sample["result"]["task"]
        )
        predicted_complete = not pending_action
        row = {
            "sample_id": sample["sample_id"],
            "task_id": sample["result"]["task"]["task_id"],
            "seed": sample["result"]["task"]["seed"],
            "fault_mode": sample["result"]["fault_mode"],
            "arm": sample["result"]["ablation_arm"],
            "step": sample["trace_record"].get("step"),
            "predicted_complete": int(predicted_complete),
            "reference_complete": int(reference_complete),
            "correct": int(predicted_complete == reference_complete),
            "raw_output": raw_output,
            "latency_seconds": latency_seconds,
            "error": error,
        }
        records.append(row)
        output_path.write_text(
            json.dumps(_result_payload(run_dir, gate, records), indent=2),
            encoding="utf-8",
        )
        print(
            f"{len(records):03d}/{len(samples)} {row['sample_id']} "
            f"predicted={predicted_complete} reference={reference_complete}"
        )

    payload = _result_payload(run_dir, gate, records)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main():
    from src.qwen_completion_gate import QwenCompletionGate

    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-id", default=DEFAULT_COMPLETION_MODEL_ID)
    parser.add_argument(
        "--prompt-version",
        choices=COMPLETION_GATE_PROMPT_VERSIONS,
        default=EVIDENCE_PROMPT_VERSION,
    )
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    samples = build_samples(args.run_dir)
    if not samples:
        parser.error(
            "No B-arm samples found. Upload and extract the complete run "
            "archive, including settings_clean_B result.json and PNG files."
        )
    missing_count = sum(
        not sample["image_path"].is_file() for sample in samples
    )
    if missing_count:
        parser.error(f"The input run is missing {missing_count} screenshots")
    print("Mode: offline shadow; no Agent actions or policy control")
    print("Prompt:", args.prompt_version)
    print("Frozen samples:", len(samples))
    print("Loading model:", args.model_id)
    gate = QwenCompletionGate.from_pretrained(
        args.model_id,
        prompt_version=args.prompt_version,
    )
    result = evaluate_samples(
        args.run_dir, gate, args.output, resume=args.resume
    )
    metrics = result["metrics"]
    print("Evaluated samples:", metrics["sample_count"])
    print("Completion precision:", metrics["completion_precision"])
    print("Completion recall:", metrics["completion_recall"])
    print("False-positive rate:", metrics["false_positive_rate"])
    print(
        "Conservative control gate:",
        "PASS" if metrics["qualification_rule"]["conservative_gate_pass"] else "FAIL",
    )
    print("Saved:", args.output)


if __name__ == "__main__":
    main()
