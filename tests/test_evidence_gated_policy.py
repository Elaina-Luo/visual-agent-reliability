import unittest

from src.evidence_gated_policy import (
    can_replan,
    can_retry_invalid,
    completion_evidence_confirmed,
    evidence_gated_status,
    should_retry_no_effect,
    update_completion_sequence,
)


class EvidenceGatedPolicyTests(unittest.TestCase):
    def test_complete_cannot_override_identical_images(self):
        self.assertEqual(evidence_gated_status("complete", 0.0), "no_effect")

    def test_complete_with_visual_change_is_only_a_candidate(self):
        self.assertEqual(
            evidence_gated_status("complete", 0.01),
            "completion_candidate",
        )

    def test_visual_change_overrides_no_effect(self):
        self.assertEqual(evidence_gated_status("no_effect", 0.01), "changed")

    def test_retry_is_bounded_and_requires_budget(self):
        self.assertTrue(should_retry_no_effect("no_effect", False, 1))
        self.assertFalse(should_retry_no_effect("no_effect", True, 1))
        self.assertFalse(should_retry_no_effect("no_effect", False, 0))

    def test_replan_limit_is_strict(self):
        self.assertTrue(can_replan(2, 3))
        self.assertFalse(can_replan(3, 3))

    def test_two_distinct_consecutive_candidates_confirm_completion(self):
        first = {"type": "click", "x": 850, "y": 582}
        second = {"type": "click", "x": 590, "y": 396}
        sequence = update_completion_sequence([], first, "completion_candidate")
        sequence = update_completion_sequence(
            sequence, second, "completion_candidate"
        )
        self.assertTrue(completion_evidence_confirmed(sequence))

    def test_same_action_or_interruption_does_not_confirm_completion(self):
        action = {"type": "click", "x": 850, "y": 582}
        sequence = update_completion_sequence([], action, "completion_candidate")
        sequence = update_completion_sequence(
            sequence, action, "completion_candidate"
        )
        self.assertFalse(completion_evidence_confirmed(sequence))
        self.assertEqual(update_completion_sequence(sequence, action, "changed"), [])

    def test_invalid_replan_limit_is_strict(self):
        self.assertTrue(can_retry_invalid(2, 3))
        self.assertFalse(can_retry_invalid(3, 3))


if __name__ == "__main__":
    unittest.main()
