import csv
import json


OUTCOMES = (
    "improved",
    "worsened",
    "unchanged_correct",
    "unchanged_wrong",
)


def _index_records(result, name):
    records = result.get("records", [])
    indexed = {record["sample_id"]: record for record in records}
    if len(indexed) != len(records):
        raise ValueError(f"{name} contains duplicate sample IDs")
    return indexed


def compare_prompt_results(baseline, candidate):
    if baseline.get("dataset") != candidate.get("dataset"):
        raise ValueError("Prompt results use different datasets")
    if baseline.get("model_id") != candidate.get("model_id"):
        raise ValueError("Prompt results use different models")

    baseline_records = _index_records(baseline, "baseline")
    candidate_records = _index_records(candidate, "candidate")
    if set(baseline_records) != set(candidate_records):
        raise ValueError("Prompt results contain different sample IDs")

    outcome_counts = {outcome: 0 for outcome in OUTCOMES}
    prediction_change_count = 0
    records = []

    for baseline_record in baseline.get("records", []):
        sample_id = baseline_record["sample_id"]
        candidate_record = candidate_records[sample_id]
        reference = baseline_record["reference_label"]
        if candidate_record["reference_label"] != reference:
            raise ValueError(f"Reference mismatch for {sample_id}")

        baseline_prediction = baseline_record["predicted_label"]
        candidate_prediction = candidate_record["predicted_label"]
        baseline_correct = baseline_prediction == reference
        candidate_correct = candidate_prediction == reference

        if not baseline_correct and candidate_correct:
            outcome = "improved"
        elif baseline_correct and not candidate_correct:
            outcome = "worsened"
        elif baseline_correct:
            outcome = "unchanged_correct"
        else:
            outcome = "unchanged_wrong"

        prediction_changed = baseline_prediction != candidate_prediction
        prediction_change_count += int(prediction_changed)
        outcome_counts[outcome] += 1
        records.append({
            "sample_id": sample_id,
            "task_id": baseline_record.get("task_id"),
            "reference_label": reference,
            "baseline_prediction": baseline_prediction,
            "candidate_prediction": candidate_prediction,
            "baseline_correct": baseline_correct,
            "candidate_correct": candidate_correct,
            "prediction_changed": prediction_changed,
            "outcome": outcome,
        })

    sample_count = len(records)
    baseline_correct_count = sum(
        record["baseline_correct"] for record in records
    )
    candidate_correct_count = sum(
        record["candidate_correct"] for record in records
    )
    return {
        "dataset": baseline.get("dataset"),
        "model_id": baseline.get("model_id"),
        "baseline_prompt_version": baseline.get("prompt_version"),
        "candidate_prompt_version": candidate.get("prompt_version"),
        "sample_count": sample_count,
        "baseline_accuracy": (
            baseline_correct_count / sample_count if sample_count else 0.0
        ),
        "candidate_accuracy": (
            candidate_correct_count / sample_count if sample_count else 0.0
        ),
        "accuracy_delta": (
            (candidate_correct_count - baseline_correct_count) / sample_count
            if sample_count
            else 0.0
        ),
        "prediction_change_count": prediction_change_count,
        "outcome_counts": outcome_counts,
        "records": records,
    }


def write_comparison_json(comparison, output_path):
    output_path.write_text(
        json.dumps(comparison, indent=2),
        encoding="utf-8",
    )


def write_comparison_csv(comparison, output_path):
    fieldnames = (
        "sample_id",
        "task_id",
        "reference_label",
        "baseline_prediction",
        "candidate_prediction",
        "baseline_correct",
        "candidate_correct",
        "prediction_changed",
        "outcome",
    )
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(comparison["records"])
