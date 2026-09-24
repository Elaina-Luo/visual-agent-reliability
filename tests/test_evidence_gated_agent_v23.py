import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from run_settings_evidence_gated_agent_v23 import run_episode
from src.action_parser import parse_agent_action

from test_evidence_gated_agent_v21 import Actor, Page, TASK, Verifier


class EvidenceGatedAgentV23Tests(unittest.TestCase):
    def test_safely_repairs_redundant_matching_coordinate_pair(self):
        action = parse_agent_action(
            '{"type":"click","x":[876,298],"y":298}',
            viewport_width=980,
            viewport_height=644,
            allow_redundant_coordinate_pair=True,
        )

        self.assertEqual(action, {"type": "click", "x": 876, "y": 298})

    def test_rejects_redundant_coordinate_pair_when_y_disagrees(self):
        with self.assertRaisesRegex(ValueError, "must agree"):
            parse_agent_action(
                '{"type":"click","x":[876,298],"y":299}',
                viewport_width=980,
                viewport_height=644,
                allow_redundant_coordinate_pair=True,
            )

    def test_v22_behavior_still_rejects_redundant_coordinate_pair(self):
        with self.assertRaisesRegex(ValueError, "must be integers"):
            parse_agent_action(
                '{"type":"click","x":[876,298],"y":298}',
                viewport_width=980,
                viewport_height=644,
            )

    def test_v23_repairs_observed_output_without_invalid_replan(self):
        actor = Actor([
            '{"type":"click","x":[20,20],"y":20}',
            {"type": "finish"},
        ])
        record = {
            "action": {"type": "click", "x": 20, "y": 20},
            "verification_status": "changed",
            "verification_vlm_status": "changed",
        }
        with tempfile.TemporaryDirectory() as directory, patch(
            "run_settings_evidence_gated_agent_v21.execute_verified_click_v2",
            return_value=(record, Image.new("RGB", (64, 64)), "after.png"),
        ):
            result = run_episode(
                Page(), actor, Verifier(), TASK, max_steps=2,
                output_root=directory,
            )

        self.assertEqual(result["invalid_replans"], 0)
        self.assertEqual(result["trace"][0]["action"]["x"], 20)
        self.assertEqual(result["strategy"], "evidence_gated_recovery_v2_3")


if __name__ == "__main__":
    unittest.main()
