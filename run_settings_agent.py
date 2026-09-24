import argparse
import io
import json
import time
from pathlib import Path

from PIL import Image

from environment.settings_tasks import generate_settings_task
from src.action_parser import parse_agent_action
from src.episode_evaluator import evaluate_episode
from src.clean_verification import verify_action
from src.settings_executor import (
    FAULT_NONE,
    VALID_FAULT_MODES,
    execute_coordinate_click,
    new_fault_state,
    wait_for_render,
)


PROJECT_DIR = Path(__file__).resolve().parent
VIEWPORT = {"width": 980, "height": 644}


def screenshot_image(screenshot_bytes):
    return Image.open(io.BytesIO(screenshot_bytes)).convert("RGB")


def run_episode(
    page,
    agent,
    task,
    fault_mode=FAULT_NONE,
    max_steps=8,
    strategy="A",
    verifier=None,
    output_root=None,
):
    if strategy not in {"A", "B", "C"}:
        raise ValueError("strategy must be A, B, or C")
    if strategy != "A" and verifier is None:
        raise ValueError("B/C require a visual verifier")
    if max_steps < 1:
        raise ValueError("max_steps must be positive")
    output_dir = (
        (Path(output_root) if output_root is not None else PROJECT_DIR / "artifacts")
        / ("settings_agent" if strategy == "A" else f"settings_clean_{strategy}")
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
    retry_count = 0
    pending_retry = None

    for step in range(1, max_steps + 1):
        screenshot_name = f"step_{step:02d}_before.png"
        screenshot_bytes = page.screenshot(
            path=str(output_dir / screenshot_name),
            type="png",
        )
        image = screenshot_image(screenshot_bytes)

        source = "verifier_retry" if pending_retry is not None else "actor"
        actor_started = time.perf_counter()
        try:
            if pending_retry is not None:
                raw_output, latency_seconds = json.dumps(pending_retry), 0.0
                pending_retry = None
                retry_count += 1
            else:
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
                "source": source,
                "actor_wall_latency_seconds": time.perf_counter() - actor_started,
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
            "actor_latency_seconds": latency_seconds,
            "actor_wall_latency_seconds": (
                time.perf_counter() - actor_started if source == "actor" else 0.0
            ),
            "source": source,
            "action": action,
            "status": "invalid_action" if parse_error else "valid_action",
            "error": parse_error,
        }

        if action is None:
            trace.append(step_record)
            continue

        visible_actions.append(action)
        if action["type"] == "finish":
            if strategy != "A":
                # Finish is a no-op action: audit it, but never veto Actor finish.
                step_record["verification"] = verify_action(
                    verifier, image, image, task["goal"], action,
                )
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
        if strategy != "A":
            after_name = f"step_{step:02d}_after.png"
            after_image = screenshot_image(page.screenshot(
                path=str(output_dir / after_name), type="png",
            ))
            step_record["observation_after"] = after_name
            verification = verify_action(
                verifier, image, after_image, task["goal"], action,
            )
            step_record["verification"] = verification
            # B is observation-only, including malformed/unavailable verification.
            if strategy == "C":
                if verification["status"] == "complete":
                    termination_reason = "verifier_complete"
                    break
                if (verification["status"] == "no_effect"
                        and retry_count == 0 and step < max_steps):
                    pending_retry = dict(action)

    final_state = page.evaluate(
        "() => window.getSettingsEvaluationState()"
    )
    evaluation = evaluate_episode(
        final_state,
        task,
        termination_reason,
    )
    result = {
        "model_id": agent.model_id,
        "strategy": {"A": "reactive", "B": "verification_only", "C": "verification_recovery"}[strategy],
        "ablation_arm": strategy,
        "fault_mode": fault_mode,
        "fault_triggered": fault_state["triggered"],
        "task": task,
        **evaluation,
        "termination_reason": termination_reason,
        "steps": len(trace),
        "action_count": sum(record.get("action") is not None for record in trace),
        "click_count": sum(record.get("action", {}).get("type") == "click"
                           for record in trace if record.get("action")),
        "retry_count": retry_count,
        "actor_calls": sum(record["source"] == "actor" for record in trace),
        "actor_latency_seconds": sum(record.get("actor_latency_seconds", 0.0) for record in trace),
        "actor_wall_latency_seconds": sum(record.get("actor_wall_latency_seconds", 0.0) for record in trace),
        "verifier_calls": sum("verification" in record for record in trace),
        "verifier_latency_seconds": sum(record.get("verification", {}).get("latency_seconds") or 0.0 for record in trace),
        "verifier_wall_latency_seconds": sum(record.get("verification", {}).get("wall_latency_seconds", 0.0) for record in trace),
        "repeat_blocks": 0,
        "forbidden_region_prompt_count": 0,
        "failure_details": {
            "task_state_mismatch": not evaluation["task_state_success"],
            "missing_termination_signal": not evaluation["termination_signal_emitted"],
            "premature_termination": evaluation["termination_signal_emitted"] and not evaluation["task_state_success"],
            "errors": [{"step": record["step"], "actor_error": record.get("error"),
                        "verifier_error": record.get("verification", {}).get("error")}
                       for record in trace if record.get("error") or record.get("verification", {}).get("error")],
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
    from playwright.sync_api import sync_playwright
    from src.qwen_settings_agent import DEFAULT_MODEL_ID, QwenSettingsAgent

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
    parser.add_argument("--strategy", choices=["A", "B", "C"], default="A")
    args = parser.parse_args()

    task = generate_settings_task(args.seed)
    print("Goal:", task["goal"])
    print("Fault mode:", args.fault_mode)
    print("Loading model:", args.model_id)
    agent = QwenSettingsAgent(args.model_id)
    verifier = None
    if args.strategy != "A":
        from src.qwen_settings_verifier import QwenSettingsVerifier
        verifier = QwenSettingsVerifier(agent)

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
            strategy=args.strategy,
            verifier=verifier,
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
    print("Ablation arm:", result["ablation_arm"])
    print("Actions:", result["action_count"])
    print("Retries:", result["retry_count"])
    print("Actor latency:", result["actor_latency_seconds"])
    print("Verifier latency:", result["verifier_latency_seconds"])
    print("Termination:", result["termination_reason"])
    print("Fault triggered:", result["fault_triggered"])


if __name__ == "__main__":
    main()
