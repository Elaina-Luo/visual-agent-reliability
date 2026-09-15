import unittest

from src.progress_verifier_parser import (
    parse_progress_verification,
)
from src.progress_verifier_prompt import (
    P1_PROMPT_VERSION,
    build_progress_verifier_prompt,
)


class ProgressVerifierTests(unittest.TestCase):
    def test_prompt_distinguishes_goal_direction(self):
        prompt = build_progress_verifier_prompt(
            "Turn off Sound alerts and save the changes.",
            {"type": "click", "x": 877, "y": 298},
        )

        self.assertIn("Judge direction relative", prompt)
        self.assertIn("to the stated goal", prompt)
        self.assertIn("unrelated setting is irrelevant", prompt)
        self.assertIn("requested state is regression", prompt)

    def test_prompt_requires_saved_completion(self):
        prompt = build_progress_verifier_prompt(
            "Select Compact density and save the changes.",
            {"type": "click", "x": 849, "y": 582},
        )

        self.assertIn("completed and\n  saved", prompt)
        self.assertIn("confirmation dialog is progress", prompt)
        self.assertIn("task is not complete", prompt)

    def test_p1_uses_explicit_goal_state_comparison(self):
        prompt = build_progress_verifier_prompt(
            "Turn off Sound alerts and save the changes.",
            {"type": "click", "x": 877, "y": 298},
            prompt_version=P1_PROMPT_VERSION,
        )

        self.assertIn("Decompose the goal", prompt)
        self.assertIn("satisfied in BEFORE", prompt)
        self.assertIn("satisfied in AFTER", prompt)
        self.assertIn("priority order", prompt)
        self.assertIn("context only", prompt)

    def test_unknown_prompt_version_is_rejected(self):
        with self.assertRaises(ValueError):
            build_progress_verifier_prompt(
                "Save the changes.",
                {"type": "click", "x": 1, "y": 2},
                prompt_version="unknown",
            )

    def test_parses_each_valid_status(self):
        statuses = (
            "complete",
            "progress",
            "regression",
            "irrelevant",
            "no_effect",
            "uncertain",
        )
        for status in statuses:
            with self.subTest(status=status):
                self.assertEqual(
                    parse_progress_verification(
                        f'{{"status": "{status}"}}'
                    ),
                    {"status": status},
                )

    def test_extracts_one_json_object_from_code_fence(self):
        self.assertEqual(
            parse_progress_verification(
                '```json\n{"status": "progress"}\n```'
            ),
            {"status": "progress"},
        )

    def test_rejects_unknown_status(self):
        with self.assertRaises(ValueError):
            parse_progress_verification('{"status": "changed"}')

    def test_rejects_extra_fields(self):
        with self.assertRaises(ValueError):
            parse_progress_verification(
                '{"status": "progress", "evidence": "toggle moved"}'
            )

    def test_rejects_multiple_decisions(self):
        with self.assertRaises(ValueError):
            parse_progress_verification(
                '{"status": "progress"}; {"status": "complete"}'
            )

    def test_rejects_missing_json(self):
        with self.assertRaises(ValueError):
            parse_progress_verification("The action helped.")


if __name__ == "__main__":
    unittest.main()
