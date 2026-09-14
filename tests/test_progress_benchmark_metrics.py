import tempfile
import unittest
from pathlib import Path

from src.progress_benchmark_metrics import (
    PREDICTION_LABELS,
    summarize_progress_predictions,
    write_confusion_csv,
)


def record(sample_id, reference, prediction):
    return {
        "sample_id": sample_id,
        "reference_label": reference,
        "predicted_label": prediction,
    }


class ProgressBenchmarkMetricsTests(unittest.TestCase):
    def test_perfect_predictions_score_one(self):
        records = [
            record(label, label, label)
            for label in PREDICTION_LABELS
            if label != "uncertain"
        ]

        summary = summarize_progress_predictions(records)

        self.assertEqual(summary["accuracy"], 1.0)
        self.assertEqual(summary["macro_f1"], 1.0)
        self.assertEqual(summary["error_sample_ids"], [])

    def test_uncertain_is_preserved_as_an_incorrect_abstention(self):
        summary = summarize_progress_predictions([
            record("p1", "progress", "uncertain"),
            record("r1", "regression", "regression"),
        ])

        self.assertEqual(summary["accuracy"], 0.5)
        self.assertEqual(summary["uncertain_count"], 1)
        self.assertEqual(
            summary["confusion_matrix"]["progress"]["uncertain"],
            1,
        )
        self.assertEqual(summary["error_sample_ids"], ["p1"])

    def test_label_collapse_is_visible_in_prediction_distribution(self):
        records = [
            record("one", "progress", "regression"),
            record("two", "irrelevant", "regression"),
            record("three", "regression", "regression"),
        ]

        summary = summarize_progress_predictions(records)

        self.assertEqual(summary["prediction_distribution"]["regression"], 3)
        self.assertEqual(summary["correct_count"], 1)

    def test_confusion_csv_includes_uncertain_column(self):
        summary = summarize_progress_predictions([
            record("p1", "progress", "uncertain"),
        ])
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "matrix.csv"
            write_confusion_csv(summary["confusion_matrix"], output_path)
            content = output_path.read_text(encoding="utf-8")

        self.assertIn("uncertain", content)
        self.assertIn("progress,0,0,0,0,0,1", content)

    def test_unknown_reference_label_is_rejected(self):
        with self.assertRaises(ValueError):
            summarize_progress_predictions([
                record("bad", "changed", "progress"),
            ])


if __name__ == "__main__":
    unittest.main()
