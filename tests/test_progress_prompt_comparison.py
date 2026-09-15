import tempfile
import unittest
from pathlib import Path

from src.progress_prompt_comparison import (
    compare_prompt_results,
    write_comparison_csv,
)


def result(prompt, predictions, references=None):
    references = references or ["progress", "regression", "no_effect"]
    return {
        "dataset": "pilot",
        "model_id": "model",
        "prompt_version": prompt,
        "records": [
            {
                "sample_id": f"sample-{index}",
                "task_id": "task",
                "reference_label": reference,
                "predicted_label": prediction,
            }
            for index, (reference, prediction) in enumerate(
                zip(references, predictions)
            )
        ],
    }


class ProgressPromptComparisonTests(unittest.TestCase):
    def test_counts_paired_outcomes_and_accuracy_delta(self):
        baseline = result(
            "p0",
            ["regression", "regression", "no_effect"],
        )
        candidate = result(
            "p1",
            ["progress", "progress", "progress"],
        )

        comparison = compare_prompt_results(baseline, candidate)

        self.assertAlmostEqual(comparison["baseline_accuracy"], 2 / 3)
        self.assertAlmostEqual(comparison["candidate_accuracy"], 1 / 3)
        self.assertAlmostEqual(comparison["accuracy_delta"], -1 / 3)
        self.assertEqual(comparison["prediction_change_count"], 3)
        self.assertEqual(comparison["outcome_counts"]["improved"], 1)
        self.assertEqual(comparison["outcome_counts"]["worsened"], 2)

    def test_rejects_different_sample_sets(self):
        baseline = result("p0", ["progress"])
        candidate = result("p1", ["progress", "regression"])

        with self.assertRaises(ValueError):
            compare_prompt_results(baseline, candidate)

    def test_rejects_reference_mismatch(self):
        baseline = result("p0", ["progress"], ["progress"])
        candidate = result("p1", ["progress"], ["regression"])

        with self.assertRaises(ValueError):
            compare_prompt_results(baseline, candidate)

    def test_writes_one_csv_row_per_sample(self):
        comparison = compare_prompt_results(
            result("p0", ["progress"]),
            result("p1", ["regression"]),
        )
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "comparison.csv"
            write_comparison_csv(comparison, output_path)
            content = output_path.read_text(encoding="utf-8")

        self.assertIn("baseline_prediction,candidate_prediction", content)
        self.assertIn("sample-0", content)


if __name__ == "__main__":
    unittest.main()
