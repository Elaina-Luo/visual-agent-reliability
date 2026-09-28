import copy
import io
import json
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from run_settings_locator_recovery_agent import run_episode
from src.locator_recovery import build_locator_prompt, parse_locator_output


ACTOR_CLICK = {"type": "click", "x": 10, "y": 10}
LOCATOR_CLICK = {"type": "click", "x": 25, "y": 25}
FINISH = {"type": "finish"}
TASK = {
    "task_id": "test",
    "goal": "Change the setting and save",
    "initial_state": {},
    "target_key": "density",
    "target_value": "compact",
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


class Actor:
    model_id = "fake"

    def __init__(self, actions):
        self.actions = iter(actions)

    def decide(self, **kwargs):
        return json.dumps(next(self.actions)), 0.1


class Verifier:
    pass


class Locator:
    def __init__(self, output):
        self.output = output
        self.inputs = []

    def locate(self, **kwargs):
        self.inputs.append(kwargs)
        return self.output, 0.3


def changed_execution(*args, **kwargs):
    action = args[3]
    return ({
        "step": args[7],
        "proposal": args[8],
        "source": args[9],
        "action": action,
        "execution_status": "executed",
        "verification_status": "changed",
        "verification_vlm_status": "changed",
        "verification_latency_seconds": 0.2,
    }, Image.new("RGB", (32, 32)), "after.png")


class LocatorRecoveryTests(unittest.TestCase):
    def test_prompt_is_history_free_and_scoped_to_visible_recovery(self):
        prompt = build_locator_prompt(
            TASK["goal"], 980, 644,
            forbidden_regions=[{"x": 876, "y": 298, "radius": 12}],
        )

        self.assertIn(TASK["goal"], prompt)
        self.assertIn("Save changes", prompt)
        self.assertIn('"x": 876', prompt)
        self.assertNotIn("Recent actions", prompt)
        self.assertNotIn("verification", prompt.lower())

    def test_parser_accepts_click_unavailable_and_qwen_pair(self):
        self.assertEqual(
            parse_locator_output(
                '{"status":"click","x":25,"y":25}', 32, 32
            ),
            LOCATOR_CLICK,
        )
        self.assertEqual(
            parse_locator_output(
                '{"status":"click","x":[25,25]}', 32, 32
            ),
            LOCATOR_CLICK,
        )
        self.assertIsNone(
            parse_locator_output('{"status":"unavailable"}', 32, 32)
        )

    def test_parser_rejects_conflicting_redundant_coordinates(self):
        with self.assertRaisesRegex(ValueError, "must agree"):
            parse_locator_output(
                '{"status":"click","x":[25,24],"y":25}', 32, 32
            )

    def test_repeat_block_triggers_one_locator_action(self):
        locator = Locator('{"status":"click","x":25,"y":25}')
        with tempfile.TemporaryDirectory() as directory, patch(
            "run_settings_evidence_gated_agent.execute_verified_click_v2",
            side_effect=changed_execution,
        ):
            result = run_episode(
                Page(), Actor([ACTOR_CLICK, ACTOR_CLICK, FINISH]), Verifier(),
                locator, TASK, max_steps=4, output_root=directory,
            )

        self.assertEqual(result["strategy"], "locator_recovery_v1")
        self.assertEqual(result["blocked_replans"], 1)
        self.assertEqual(result["locator_calls"], 1)
        self.assertEqual(result["locator_executed_actions"], 1)
        self.assertEqual(result["locator_latency_seconds"], 0.3)
        self.assertEqual(result["steps"], 3)
        self.assertEqual(result["termination_reason"], "agent_finish")
        self.assertEqual(
            set(locator.inputs[0]), {"image", "goal", "forbidden_regions"}
        )
        locator_trace = next(
            item for item in result["trace"]
            if item.get("source") == "recovery_locator"
        )
        self.assertEqual(locator_trace["action"], LOCATOR_CLICK)

    def test_unavailable_locator_falls_back_without_spending_action(self):
        locator = Locator('{"status":"unavailable"}')
        with tempfile.TemporaryDirectory() as directory, patch(
            "run_settings_evidence_gated_agent.execute_verified_click_v2",
            side_effect=changed_execution,
        ):
            result = run_episode(
                Page(), Actor([ACTOR_CLICK, ACTOR_CLICK, FINISH]), Verifier(),
                locator, TASK, max_steps=4, output_root=directory,
            )

        self.assertEqual(result["locator_calls"], 1)
        self.assertEqual(result["locator_executed_actions"], 0)
        self.assertEqual(result["steps"], 2)
        self.assertEqual(result["termination_reason"], "agent_finish")
        unavailable = next(
            item for item in result["trace"]
            if item.get("execution_status") == "locator_unavailable"
        )
        self.assertIsNone(unavailable["action"])


if __name__ == "__main__":
    unittest.main()
