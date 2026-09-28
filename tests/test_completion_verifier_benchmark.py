import json
import tempfile
import unittest
from pathlib import Path

from src.completion_verifier_benchmark import (
    benchmark_run,
    extract_completion_records,
    summarize_completion_records,
    wilson_interval,
)


def state(value="comfortable", pending=False):
    return {
        "saved": {"density": value},
        "has_unapplied_changes": pending,
        "confirmation_visible": False,
    }


def result(status="complete", after=None, final=None, arm="B"):
    return {
        "_result_path": "settings_clean_B/none/task/result.json",
        "ablation_arm": arm,
        "fault_mode": "none",
        "task": {
            "seed": 0,
            "task_id": "settings_000_density",
            "target_key": "density",
            "target_value": "compact",
        },
        "final_state": final or state("compact"),
        "trace": [{
            "step": 1,
            "action": {"type": "click"},
            "evaluator_state_after": after or state(),
            "verification": {"status": status, "latency_seconds": 1.0},
        }],
    }


class CompletionVerifierBenchmarkTests(unittest.TestCase):
    def test_uses_step_state_instead_of_successful_final_state(self):
        records = extract_completion_records([result()])

        self.assertEqual(records[0]["predicted_complete"], 1)
        self.assertEqual(records[0]["reference_complete"], 0)

    def test_default_arm_excludes_policy_controlled_c(self):
        records = extract_completion_records([result(), result(arm="C")])

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["arm"], "B")

    def test_confusion_and_qualification_gate(self):
        rows = [
            {"predicted_complete": 1, "reference_complete": 1},
            {"predicted_complete": 1, "reference_complete": 0},
            {"predicted_complete": 0, "reference_complete": 0},
            {"predicted_complete": 0, "reference_complete": 1},
        ]

        summary = summarize_completion_records(
            rows, minimum_precision=0.90, minimum_complete_predictions=2
        )

        self.assertEqual(
            summary["confusion_matrix"],
            {
                "true_positive": 1,
                "false_positive": 1,
                "true_negative": 1,
                "false_negative": 1,
            },
        )
        self.assertEqual(summary["completion_precision"], 0.5)
        self.assertFalse(summary["qualification_rule"]["point_threshold_pass"])
        self.assertFalse(summary["qualification_rule"]["conservative_gate_pass"])

    def test_no_positive_predictions_cannot_qualify(self):
        summary = summarize_completion_records(
            [{"predicted_complete": 0, "reference_complete": 0}],
            minimum_complete_predictions=1,
        )

        self.assertEqual(summary["completion_precision"], 0.0)
        self.assertFalse(summary["qualification_rule"]["conservative_gate_pass"])

    def test_wilson_interval_contains_observed_proportion(self):
        lower, upper = wilson_interval(9, 10)

        self.assertLess(lower, 0.9)
        self.assertGreater(upper, 0.9)

    def test_benchmark_writes_json_and_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir = root / "run"
            episode_dir = run_dir / "settings_clean_B" / "none" / "task"
            episode_dir.mkdir(parents=True)
            payload = result()
            payload.pop("_result_path")
            (episode_dir / "result.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )

            summary = benchmark_run(run_dir, root / "output")

            self.assertEqual(summary["overall"]["sample_count"], 1)
            self.assertTrue((root / "output" / "completion_verifier_summary.json").exists())
            self.assertTrue((root / "output" / "completion_verifier_records.csv").exists())


if __name__ == "__main__":
    unittest.main()
