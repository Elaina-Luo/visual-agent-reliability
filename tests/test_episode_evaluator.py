import unittest

from src.episode_evaluator import evaluate_episode


class EpisodeEvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.task = {"target_key": "density", "target_value": "compact"}
        self.completed_state = {
            "saved": {"density": "compact"},
            "has_unapplied_changes": False,
            "confirmation_visible": False,
        }

    def test_separates_completed_state_from_missing_finish(self):
        result = evaluate_episode(
            self.completed_state,
            self.task,
            "budget_exhausted",
        )

        self.assertTrue(result["task_state_success"])
        self.assertFalse(result["agent_terminated_correctly"])
        self.assertFalse(result["success"])

    def test_full_success_requires_state_and_finish(self):
        result = evaluate_episode(
            self.completed_state,
            self.task,
            "agent_finish",
        )

        self.assertTrue(result["task_state_success"])
        self.assertTrue(result["agent_terminated_correctly"])
        self.assertTrue(result["success"])

    def test_finish_does_not_hide_incomplete_state(self):
        incomplete_state = {
            **self.completed_state,
            "saved": {"density": "comfortable"},
        }
        result = evaluate_episode(
            incomplete_state,
            self.task,
            "agent_finish",
        )

        self.assertFalse(result["task_state_success"])
        self.assertTrue(result["agent_terminated_correctly"])
        self.assertFalse(result["success"])

    def test_verifier_can_terminate_completed_episode(self):
        result = evaluate_episode(
            self.completed_state,
            self.task,
            "verifier_complete",
        )

        self.assertTrue(result["task_state_success"])
        self.assertTrue(result["agent_terminated_correctly"])
        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()
