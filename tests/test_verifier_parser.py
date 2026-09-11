import unittest

from src.verifier_parser import parse_verification
from src.verifier_prompt import build_verifier_prompt


class ParseVerificationTests(unittest.TestCase):
    def test_prompt_rejects_pending_confirmation_as_complete(self):
        prompt = build_verifier_prompt(
            "Select Compact density and save the changes.",
            {"type": "click", "x": 849, "y": 582},
        )

        self.assertIn("confirmation dialog is changed, not complete", prompt)
        self.assertIn("pending user action", prompt)

    def test_parses_each_valid_status(self):
        for status in ("complete", "changed", "no_effect", "uncertain"):
            with self.subTest(status=status):
                self.assertEqual(
                    parse_verification(f'{{"status": "{status}"}}'),
                    {"status": status},
                )

    def test_extracts_one_json_object_from_code_fence(self):
        self.assertEqual(
            parse_verification('```json\n{"status": "changed"}\n```'),
            {"status": "changed"},
        )

    def test_rejects_unknown_status(self):
        with self.assertRaises(ValueError):
            parse_verification('{"status": "success"}')

    def test_rejects_extra_fields(self):
        with self.assertRaises(ValueError):
            parse_verification(
                '{"status": "changed", "evidence": "toggle moved"}'
            )

    def test_rejects_multiple_decisions(self):
        with self.assertRaises(ValueError):
            parse_verification(
                '{"status": "changed"}; {"status": "complete"}'
            )

    def test_rejects_missing_json(self):
        with self.assertRaises(ValueError):
            parse_verification("The action worked.")


if __name__ == "__main__":
    unittest.main()
