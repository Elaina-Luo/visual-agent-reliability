import argparse
import json
from pathlib import Path

from src.progress_prompt_comparison import (
    compare_prompt_results,
    write_comparison_csv,
    write_comparison_json,
)


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_RESULTS_DIR = (
    PROJECT_DIR / "artifacts" / "progress_transition_dataset_v1"
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_RESULTS_DIR / "progress_benchmark_p0.json",
    )
    parser.add_argument(
        "--candidate",
        type=Path,
        default=DEFAULT_RESULTS_DIR / "progress_benchmark_p1.json",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=DEFAULT_RESULTS_DIR / "progress_prompt_comparison.json",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=DEFAULT_RESULTS_DIR / "progress_prompt_comparison.csv",
    )
    args = parser.parse_args()

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    comparison = compare_prompt_results(baseline, candidate)

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    write_comparison_json(comparison, args.output_json)
    write_comparison_csv(comparison, args.output_csv)

    print("Baseline:", comparison["baseline_prompt_version"])
    print("Candidate:", comparison["candidate_prompt_version"])
    print("Samples:", comparison["sample_count"])
    print(f"Baseline accuracy: {comparison['baseline_accuracy']:.4f}")
    print(f"Candidate accuracy: {comparison['candidate_accuracy']:.4f}")
    print(f"Accuracy delta: {comparison['accuracy_delta']:+.4f}")
    print("Prediction changes:", comparison["prediction_change_count"])
    for outcome, count in comparison["outcome_counts"].items():
        print(f"{outcome}: {count}")
    print("Changed predictions:")
    for record in comparison["records"]:
        if record["prediction_changed"]:
            print(
                f"- {record['sample_id']}: "
                f"{record['baseline_prediction']} -> "
                f"{record['candidate_prediction']} "
                f"({record['outcome']})"
            )
    print("Saved JSON:", args.output_json)
    print("Saved CSV:", args.output_csv)


if __name__ == "__main__":
    main()
