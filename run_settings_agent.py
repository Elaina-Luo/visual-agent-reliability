import argparse
import io
import json
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

from environment.settings_tasks import generate_settings_task
from src.action_parser import parse_agent_action
from src.qwen_settings_agent import DEFAULT_MODEL_ID, QwenSettingsAgent
from src.settings_executor import (
    FAULT_NONE,
    VALID_FAULT_MODES,
    execute_coordinate_click,
    new_fault_state,
    wait_for_render,
)


PROJECT_DIR = Path(__file__).resolve().parent
VIEWPORT = {"width": 980, "height": 644}


def evaluate_episode(state, task, termination_reason):
    return (
        termination_reason == "agent_finish"
        and state["saved"][task["target_key"]] == task["target_value"]
        and state["has_unapplied_changes"] is False
        and state["confirmation_visible"] is False
    )


def screenshot_image(screenshot_bytes):
    return Image.open(io.BytesIO(screenshot_bytes)).convert("RGB")


def run_episode(
    page,
    agent,
    task,
    fault_mode=FAULT_NONE,
    max_steps=8,
):
    output_dir = (
        PROJECT_DIR
        / "artifacts"
        / "settings_agent"
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
    trace = []
    fault_state = new_fault_state()
    termination_reason = "budget_exhausted"

    for step in range(1, max_steps + 1):
        screenshot_name = f"step_{step:02d}_before.png"
        screenshot_bytes = page.screenshot(
            path=str(output_dir / screenshot_name),
            type="png",
        )
        image = screenshot_image(screenshot_bytes)

        try:
            raw_output, latency_seconds = agent.decide(
                image=image,
                goal=task["goal"],
                recent_actions=visible_actions,
                remaining_steps=max_steps - step + 1,
            )
        except Exception as error:
            trace.append({
                "step": step,
                "observation": screenshot_name,
                "raw_output": None,
                "action": None,
                "status": "inference_error",
                "error": f"{type(error).__name__}: {error}",
            })
            termination_reason = "inference_error"
            break

        try:
            action = parse_agent_action(
                raw_output,
                viewport_width=image.width,
                viewport_height=image.height,
            )
            parse_error = None
        except ValueError as error:
            action = None
            parse_error = str(error)

        step_record = {
            "step": step,
            "observation": screenshot_name,
            "raw_output": raw_output,
            "latency_seconds": latency_seconds,
            "action": action,
            "status": "invalid_action" if parse_error else "valid_action",
            "error": parse_error,
        }

        if action is None:
            trace.append(step_record)
            continue

        visible_actions.append(action)
        if action["type"] == "finish":
            termination_reason = "agent_finish"
            step_record["execution_status"] = "finished"
            trace.append(step_record)
            break

        execution_record = execute_coordinate_click(
            page,
            action["x"],
            action["y"],
            fault_mode,
            fault_state,
        )
        # Keep evaluator-only execution details in the trace, not the prompt.
        step_record.update({
            "execution_status": execution_record["execution_status"],
            "fault_triggered": execution_record["fault_triggered"],
            "evaluator_state_before": (
                execution_record["evaluator_state_before"]
            ),
            "evaluator_state_after": (
                execution_record["evaluator_state_after"]
            ),
        })
        trace.append(step_record)

    final_state = page.evaluate(
        "() => window.getSettingsEvaluationState()"
    )
    result = {
        "model_id": agent.model_id,
        "strategy": "reactive",
        "fault_mode": fault_mode,
        "fault_triggered": fault_state["triggered"],
        "task": task,
        "success": evaluate_episode(
            final_state,
            task,
            termination_reason,
        ),
        "termination_reason": termination_reason,
        "steps": len(trace),
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
    print("Fault mode:", args.fault_mode)
    print("Loading model:", args.model_id)
    agent = QwenSettingsAgent(args.model_id)

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
            agent=agent,
            task=task,
            fault_mode=args.fault_mode,
            max_steps=args.max_steps,
        )
        browser.close()

    print("Success:", result["success"])
    print("Steps:", result["steps"])
    print("Termination:", result["termination_reason"])
    print("Fault triggered:", result["fault_triggered"])


if __name__ == "__main__":
    main()
