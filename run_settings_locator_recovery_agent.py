import argparse

from environment.settings_tasks import generate_settings_task
from run_settings_evidence_gated_agent import (
    DEFAULT_MODEL_ID,
    PROJECT_DIR,
    VIEWPORT,
    run_episode as run_evidence_gated_episode,
)
from src.settings_executor import FAULT_NONE, VALID_FAULT_MODES


def run_episode(
    page,
    actor,
    verifier,
    locator,
    task,
    fault_mode=FAULT_NONE,
    max_steps=8,
    max_blocked_replans=3,
    max_locator_calls=1,
    output_root=None,
):
    return run_evidence_gated_episode(
        page,
        actor,
        verifier,
        task,
        fault_mode=fault_mode,
        max_steps=max_steps,
        max_blocked_replans=max_blocked_replans,
        output_root=output_root,
        locator=locator,
        max_locator_calls=max_locator_calls,
        strategy="locator_recovery_v1",
        output_subdir="settings_locator_recovery_agent",
    )


def main():
    from playwright.sync_api import sync_playwright
    from src.qwen_settings_agent import QwenSettingsAgent
    from src.qwen_settings_locator import QwenSettingsLocator
    from src.qwen_settings_verifier import QwenSettingsVerifier

    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--max-blocked-replans", type=int, default=3)
    parser.add_argument("--max-locator-calls", type=int, default=1)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument(
        "--fault-mode", choices=sorted(VALID_FAULT_MODES), default=FAULT_NONE
    )
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    task = generate_settings_task(args.seed)
    print("Goal:", task["goal"])
    print("Strategy: locator-based recovery v1")
    print("Fault mode:", args.fault_mode)
    print("Loading model:", args.model_id)
    actor = QwenSettingsAgent(args.model_id)
    verifier = QwenSettingsVerifier(actor)
    locator = QwenSettingsLocator(actor)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed)
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=1)
        page.goto((PROJECT_DIR / "environment" / "settings.html").as_uri())
        result = run_episode(
            page,
            actor,
            verifier,
            locator,
            task,
            fault_mode=args.fault_mode,
            max_steps=args.max_steps,
            max_blocked_replans=args.max_blocked_replans,
            max_locator_calls=args.max_locator_calls,
        )
        browser.close()

    print("Success:", result["success"])
    print("Task state success:", result["task_state_success"])
    print("Agent terminated correctly:", result["agent_terminated_correctly"])
    print("Steps:", result["steps"])
    print("Proposals:", result["proposals"])
    print("Retries:", result["retry_count"])
    print("Blocked replans:", result["blocked_replans"])
    print("Locator calls:", result["locator_calls"])
    print("Locator actions:", result["locator_executed_actions"])
    print("Locator latency:", result["locator_latency_seconds"])
    print("Termination:", result["termination_reason"])


if __name__ == "__main__":
    main()
