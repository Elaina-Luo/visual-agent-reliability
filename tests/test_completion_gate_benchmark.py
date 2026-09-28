import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from run_completion_gate_benchmark import build_samples, evaluate_samples
from src.completion_gate_prompt import EVIDENCE_PROMPT_VERSION


class FakeGate:
    model_id = "fake/model"
    prompt_version = EVIDENCE_PROMPT_VERSION

    def check(self, image, goal):
        return '{"pending_action": true}', 0.1


def payload():
    state = {
        "saved": {"density": "comfortable"},
        "has_unapplied_changes": False,
        "confirmation_visible": False,
    }
    return {
        "ablation_arm": "B",
        "fault_mode": "none",
        "task": {
            "seed": 0,
            "task_id": "settings_000_density",
            "goal": "Select Compact density and save the changes.",
            "target_key": "density",
            "target_value": "compact",
        },
        "final_state": state,
        "trace": [{
            "step": 1,
            "observation": "step_01_before.png",
            "observation_after": "step_01_after.png",
            "evaluator_state_after": state,
            "verification": {"status": "changed"},
        }],
    }


class CompletionGateBenchmarkTests(unittest.TestCase):
    def test_builds_samples_only_from_selected_shadow_arm(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            episode = run_dir / "settings_clean_B" / "none" / "task"
            episode.mkdir(parents=True)
            (episode / "result.json").write_text(
                json.dumps(payload()), encoding="utf-8"
            )
            Image.new("RGB", (4, 4)).save(episode / "step_01_after.png")

            samples = build_samples(run_dir)

            self.assertEqual(len(samples), 1)
            self.assertEqual(samples[0]["result"]["ablation_arm"], "B")

    def test_evaluation_is_offline_and_writes_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            episode = root / "run" / "settings_clean_B" / "none" / "task"
            episode.mkdir(parents=True)
            (episode / "result.json").write_text(
                json.dumps(payload()), encoding="utf-8"
            )
            Image.new("RGB", (4, 4)).save(episode / "step_01_after.png")
            output = root / "result.json"

            result = evaluate_samples(root / "run", FakeGate(), output)

            self.assertEqual(result["metrics"]["sample_count"], 1)
            self.assertEqual(result["mode"], "offline_shadow_no_policy_control")
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
