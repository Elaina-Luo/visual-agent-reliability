import copy
import io
import json
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from run_settings_evidence_gated_agent import run_episode


CLICK = {"type": "click", "x": 10, "y": 10}
FINISH = {"type": "finish"}
TASK = {
    "task_id": "test", "goal": "Change and save", "initial_state": {},
    "target_key": "density", "target_value": "compact",
}
STATE = {
    "saved": {"density": "comfortable"},
    "has_unapplied_changes": False,
    "confirmation_visible": False,
}


class Page:
    def __init__(self):
        stream = io.BytesIO()
        Image.new("RGB", (32, 32), "white").save(stream, format="PNG")
        self.png = stream.getvalue()

    def evaluate(self, script, *args):
        return copy.deepcopy(STATE)

    def screenshot(self, **kwargs):
        return self.png

    def wait_for_timeout(self, milliseconds):
        return None


class Actor:
    model_id = "fake"

    def __init__(self, actions):
        self.actions = iter(actions)
        self.inputs = []

    def decide(self, **kwargs):
        self.inputs.append(kwargs)
        return json.dumps(next(self.actions)), 0.1


class Verifier:
    def __init__(self, status="complete"):
        self.status = status

    def verify(self, **kwargs):
        return json.dumps({"status": self.status}), 0.2


class EvidenceGatedAgentTests(unittest.TestCase):
    def test_dropped_click_complete_prediction_retries_instead_of_stopping(self):
        execution = {
            "execution_status": "dropped_by_fault", "fault_triggered": True,
            "evaluator_state_before": STATE, "evaluator_state_after": STATE,
        }
        with tempfile.TemporaryDirectory() as directory, patch(
            "run_settings_evidence_gated_agent.execute_coordinate_click",
            return_value=execution,
        ):
            result = run_episode(
                Page(), Actor([CLICK, FINISH]), Verifier("complete"), TASK,
                max_steps=4, output_root=directory,
            )

        self.assertEqual(result["retry_count"], 1)
        self.assertEqual(result["completion_candidates"], 0)
        self.assertEqual(result["termination_reason"], "agent_finish")
        self.assertNotEqual(result["termination_reason"], "verifier_complete")

    def test_blocked_proposals_do_not_consume_action_budget(self):
        changed_record = {
            "step": 1, "proposal": 1, "source": "actor",
            "action": CLICK, "verification_status": "changed",
            "verification_vlm_status": "changed",
            "verification_latency_seconds": 0.2,
        }
        actor = Actor([CLICK, CLICK, CLICK, CLICK, FINISH])
        with tempfile.TemporaryDirectory() as directory, patch(
            "run_settings_evidence_gated_agent.execute_verified_click_v2",
            return_value=(changed_record, Image.new("RGB", (32, 32)), "after.png"),
        ):
            result = run_episode(
                Page(), actor, Verifier("changed"), TASK, max_steps=4,
                max_blocked_replans=4, output_root=directory,
            )

        self.assertEqual(result["blocked_replans"], 3)
        self.assertEqual(result["proposals"], 5)
        self.assertEqual(result["steps"], 2)
        self.assertEqual(result["termination_reason"], "agent_finish")
        self.assertEqual(len(actor.inputs[-1]["forbidden_click_regions"]), 1)

    def test_replan_limit_prevents_infinite_block_loop(self):
        changed_record = {
            "step": 1, "proposal": 1, "source": "actor",
            "action": CLICK, "verification_status": "changed",
            "verification_vlm_status": "changed",
            "verification_latency_seconds": 0.2,
        }
        with tempfile.TemporaryDirectory() as directory, patch(
            "run_settings_evidence_gated_agent.execute_verified_click_v2",
            return_value=(changed_record, Image.new("RGB", (32, 32)), "after.png"),
        ):
            result = run_episode(
                Page(), Actor([CLICK, CLICK, CLICK]), Verifier("changed"), TASK,
                max_steps=8, max_blocked_replans=2, output_root=directory,
            )

        self.assertEqual(result["steps"], 1)
        self.assertEqual(result["blocked_replans"], 2)
        self.assertEqual(result["termination_reason"], "replan_limit_exhausted")


if __name__ == "__main__":
    unittest.main()
