"""Offline binary benchmark for Settings completion predictions."""

import csv
import json
import math
from pathlib import Path

from src.episode_evaluator import task_state_succeeded
from src.settings_ablation_summary import load_episode_results


def safe_divide(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def wilson_interval(successes, trials, z=1.959963984540054):
    """Return a two-sided 95% Wilson interval for a binomial proportion."""
    if trials == 0:
        return [0.0, 0.0]
    proportion = successes / trials
    denominator = 1 + z * z / trials
    center = (proportion + z * z / (2 * trials)) / denominator
    margin = (
        z
        * math.sqrt(
            proportion * (1 - proportion) / trials
            + z * z / (4 * trials * trials)
        )
        / denominator
    )
    return [max(0.0, center - margin), min(1.0, center + margin)]


def _reference_state(record, result):
    # State immediately after the audited action is the primary reference.
    # Finish is a no-op and older traces may omit its state, so before/final
    # state are safe fallbacks in that order.
    return (
        record.get("evaluator_state_after")
        or record.get("evaluator_state_before")
        or result.get("final_state")
    )


def extract_completion_records(results, arms=("B",)):
    """Convert saved episode traces into binary completion examples."""
    allowed_arms = set(arms)
    records = []
    for result in results:
        arm = result.get("ablation_arm")
        if arm not in allowed_arms:
            continue
        task = result["task"]
        for trace_index, trace_record in enumerate(result.get("trace", [])):
            verification = trace_record.get("verification")
            if not verification:
                continue
            state = _reference_state(trace_record, result)
            if state is None:
                raise ValueError(
                    f"Missing evaluator state for {task['task_id']} "
                    f"trace index {trace_index}"
                )
            status = verification.get("status", "uncertain")
            reference_complete = task_state_succeeded(state, task)
            predicted_complete = status == "complete"
            records.append({
                "sample_id": (
                    f"{arm}:{result['fault_mode']}:{task['task_id']}:"
                    f"{trace_record.get('step', trace_index + 1)}"
                ),
                "task_id": task["task_id"],
                "seed": task["seed"],
                "fault_mode": result["fault_mode"],
                "arm": arm,
                "step": trace_record.get("step", trace_index + 1),
                "action_type": (trace_record.get("action") or {}).get("type"),
                "verifier_status": status,
                "predicted_complete": int(predicted_complete),
                "reference_complete": int(reference_complete),
                "correct": int(predicted_complete == reference_complete),
                "latency_seconds": verification.get("latency_seconds"),
                "result_path": result.get("_result_path", ""),
            })
    return records


def summarize_completion_records(
    records,
    minimum_precision=0.90,
    minimum_complete_predictions=10,
):
    true_positive = sum(
        row["predicted_complete"] and row["reference_complete"]
        for row in records
    )
    false_positive = sum(
        row["predicted_complete"] and not row["reference_complete"]
        for row in records
    )
    true_negative = sum(
        not row["predicted_complete"] and not row["reference_complete"]
        for row in records
    )
    false_negative = sum(
        not row["predicted_complete"] and row["reference_complete"]
        for row in records
    )
    predicted_positive = true_positive + false_positive
    reference_positive = true_positive + false_negative
    reference_negative = true_negative + false_positive
    precision = safe_divide(true_positive, predicted_positive)
    precision_interval = wilson_interval(true_positive, predicted_positive)
    recall = safe_divide(true_positive, reference_positive)
    false_positive_rate = safe_divide(false_positive, reference_negative)
    accuracy = safe_divide(true_positive + true_negative, len(records))
    enough_predictions = predicted_positive >= minimum_complete_predictions
    point_threshold_pass = enough_predictions and precision >= minimum_precision
    conservative_gate_pass = (
        point_threshold_pass
        and precision_interval[0] >= minimum_precision
    )
    return {
        "sample_count": len(records),
        "confusion_matrix": {
            "true_positive": true_positive,
            "false_positive": false_positive,
            "true_negative": true_negative,
            "false_negative": false_negative,
        },
        "predicted_complete_count": predicted_positive,
        "reference_complete_count": reference_positive,
        "completion_precision": precision,
        "completion_precision_wilson_95": precision_interval,
        "completion_recall": recall,
        "false_positive_rate": false_positive_rate,
        "accuracy": accuracy,
        "qualification_rule": {
            "minimum_precision": minimum_precision,
            "minimum_complete_predictions": minimum_complete_predictions,
            "enough_complete_predictions": enough_predictions,
            "point_threshold_pass": point_threshold_pass,
            "conservative_gate_pass": conservative_gate_pass,
        },
    }


def _group_summaries(records, minimum_precision, minimum_predictions):
    fault_modes = sorted({row["fault_mode"] for row in records})
    return {
        fault_mode: summarize_completion_records(
            [row for row in records if row["fault_mode"] == fault_mode],
            minimum_precision,
            minimum_predictions,
        )
        for fault_mode in fault_modes
    }


def _write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def benchmark_run(
    run_dir,
    output_dir,
    arms=("B",),
    minimum_precision=0.90,
    minimum_complete_predictions=10,
):
    run_dir = Path(run_dir)
    output_dir = Path(output_dir)
    results = load_episode_results(run_dir)
    records = extract_completion_records(results, arms=arms)
    if not records:
        raise ValueError("No verification records found for the selected arms")
    summary = {
        "source_run_id": run_dir.name,
        "mode": "offline_shadow_no_policy_control",
        "arms": list(arms),
        "reference": "hidden evaluator state immediately after each action",
        "overall": summarize_completion_records(
            records,
            minimum_precision,
            minimum_complete_predictions,
        ),
        "by_fault_mode": _group_summaries(
            records,
            minimum_precision,
            minimum_complete_predictions,
        ),
        "records": records,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "completion_verifier_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    _write_csv(output_dir / "completion_verifier_records.csv", records)
    return summary
