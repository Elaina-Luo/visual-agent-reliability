import copy
import io
import json
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from run_settings_evidence_gated_agent_v21 import run_episode


CLICK_SAVE = {"type": "click", "x": 20, "y": 20}
CLICK_CONFIRM = {"type": "click", "x": 40, "y": 40}
FINISH = {"type": "finish"}
TASK = {
    "task_id": "test", "goal": "Change and save", "initial_state": {},
    "target_key": "density", "target_value": "compact",
}
INCOMPLETE = {
    "saved": {"density": "comfortable"},
    "has_unapplied_changes": False,
    "confirmation_visible": False,
}
COMPLETE = {
    "saved": {"density": "compact"},
    "has_unapplied_changes": False,
    "confirmation_visible": False,
}


class Page:
    def __init__(self, state=INCOMPLETE):
        self.state = state
        stream = io.BytesIO()
        Image.new("RGB", (64, 64), "white").save(stream, format="PNG")
        self.png = stream.getvalue()

    def evaluate(self, script, *args):
        return copy.deepcopy(self.state)

    def screenshot(self, **kwargs):
        return self.png


class Actor:
    model_id = "fake"

    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.inputs = []

    def decide(self, **kwargs):
        self.inputs.append(copy.deepcopy(kwargs))
        output = next(self.outputs)
        return output if isinstance(output, str) else json.dumps(output), 0.1


class Verifier:
    pass


def candidate_record(action):
    return {
        "step": 1, "proposal": 1, "source": "actor", "action": action,
        "verification_status": "completion_candidate",
        "verification_vlm_status": "complete",
        "verification_latency_seconds": 0.2,
    }


class EvidenceGatedAgentV21Tests(unittest.TestCase):
    def test_two_distinct_candidates_terminate_completed_episode(self):
        def execute(*args, **kwargs):
            action = args[3]
            return (
                candidate_record(action),
                Image.new("RGB", (64, 64)),
                "after.png",
            )

        with tempfile.TemporaryDirectory() as directory, patch(
            "run_settings_evidence_gated_agent_v21.execute_verified_click_v2",
            side_effect=execute,
        ):
            result = run_episode(
                Page(COMPLETE), Actor([CLICK_SAVE, CLICK_CONFIRM]), Verifier(),
                TASK, max_steps=8, output_root=directory,
            )

        self.assertEqual(
            result["termination_reason"], "evidence_confirmed_complete"
        )
        self.assertTrue(result["agent_terminated_correctly"])
        self.assertEqual(result["steps"], 2)
        self.assertEqual(len(result["completion_evidence"]), 2)
        self.assertEqual(result["completion_candidates"], 2)
        self.assertEqual(result["trace"][-1]["completion_evidence_count"], 2)

    def test_false_two_candidate_completion_is_caught_by_evaluator(self):
        def execute(*args, **kwargs):
            action = args[3]
            return (
                candidate_record(action),
                Image.new("RGB", (64, 64)),
                "after.png",
            )

        with tempfile.TemporaryDirectory() as directory, patch(
            "run_settings_evidence_gated_agent_v21.execute_verified_click_v2",
            side_effect=execute,
        ):
            result = run_episode(
                Page(INCOMPLETE), Actor([CLICK_SAVE, CLICK_CONFIRM]), Verifier(),
                TASK, max_steps=8, output_root=directory,
            )

        self.assertEqual(
            result["termination_reason"], "evidence_confirmed_complete"
        )
        self.assertFalse(result["task_state_success"])
        self.assertFalse(result["agent_terminated_correctly"])

    def test_invalid_feedback_does_not_consume_action_budget(self):
        malformed = '{"type":"click","x":[20,20],"y":20}'
        actor = Actor([malformed, malformed, FINISH])
        with tempfile.TemporaryDirectory() as directory:
            result = run_episode(
                Page(), actor, Verifier(), TASK, max_steps=4,
                max_invalid_replans=3, output_root=directory,
            )

        self.assertEqual(result["invalid_replans"], 2)
        self.assertEqual(result["proposals"], 3)
        self.assertEqual(result["steps"], 1)
        self.assertEqual(result["termination_reason"], "agent_finish")
        feedback = actor.inputs[1]["verification_history"][-1]
        self.assertEqual(feedback["status"], "invalid_action")
        self.assertIn("integers", feedback["error"])
        self.assertIn('"x":integer', feedback["required_format"])

    def test_invalid_replan_limit_prevents_infinite_malformed_loop(self):
        malformed = '{"type":"click","x":[20,20],"y":20}'
        with tempfile.TemporaryDirectory() as directory:
            result = run_episode(
                Page(), Actor([malformed] * 3), Verifier(), TASK,
                max_steps=8, max_invalid_replans=3, output_root=directory,
            )

        self.assertEqual(result["steps"], 0)
        self.assertEqual(result["invalid_replans"], 3)
        self.assertEqual(
            result["termination_reason"], "invalid_replan_limit_exhausted"
        )


if __name__ == "__main__":
    unittest.main()
