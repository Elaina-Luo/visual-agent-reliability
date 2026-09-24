import tempfile
import unittest

from run_settings_evidence_gated_agent_v22 import run_episode
from src.action_aware_feedback import build_action_aware_recovery_context

from test_evidence_gated_agent_v21 import Actor, Page, TASK, Verifier


class EvidenceGatedAgentV22Tests(unittest.TestCase):
    def test_changed_feedback_adds_save_guidance_only_when_enabled(self):
        history = [{"action": {"type": "click", "x": 20, "y": 20},
                    "status": "changed"}]
        baseline = ""
        guided = build_action_aware_recovery_context(history)

        self.assertNotIn("ACTION-AWARE RECOVERY", baseline)
        self.assertIn("ACTION-AWARE RECOVERY", guided)
        self.assertIn("Save changes", guided)
        self.assertIn("Do not immediately click", guided)
        self.assertIn("same control again", guided)

    def test_repeat_blocked_feedback_says_proposal_was_not_executed(self):
        prompt = build_action_aware_recovery_context([{
                "action": {"type": "click", "x": 20, "y": 20},
                "status": "repeat_blocked",
            }])

        self.assertIn("was blocked and was not executed", prompt)
        self.assertIn("next distinct task step", prompt)

    def test_v22_enables_guidance_and_uses_separate_result_namespace(self):
        actor = Actor([{"type": "finish"}])
        with tempfile.TemporaryDirectory() as directory:
            result = run_episode(
                Page(), actor, Verifier(), TASK, max_steps=2,
                output_root=directory,
            )

        self.assertTrue(actor.inputs[0]["action_aware_recovery"])
        self.assertEqual(result["strategy"], "evidence_gated_recovery_v2_2")


if __name__ == "__main__":
    unittest.main()
