import unittest

from src.recovery_policy import choose_recovery


class RecoveryPolicyTests(unittest.TestCase):
    def test_complete_finishes(self):
        self.assertEqual(choose_recovery("complete", False), "finish")

    def test_no_effect_retries_once(self):
        self.assertEqual(choose_recovery("no_effect", False), "retry")

    def test_second_no_effect_replans(self):
        self.assertEqual(choose_recovery("no_effect", True), "replan")

    def test_changed_replans(self):
        self.assertEqual(choose_recovery("changed", False), "replan")

    def test_uncertain_replans(self):
        self.assertEqual(choose_recovery("uncertain", False), "replan")


if __name__ == "__main__":
    unittest.main()
