import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from run_settings_agent import run_episode


CLICK = {"type": "click", "x": 10, "y": 10}
FINISH = {"type": "finish"}
TASK = {
    "task_id": "test", "goal": "Save compact density", "initial_state": {},
    "target_key": "density", "target_value": "compact",
}


class Page:
    def __init__(self, completed=True):
        self.state = {
            "saved": {"density": "compact" if completed else "comfortable"},
            "has_unapplied_changes": False, "confirmation_visible": False,
        }
        stream = io.BytesIO()
        Image.new("RGB", (32, 32)).save(stream, format="PNG")
        self.png = stream.getvalue()

    def evaluate(self, script, *args):
        return copy.deepcopy(self.state)

    def screenshot(self, **kwargs):
        return self.png


class Actor:
    model_id = "fake"

    def __init__(self, actions):
        self.actions = iter(actions)
        self.inputs = []

    # Deliberately rejects verification_history and forbidden_click_region.
    def decide(self, image, goal, recent_actions, remaining_steps):
        self.inputs.append((goal, copy.deepcopy(recent_actions), remaining_steps))
        action = next(self.actions)
        if isinstance(action, Exception):
            raise action
        return (action if isinstance(action, str) else json.dumps(action)), 0.25


class Verifier:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.actions = []

    def verify(self, **kwargs):
        self.actions.append(kwargs["requested_action"])
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response, 0.5


def status(value):
    return json.dumps({"status": value})


class CleanAblationTests(unittest.TestCase):
    def run_arm(self, arm, actions, responses=(), budget=8, completed=True):
        actor, verifier = Actor(actions), Verifier(responses)
        execution = {
            "execution_status": "executed", "fault_triggered": False,
            "evaluator_state_before": {}, "evaluator_state_after": {},
        }
        with tempfile.TemporaryDirectory() as directory, patch(
            "run_settings_agent.execute_coordinate_click", return_value=execution,
        ) as execute:
            result = run_episode(
                Page(completed), actor, TASK, max_steps=budget,
                strategy=arm, verifier=verifier, output_root=directory,
            )
            saved = list(Path(directory).rglob("result.json"))
            self.assertEqual(json.loads(saved[0].read_text()), result)
            return result, actor, verifier, execute.call_count

    def test_a_never_calls_verifier(self):
        result, _, verifier, _ = self.run_arm("A", [CLICK, FINISH])
        self.assertEqual(verifier.actions, [])
        self.assertEqual(result["verifier_calls"], 0)
        self.assertEqual(result["retry_count"], 0)

    def test_b_all_verifier_outcomes_leave_policy_identical_to_a(self):
        actions = [CLICK, CLICK, FINISH]
        baseline, baseline_actor, _, _ = self.run_arm("A", actions)
        for response in [status(s) for s in ("complete", "no_effect", "changed", "uncertain")] + ["bad json", RuntimeError("offline")]:
            with self.subTest(response=response):
                result, actor, verifier, clicks = self.run_arm("B", actions, [response] * 3)
                self.assertEqual(actor.inputs, baseline_actor.inputs)
                self.assertEqual([r["action"] for r in result["trace"]], actions)
                self.assertEqual(result["termination_reason"], baseline["termination_reason"])
                self.assertEqual(result["retry_count"], 0)
                self.assertEqual(clicks, 2)
                self.assertEqual(len(verifier.actions), 3)

    def test_b_complete_does_not_stop_at_budget(self):
        result, _, _, _ = self.run_arm("B", [CLICK] * 3, [status("complete")] * 3, budget=3)
        self.assertEqual(result["steps"], 3)
        self.assertEqual(result["termination_reason"], "budget_exhausted")

    def test_c_retries_at_most_once_per_episode(self):
        result, actor, verifier, clicks = self.run_arm("C", [CLICK] * 4, [status("no_effect")] * 5, budget=5)
        self.assertEqual(result["retry_count"], 1)
        self.assertEqual(clicks, 5)
        self.assertEqual(len(actor.inputs), 4)
        self.assertEqual(len(verifier.actions), 5)
        self.assertEqual([r["source"] for r in result["trace"]], ["actor", "verifier_retry", "actor", "actor", "actor"])
        self.assertEqual([i[2] for i in actor.inputs], [5, 3, 2, 1])

    def test_c_cannot_retry_beyond_budget(self):
        result, _, _, clicks = self.run_arm("C", [CLICK], [status("no_effect")], budget=1)
        self.assertEqual(result["retry_count"], 0)
        self.assertEqual(clicks, 1)

    def test_c_verified_completion(self):
        result, _, _, clicks = self.run_arm("C", [CLICK], [status("complete")])
        self.assertEqual(result["termination_reason"], "verifier_complete")
        self.assertTrue(result["agent_terminated_correctly"])
        self.assertEqual(clicks, 1)

    def test_c_completion_on_retry(self):
        result, _, _, clicks = self.run_arm("C", [CLICK], [status("no_effect"), status("complete")])
        self.assertEqual(result["termination_reason"], "verifier_complete")
        self.assertEqual(result["retry_count"], 1)
        self.assertEqual(clicks, 2)

    def test_false_completion_fails_ground_truth_evaluation(self):
        result, _, _, _ = self.run_arm("C", [CLICK], [status("complete")], completed=False)
        self.assertFalse(result["task_state_success"])
        self.assertFalse(result["agent_terminated_correctly"])
        self.assertTrue(result["failure_details"]["premature_termination"])

    def test_clean_arms_preserve_actor_inputs_and_execute_repeated_clicks(self):
        actions = [CLICK, CLICK, FINISH]
        _, baseline, _, _ = self.run_arm("A", actions)
        with patch("src.repeat_guard.should_block_repeated_click", side_effect=AssertionError("guard called")), patch(
            "src.repeat_guard.active_forbidden_click_region", side_effect=AssertionError("replanning called"),
        ):
            for arm in ("B", "C"):
                result, actor, _, clicks = self.run_arm(arm, actions, [status("changed")] * 3)
                self.assertEqual(actor.inputs, baseline.inputs)
                self.assertEqual(clicks, 2)
                self.assertEqual(result["repeat_blocks"], 0)
                self.assertEqual(result["forbidden_region_prompt_count"], 0)

    def test_metrics_include_retry_cost_and_verifier_outputs(self):
        result, _, _, _ = self.run_arm("C", [CLICK, FINISH], [status("no_effect"), status("changed"), status("changed")])
        self.assertEqual(result["steps"], 3)
        self.assertEqual(result["action_count"], 3)
        self.assertEqual(result["click_count"], 2)
        self.assertEqual(result["actor_calls"], 2)
        self.assertEqual(result["actor_latency_seconds"], 0.5)
        self.assertEqual(result["verifier_latency_seconds"], 1.5)
        self.assertEqual(result["trace"][0]["verification"]["raw_output"], status("no_effect"))

    def test_c_verifier_errors_do_not_trigger_recovery(self):
        for response in ("bad json", RuntimeError("offline")):
            result, _, _, _ = self.run_arm("C", [CLICK, FINISH], [response] * 2)
            self.assertEqual(result["retry_count"], 0)
            self.assertEqual(result["termination_reason"], "agent_finish")
            self.assertEqual(len(result["failure_details"]["errors"]), 2)
            self.assertGreaterEqual(result["verifier_wall_latency_seconds"], 0)

    def test_invalid_actor_output_is_not_an_executed_action(self):
        result, _, verifier, clicks = self.run_arm("B", ["bad json", FINISH], [status("complete")])
        self.assertEqual(result["steps"], 2)
        self.assertEqual(result["action_count"], 1)
        self.assertEqual(clicks, 0)
        self.assertEqual(len(verifier.actions), 1)
        self.assertEqual(len(result["failure_details"]["errors"]), 1)

    def test_actor_inference_error_is_recorded(self):
        result, _, _, _ = self.run_arm("B", [RuntimeError("actor offline")])
        self.assertEqual(result["termination_reason"], "inference_error")
        self.assertEqual(result["action_count"], 0)
        self.assertEqual(result["actor_calls"], 1)
        self.assertIn("actor offline", result["failure_details"]["errors"][0]["actor_error"])


if __name__ == "__main__":
    unittest.main()
