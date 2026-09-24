import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from run_settings_evidence_gated_agent_v24 import run_episode
from src.constrained_recovery import select_actor_goal

from test_evidence_gated_agent_v21 import Actor, Page, TASK, Verifier


class EvidenceGatedAgentV24Tests(unittest.TestCase):
    def test_subgoal_activates_only_after_repeat_block(self):
        history = [{"status": "changed"}]
        self.assertEqual(select_actor_goal("Original", history, True), "Original")
        history.append({"status": "repeat_blocked"})

        goal = select_actor_goal("Original", history, True)

        self.assertIn("RECOVERY SUBGOAL", goal)
        self.assertIn("Save changes", goal)
        self.assertIn("Original task: Original", goal)

    def test_disabled_subgoal_preserves_original_goal(self):
        history = [{"status": "repeat_blocked"}]
        self.assertEqual(select_actor_goal("Original", history, False), "Original")

    def test_blocked_repeat_causes_one_constrained_actor_turn(self):
        repeated = {"type": "click", "x": 20, "y": 20}
        next_action = {"type": "click", "x": 50, "y": 50}
        actor = Actor([repeated, repeated, next_action, {"type": "finish"}])

        def execute(*args, **kwargs):
            action = args[3]
            return ({
                "action": action,
                "verification_status": "changed",
                "verification_vlm_status": "changed",
            }, Image.new("RGB", (64, 64)), "after.png")

        with tempfile.TemporaryDirectory() as directory, patch(
            "run_settings_evidence_gated_agent_v21.execute_verified_click_v2",
            side_effect=execute,
        ):
            result = run_episode(
                Page(), actor, Verifier(), TASK, max_steps=3,
                output_root=directory,
            )

        self.assertEqual(result["blocked_replans"], 1)
        self.assertEqual(actor.inputs[0]["goal"], TASK["goal"])
        self.assertEqual(actor.inputs[1]["goal"], TASK["goal"])
        self.assertIn("RECOVERY SUBGOAL", actor.inputs[2]["goal"])
        self.assertEqual(actor.inputs[3]["goal"], TASK["goal"])
        blocked = next(
            item for item in result["trace"]
            if item.get("execution_status") == "blocked_remembered_region"
        )
        self.assertEqual(blocked["actor_goal"], TASK["goal"])


if __name__ == "__main__":
    unittest.main()
