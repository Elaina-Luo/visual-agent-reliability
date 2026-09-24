import tempfile
import unittest
from pathlib import Path

from run_settings_ablation_batch import (
    build_plan,
    parse_seeds,
    prepare_run_dir,
    result_path,
    write_or_validate_manifest,
)


class SettingsAblationBatchTests(unittest.TestCase):
    def test_parses_ranges_lists_and_removes_duplicates(self):
        self.assertEqual(parse_seeds("0:3,2,5:8"), [0, 1, 2, 5, 6, 7])

    def test_rejects_bad_or_negative_seeds(self):
        for value in ("", "0:", "3:3", "-1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_seeds(value)

    def test_result_path_uses_arm_specific_directory(self):
        root = Path("runs") / "pilot"
        self.assertEqual(
            result_path(root, "A", "none", "task"),
            root / "settings_agent" / "none" / "task" / "result.json",
        )
        self.assertEqual(
            result_path(root, "C", "none", "task"),
            root / "settings_clean_C" / "none" / "task" / "result.json",
        )

    def test_resume_skips_only_completed_results(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            completed = result_path(
                run_dir, "A", "none", "settings_000_density"
            )
            completed.parent.mkdir(parents=True)
            completed.write_text("{}", encoding="utf-8")

            plan = build_plan([0], ["none"], ["A", "B", "C"], run_dir, True)

            self.assertEqual([item["arm"] for item in plan], ["B", "C"])

    def test_existing_run_requires_explicit_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_run_dir(root, "pilot")
            with self.assertRaises(FileExistsError):
                prepare_run_dir(root, "pilot")
            self.assertEqual(prepare_run_dir(root, "pilot", True), root / "pilot")

    def test_resume_rejects_configuration_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            manifest = {
                "run_id": "pilot", "seeds": [0], "fault_modes": ["none"],
                "arms": ["A"], "max_steps": 8, "model_id": None,
                "created_at_utc": "first",
            }
            write_or_validate_manifest(run_dir, manifest)
            changed = {**manifest, "seeds": [0, 1], "created_at_utc": "second"}
            with self.assertRaises(ValueError):
                write_or_validate_manifest(run_dir, changed, True)

    def test_resume_preserves_original_manifest_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            manifest = {
                "run_id": "pilot", "seeds": [0], "fault_modes": ["none"],
                "arms": ["A"], "max_steps": 8, "model_id": None,
                "created_at_utc": "first",
            }
            write_or_validate_manifest(run_dir, manifest)
            resumed = write_or_validate_manifest(
                run_dir, {**manifest, "created_at_utc": "second"}, True
            )
            self.assertEqual(resumed["created_at_utc"], "first")


if __name__ == "__main__":
    unittest.main()
