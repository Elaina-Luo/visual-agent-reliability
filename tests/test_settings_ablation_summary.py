import json
import tempfile
import unittest
from pathlib import Path

from src.settings_ablation_summary import (
    aggregate_rows,
    episode_row,
    paired_rows,
    summarize_run,
)


def result(arm="C", success=False, seed=0, fault="none"):
    task = {
        "seed": seed,
        "task_id": f"settings_{seed:03d}_density",
        "target_key": "density",
        "target_value": "compact",
    }
    incomplete = {
        "saved": {"density": "comfortable"},
        "has_unapplied_changes": False,
        "confirmation_visible": False,
    }
    complete = {
        "saved": {"density": "compact"},
        "has_unapplied_changes": False,
        "confirmation_visible": False,
    }
    return {
        "_result_path": f"{arm}/{fault}/{seed}/result.json",
        "ablation_arm": arm,
        "fault_mode": fault,
        "task": task,
        "task_state_success": success,
        "agent_terminated_correctly": success,
        "termination_reason": "agent_finish" if success else "verifier_complete",
        "retry_count": 1 if arm == "C" else 0,
        "steps": 4,
        "action_count": 4,
        "click_count": 4,
        "actor_latency_seconds": 8.0,
        "verifier_latency_seconds": 4.0 if arm != "A" else 0.0,
        "final_state": complete if success else incomplete,
        "trace": [{
            "verification": {"status": "complete"},
            "evaluator_state_after": complete if success else incomplete,
        }] if arm != "A" else [],
    }


class SettingsAblationSummaryTests(unittest.TestCase):
    def test_episode_marks_false_complete_prediction_and_termination(self):
        row = episode_row(result())
        self.assertEqual(row["false_completion_termination"], 1)
        self.assertEqual(row["verifier_complete_predictions"], 1)
        self.assertEqual(row["false_complete_predictions"], 1)

    def test_correct_complete_is_not_false_positive(self):
        row = episode_row(result(success=True))
        self.assertEqual(row["false_completion_termination"], 0)
        self.assertEqual(row["false_complete_predictions"], 0)

    def test_aggregates_rates_and_means(self):
        rows = [episode_row(result(success=False)), episode_row(result(success=True, seed=1))]
        aggregate = aggregate_rows(rows)[0]
        self.assertEqual(aggregate["episode_count"], 2)
        self.assertEqual(aggregate["task_state_success_rate"], 0.5)
        self.assertEqual(aggregate["false_completion_termination_rate"], 0.5)
        self.assertEqual(aggregate["mean_retry_count"], 1.0)
        self.assertEqual(aggregate["false_complete_predictions"], 1)

    def test_paired_rows_align_arms_by_seed_and_fault(self):
        rows = [
            episode_row(result("A", True)),
            episode_row(result("B", True)),
            episode_row(result("C", False)),
        ]
        pair = paired_rows(rows)[0]
        self.assertEqual(pair["A_task_state_success"], 1)
        self.assertEqual(pair["C_task_state_success"], 0)
        self.assertEqual(pair["C_minus_A_task_state_success"], -1)

    def test_summarize_writes_all_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            path = run_dir / "settings_clean_C" / "none" / "task"
            path.mkdir(parents=True)
            payload = result()
            payload.pop("_result_path")
            (path / "result.json").write_text(json.dumps(payload), encoding="utf-8")

            summary = summarize_run(run_dir)

            self.assertEqual(summary["episode_count"], 1)
            for name in ("episodes.csv", "aggregate.csv", "paired.csv", "summary.json"):
                self.assertTrue((run_dir / name).exists())


if __name__ == "__main__":
    unittest.main()
