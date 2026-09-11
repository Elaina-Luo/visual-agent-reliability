import argparse
import io
import json
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

from environment.settings_tasks import generate_settings_task
from src.action_parser import parse_agent_action
from src.episode_evaluator import evaluate_episode
from src.qwen_settings_agent import DEFAULT_MODEL_ID, QwenSettingsAgent
from src.qwen_settings_verifier import QwenSettingsVerifier
from src.recovery_policy import choose_recovery
from src.settings_executor import (
    FAULT_NONE,
    VALID_FAULT_MODES,
    execute_coordinate_click,
    new_fault_state,
    wait_for_render,
)
from src.verifier_parser import parse_verification
from src.visual_change import (
    DEFAULT_CHANGED_FRACTION_THRESHOLD,
    DEFAULT_INTENSITY_THRESHOLD,
    changed_pixel_fraction,
    fuse_verification,
)


PROJECT_DIR = Path(__file__).resolve().parent
VIEWPORT = {"width": 980, "height": 644}


def screenshot_image(screenshot_bytes):
    return Image.open(io.BytesIO(screenshot_bytes)).convert("RGB")


def capture(page, output_dir, name):
    screenshot_bytes = page.screenshot(
        path=str(output_dir / name),
        type="png",
    )
    return screenshot_image(screenshot_bytes)


def verify_transition(verifier, before_image, after_image, goal, action):
    pixel_change_fraction = changed_pixel_fraction(
        before_image,
        after_image,
    )
    try:
        raw_output, latency_seconds = verifier.verify(
            before_image=before_image,
            after_image=after_image,
            goal=goal,
            requested_action=action,
        )
    except Exception as error:
        return {
            "raw_output": None,
            "vlm_status": "uncertain",
            "status": fuse_verification(
                "uncertain",
                pixel_change_fraction,
            ),
            "pixel_change_fraction": pixel_change_fraction,
            "latency_seconds": None,
            "error": f"{type(error).__name__}: {error}",
        }

    try:
        verification = parse_verification(raw_output)
        vlm_status = verification["status"]
        parse_error = None
    except ValueError as error:
        vlm_status = "uncertain"
        parse_error = str(error)

    return {
        "raw_output": raw_output,
        "vlm_status": vlm_status,
        "status": fuse_verification(
            vlm_status,
            pixel_change_fraction,
        ),
        "pixel_change_fraction": pixel_change_fraction,
        "latency_seconds": latency_seconds,
        "error": parse_error,
    }


def execute_verified_click(
    page,
    verifier,
    task,
    action,
    before_image,
    before_name,
    output_dir,
    action_number,
    source,
    fault_mode,
    fault_state,
    actor_raw_output=None,
    actor_latency_seconds=None,
):
    execution = execute_coordinate_click(
        page,
        action["x"],
        action["y"],
        fault_mode,
        fault_state,
    )
    # Let the Settings App's 150 ms visual transitions settle before
    # comparing screenshots.
    page.wait_for_timeout(180)
    after_name = f"step_{action_number:02d}_after.png"
    after_image = capture(page, output_dir, after_name)
    verification = verify_transition(
        verifier,
        before_image,
        after_image,
        task["goal"],
        action,
    )

    record = {
        "step": action_number,
        "source": source,
        "observation_before": before_name,
        "observation_after": after_name,
        "actor_raw_output": actor_raw_output,
        "actor_latency_seconds": actor_latency_seconds,
        "action": action,
        "execution_status": execution["execution_status"],
        "fault_triggered": execution["fault_triggered"],
        "verification_raw_output": verification["raw_output"],
        "verification_vlm_status": verification["vlm_status"],
        "verification_status": verification["status"],
        "pixel_change_fraction": verification["pixel_change_fraction"],
        "verification_latency_seconds": verification["latency_seconds"],
        "verification_error": verification["error"],
        "evaluator_state_before": execution["evaluator_state_before"],
        "evaluator_state_after": execution["evaluator_state_after"],
    }
    return record, after_image, after_name


def run_episode(
    page,
    actor,
    verifier,
    task,
    fault_mode=FAULT_NONE,
    max_steps=8,
):
    output_dir = (
        PROJECT_DIR
        / "artifacts"
        / "settings_verified_agent"
        / fault_mode
        / task["task_id"]
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    page.evaluate(
        "(state) => window.resetSettingsTask(state)",
        task["initial_state"],
    )
    wait_for_render(page)

    visible_actions = []
    verification_history = []
    trace = []
    fault_state = new_fault_state()
    termination_reason = "budget_exhausted"
    action_number = 0
    retry_count = 0

    while action_number < max_steps:
        next_number = action_number + 1
        before_name = f"step_{next_number:02d}_before.png"
        before_image = capture(page, output_dir, before_name)

        try:
            raw_output, actor_latency = actor.decide(
                image=before_image,
                goal=task["goal"],
                recent_actions=visible_actions,
                remaining_steps=max_steps - action_number,
                verification_history=verification_history,
            )
        except Exception as error:
            action_number += 1
            trace.append({
                "step": action_number,
                "source": "actor",
                "observation_before": before_name,
                "actor_raw_output": None,
                "action": None,
                "error": f"{type(error).__name__}: {error}",
            })
            termination_reason = "inference_error"
            break

        try:
            action = parse_agent_action(
                raw_output,
                viewport_width=before_image.width,
                viewport_height=before_image.height,
            )
            parse_error = None
        except ValueError as error:
            action = None
            parse_error = str(error)

        action_number += 1
        if action is None:
            trace.append({
                "step": action_number,
                "source": "actor",
                "observation_before": before_name,
                "actor_raw_output": raw_output,
                "actor_latency_seconds": actor_latency,
                "action": None,
                "error": parse_error,
            })
            continue

        visible_actions.append(action)
        if action["type"] == "finish":
            termination_reason = "agent_finish"
            trace.append({
                "step": action_number,
                "source": "actor",
                "observation_before": before_name,
                "actor_raw_output": raw_output,
                "actor_latency_seconds": actor_latency,
                "action": action,
                "execution_status": "finished",
            })
            break

        record, after_image, after_name = execute_verified_click(
            page=page,
            verifier=verifier,
            task=task,
            action=action,
            before_image=before_image,
            before_name=before_name,
            output_dir=output_dir,
            action_number=action_number,
            source="actor",
            fault_mode=fault_mode,
            fault_state=fault_state,
            actor_raw_output=raw_output,
            actor_latency_seconds=actor_latency,
        )
        trace.append(record)
        verification_history.append({
            "action": action,
            "status": record["verification_status"],
            "retry": False,
        })

        recovery = choose_recovery(
            record["verification_status"],
            retry_already_used=False,
        )
        if recovery == "finish":
            termination_reason = "verifier_complete"
            break

        if recovery != "retry" or action_number >= max_steps:
            continue

        retry_count += 1
        action_number += 1
        visible_actions.append(action)
        retry_record, _, _ = execute_verified_click(
            page=page,
            verifier=verifier,
            task=task,
            action=action,
            before_image=after_image,
            before_name=after_name,
            output_dir=output_dir,
            action_number=action_number,
            source="verifier_retry",
            fault_mode=fault_mode,
            fault_state=fault_state,
        )
        trace.append(retry_record)
        verification_history.append({
            "action": action,
            "status": retry_record["verification_status"],
            "retry": True,
        })

        retry_recovery = choose_recovery(
            retry_record["verification_status"],
            retry_already_used=True,
        )
        if retry_recovery == "finish":
            termination_reason = "verifier_complete"
            break

    final_state = page.evaluate(
        "() => window.getSettingsEvaluationState()"
    )
    evaluation = evaluate_episode(
        final_state,
        task,
        termination_reason,
    )
    result = {
        "model_id": actor.model_id,
        "strategy": (
            "hybrid_visual_verification_retry_1_completion_guard"
        ),
        "fault_mode": fault_mode,
        "fault_triggered": fault_state["triggered"],
        "task": task,
        **evaluation,
        "termination_reason": termination_reason,
        "steps": len(trace),
        "retry_count": retry_count,
        "verifier_calls": sum(
            "verification_status" in record for record in trace
        ),
        "pixel_change_config": {
            "intensity_threshold": DEFAULT_INTENSITY_THRESHOLD,
            "changed_fraction_threshold": (
                DEFAULT_CHANGED_FRACTION_THRESHOLD
            ),
        },
        "final_state": final_state,
        "trace": trace,
    }
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument(
        "--fault-mode",
        choices=sorted(VALID_FAULT_MODES),
        default=FAULT_NONE,
    )
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    task = generate_settings_task(args.seed)
    print("Goal:", task["goal"])
    print("Strategy: visual verification + one retry")
    print("Fault mode:", args.fault_mode)
    print("Loading model:", args.model_id)
    actor = QwenSettingsAgent(args.model_id)
    verifier = QwenSettingsVerifier(actor)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed)
        page = browser.new_page(
            viewport=VIEWPORT,
            device_scale_factor=1,
        )
        page.goto(
            (PROJECT_DIR / "environment" / "settings.html").as_uri()
        )
        result = run_episode(
            page=page,
            actor=actor,
            verifier=verifier,
            task=task,
            fault_mode=args.fault_mode,
            max_steps=args.max_steps,
        )
        browser.close()

    print("Success:", result["success"])
    print("Task state success:", result["task_state_success"])
    print(
        "Termination signal emitted:",
        result["termination_signal_emitted"],
    )
    print(
        "Agent terminated correctly:",
        result["agent_terminated_correctly"],
    )
    print("Steps:", result["steps"])
    print("Retries:", result["retry_count"])
    print("Verifier calls:", result["verifier_calls"])
    print("Termination:", result["termination_reason"])
    print("Fault triggered:", result["fault_triggered"])


if __name__ == "__main__":
    main()
