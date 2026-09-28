"""Evaluate saved Settings verifier predictions against hidden state."""

import argparse
from pathlib import Path

from src.completion_verifier_benchmark import benchmark_run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--arms", nargs="+", default=["B"])
    parser.add_argument("--minimum-precision", type=float, default=0.90)
    parser.add_argument("--minimum-complete-predictions", type=int, default=10)
    args = parser.parse_args()

    if not 0.0 <= args.minimum_precision <= 1.0:
        parser.error("--minimum-precision must be between 0 and 1")
    if args.minimum_complete_predictions < 1:
        parser.error("--minimum-complete-predictions must be positive")

    output_dir = args.output_dir or args.run_dir / "completion_benchmark"
    summary = benchmark_run(
        args.run_dir,
        output_dir,
        arms=tuple(args.arms),
        minimum_precision=args.minimum_precision,
        minimum_complete_predictions=args.minimum_complete_predictions,
    )
    metrics = summary["overall"]
    matrix = metrics["confusion_matrix"]
    rule = metrics["qualification_rule"]
    print("Samples:", metrics["sample_count"])
    print("Confusion:", matrix)
    print("Completion precision:", f"{metrics['completion_precision']:.3f}")
    print("Completion recall:", f"{metrics['completion_recall']:.3f}")
    print("False-positive rate:", f"{metrics['false_positive_rate']:.3f}")
    print("Conservative control gate:", "PASS" if rule["conservative_gate_pass"] else "FAIL")
    print("Saved:", output_dir)


if __name__ == "__main__":
    main()
