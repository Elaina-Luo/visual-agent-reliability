import argparse
import json
from pathlib import Path

from environment.settings_tasks import generate_settings_task
from run_settings_evidence_gated_agent import (
    DEFAULT_MODEL_ID,
    PROJECT_DIR,
    VIEWPORT,
    capture,
    execute_verified_click_v2,
)
from src.action_parser import parse_agent_action
from src.episode_evaluator import evaluate_episode
from src.evidence_gated_policy import (
    can_replan,
    can_retry_invalid,
    completion_evidence_confirmed,
    should_retry_no_effect,
    update_completion_sequence,
)
from src.repeat_guard import (
    click_in_forbidden_regions,
    remember_changed_click,
)
from src.settings_executor import (
    FAULT_NONE,
    VALID_FAULT_MODES,
    new_fault_state,
    wait_for_render,
)


def run_episode(
    page,
    actor,
    verifier,
    task,
    fault_mode=FAULT_NONE,
    max_steps=8,
    max_blocked_replans=3,
    max_invalid_replans=3,
    output_root=None,
    strategy="evidence_gated_recovery_v2_1",
    output_subdir="settings_evidence_gated_agent_v21",
    action_aware_recovery=False,
    repair_redundant_coordinates=False,
):
    output_dir = (
        (Path(output_root) if output_root else PROJECT_DIR / "artifacts")
        / output_subdir
        / fault_mode
        / task["task_id"]
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    page.evaluate("(state) => window.resetSettingsTask(state)", task["initial_state"])
    wait_for_render(page)

    visible_actions = []
    verification_history = []
    forbidden_regions = []
    completion_sequence = []
    trace = []
    fault_state = new_fault_state()
    termination_reason = "budget_exhausted"
    action_number = 0
    proposal_number = 0
    retry_count = 0
    blocked_replans = 0
    invalid_replans = 0

    while action_number < max_steps:
        proposal_number += 1
        before_name = f"proposal_{proposal_number:02d}_before.png"
        before_image = capture(page, output_dir, before_name)
        try:
            raw_output, actor_latency = actor.decide(
                image=before_image,
                goal=task["goal"],
                recent_actions=visible_actions,
                remaining_steps=max_steps - action_number,
                verification_history=verification_history,
                forbidden_click_regions=forbidden_regions,
                action_aware_recovery=action_aware_recovery,
            )
        except Exception as error:
            trace.append({
                "step": None, "proposal": proposal_number, "source": "actor",
                "observation_before": before_name, "actor_raw_output": None,
                "action": None, "execution_status": "inference_error",
                "error": f"{type(error).__name__}: {error}",
            })
            termination_reason = "inference_error"
            break

        try:
            action = parse_agent_action(
                raw_output,
                viewport_width=before_image.width,
                viewport_height=before_image.height,
                allow_redundant_coordinate_pair=repair_redundant_coordinates,
            )
            parse_error = None
        except ValueError as error:
            action = None
            parse_error = str(error)

        if action is None:
            invalid_replans += 1
            completion_sequence = []
            trace.append({
                "step": None, "proposal": proposal_number,
                "source": "actor", "observation_before": before_name,
                "actor_raw_output": raw_output,
                "actor_latency_seconds": actor_latency, "action": None,
                "execution_status": "invalid_action", "error": parse_error,
            })
            verification_history.append({
                "action": None,
                "status": "invalid_action",
                "error": parse_error,
                "required_format": (
                    '{"type":"click","x":integer,"y":integer}'
                ),
                "retry": False,
            })
            if not can_retry_invalid(invalid_replans, max_invalid_replans):
                termination_reason = "invalid_replan_limit_exhausted"
                break
            continue

        visible_actions.append(action)
        if action["type"] == "finish":
            action_number += 1
            termination_reason = "agent_finish"
            trace.append({
                "step": action_number, "proposal": proposal_number,
                "source": "actor", "observation_before": before_name,
                "actor_raw_output": raw_output,
                "actor_latency_seconds": actor_latency, "action": action,
                "execution_status": "finished", "error": None,
            })
            break

        if click_in_forbidden_regions(action, forbidden_regions):
            blocked_replans += 1
            completion_sequence = []
            trace.append({
                "step": None, "proposal": proposal_number, "source": "actor",
                "observation_before": before_name,
                "actor_raw_output": raw_output,
                "actor_latency_seconds": actor_latency, "action": action,
                "execution_status": "blocked_remembered_region",
                "verification_status": "repeat_blocked", "error": None,
            })
            verification_history.append({
                "action": action, "status": "repeat_blocked", "retry": False,
            })
            if not can_replan(blocked_replans, max_blocked_replans):
                termination_reason = "replan_limit_exhausted"
                break
            continue

        action_number += 1
        record, after_image, after_name = execute_verified_click_v2(
            page, verifier, task, action, before_image, before_name, output_dir,
            action_number, proposal_number, "actor", fault_mode, fault_state,
            raw_output, actor_latency,
        )
        trace.append(record)
        status = record["verification_status"]
        completion_sequence = update_completion_sequence(
            completion_sequence, action, status
        )
        record["completion_evidence_count"] = len(completion_sequence)
        verification_history.append({
            "action": action, "status": status, "retry": False,
            "completion_evidence_count": len(completion_sequence),
        })
        if status in {"changed", "completion_candidate"}:
            forbidden_regions = remember_changed_click(
                forbidden_regions, action, "changed"
            )
        if completion_evidence_confirmed(completion_sequence):
            termination_reason = "evidence_confirmed_complete"
            break

        if not should_retry_no_effect(
            status, retry_count > 0, max_steps - action_number
        ):
            continue

        retry_count += 1
        action_number += 1
        visible_actions.append(action)
        retry_record, _, _ = execute_verified_click_v2(
            page, verifier, task, action, after_image, after_name, output_dir,
            action_number, proposal_number, "verifier_retry", fault_mode,
            fault_state,
        )
        trace.append(retry_record)
        retry_status = retry_record["verification_status"]
        completion_sequence = update_completion_sequence(
            completion_sequence, action, retry_status
        )
        retry_record["completion_evidence_count"] = len(completion_sequence)
        verification_history.append({
            "action": action, "status": retry_status, "retry": True,
            "completion_evidence_count": len(completion_sequence),
        })
        if retry_status in {"changed", "completion_candidate"}:
            forbidden_regions = remember_changed_click(
                forbidden_regions, action, "changed"
            )
        if completion_evidence_confirmed(completion_sequence):
            termination_reason = "evidence_confirmed_complete"
            break

    final_state = page.evaluate("() => window.getSettingsEvaluationState()")
    evaluation = evaluate_episode(final_state, task, termination_reason)
    result = {
        "model_id": actor.model_id,
        "strategy": strategy,
        "fault_mode": fault_mode,
        "fault_triggered": fault_state["triggered"],
        "task": task,
        **evaluation,
        "termination_reason": termination_reason,
        "steps": action_number,
        "proposals": proposal_number,
        "retry_count": retry_count,
        "blocked_replans": blocked_replans,
        "invalid_replans": invalid_replans,
        "max_blocked_replans": max_blocked_replans,
        "max_invalid_replans": max_invalid_replans,
        "forbidden_regions": forbidden_regions,
        "completion_evidence": completion_sequence,
        "completion_candidates": sum(
            record.get("verification_status") == "completion_candidate"
            for record in trace
        ),
        "verifier_calls": sum(
            "verification_vlm_status" in record for record in trace
        ),
        "trace": trace,
        "final_state": final_state,
    }
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    return result


def main():
    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--max-blocked-replans", type=int, default=3)
    parser.add_argument("--max-invalid-replans", type=int, default=3)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument(
        "--fault-mode", choices=sorted(VALID_FAULT_MODES), default=FAULT_NONE
    )
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    from src.qwen_settings_agent import QwenSettingsAgent
    from src.qwen_settings_verifier import QwenSettingsVerifier

    task = generate_settings_task(args.seed)
    print("Goal:", task["goal"])
    print("Strategy: evidence-gated recovery v2.1")
    print("Fault mode:", args.fault_mode)
    print("Loading model:", args.model_id)
    actor = QwenSettingsAgent(args.model_id)
    verifier = QwenSettingsVerifier(actor)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed)
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=1)
        page.goto((PROJECT_DIR / "environment" / "settings.html").as_uri())
        result = run_episode(
            page, actor, verifier, task, args.fault_mode, args.max_steps,
            args.max_blocked_replans, args.max_invalid_replans,
        )
        browser.close()

    print("Success:", result["success"])
    print("Task state success:", result["task_state_success"])
    print("Agent terminated correctly:", result["agent_terminated_correctly"])
    print("Steps:", result["steps"])
    print("Proposals:", result["proposals"])
    print("Retries:", result["retry_count"])
    print("Blocked replans:", result["blocked_replans"])
    print("Invalid replans:", result["invalid_replans"])
    print("Completion evidence:", len(result["completion_evidence"]))
    print("Termination:", result["termination_reason"])


if __name__ == "__main__":
    main()
