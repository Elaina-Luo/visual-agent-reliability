import unittest

from src.completion_gate import gate_completion, parse_completion_gate
from src.completion_gate_prompt import build_completion_gate_prompt


class CompletionGateTests(unittest.TestCase):
    def test_parses_pending_action_true(self):
        self.assertEqual(
            parse_completion_gate('{"pending_action": true}'),
            {"pending_action": True},
        )

    def test_parses_pending_action_false(self):
        self.assertEqual(
            parse_completion_gate('{"pending_action": false}'),
            {"pending_action": False},
        )

    def test_rejects_non_boolean_decision(self):
        with self.assertRaises(ValueError):
            parse_completion_gate('{"pending_action": "true"}')

    def test_rejects_multiple_decisions(self):
        with self.assertRaises(ValueError):
            parse_completion_gate(
                '{"pending_action": true}; {"pending_action": false}'
            )

    def test_pending_action_blocks_complete(self):
        self.assertEqual(gate_completion("complete", True), "changed")

    def test_no_pending_action_allows_complete(self):
        self.assertEqual(gate_completion("complete", False), "complete")

    def test_non_complete_status_bypasses_gate_decision(self):
        self.assertEqual(gate_completion("changed", False), "changed")

    def test_prompt_treats_open_dialog_as_pending(self):
        prompt = build_completion_gate_prompt(
            "Select Compact density and save the changes."
        )

        self.assertIn("a modal or dialog is open", prompt)
        self.assertIn("When evidence is insufficient, use true", prompt)


if __name__ == "__main__":
    unittest.main()
