import unittest

from environment.settings_tasks import generate_settings_task
from src.progress_transition_dataset import (
    PROGRESS_LABELS,
    build_transition_specs,
    label_counts,
    regression_selector,
    unrelated_selector,
    validate_balanced_specs,
)


class ProgressTransitionDatasetTests(unittest.TestCase):
    def setUp(self):
        self.tasks = [generate_settings_task(seed) for seed in range(3)]

    def test_builds_balanced_fifteen_sample_dataset(self):
        specs = build_transition_specs(self.tasks)

        self.assertEqual(len(specs), 15)
        expected = {label: 3 for label in PROGRESS_LABELS}
        self.assertEqual(label_counts(specs), expected)
        self.assertEqual(validate_balanced_specs(specs), expected)

    def test_sample_ids_are_unique(self):
        specs = build_transition_specs(self.tasks)
        self.assertEqual(
            len({spec["sample_id"] for spec in specs}),
            len(specs),
        )

    def test_density_regression_selects_comfortable(self):
        self.assertIn(
            'data-value="comfortable"',
            regression_selector(self.tasks[0]),
        )

    def test_boolean_regression_reuses_target_toggle(self):
        self.assertIn(
            'data-testid="sound-alerts"',
            regression_selector(self.tasks[1]),
        )

    def test_appearance_irrelevant_segment_differs_from_current(self):
        selector = unrelated_selector(
            self.tasks[0],
            {"theme": "light"},
        )
        self.assertIn('data-value="dark"', selector)

    def test_boolean_irrelevant_control_is_not_target(self):
        selector = unrelated_selector(
            self.tasks[1],
            self.tasks[1]["initial_state"],
        )
        self.assertIn('data-key="push_notifications"', selector)
        self.assertNotIn("sound_alerts", selector)


if __name__ == "__main__":
    unittest.main()
