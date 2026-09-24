import unittest

from src.evidence_gated_policy import (
    can_replan,
    evidence_gated_status,
    should_retry_no_effect,
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


if __name__ == "__main__":
    unittest.main()
