import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from environment.settings_tasks import generate_settings_task
from src.settings_executor import (
    FAULT_DROP_FIRST_SETTING_CHANGE,
    FAULT_NONE,
    execute_coordinate_click,
    new_fault_state,
)


PROJECT_DIR = Path(__file__).resolve().parent


def click_test_id(
    page,
    test_id,
    trace,
    output_dir,
    fault_mode,
    fault_state,
):
    locator = page.locator(f'[data-testid="{test_id}"]')
    box = locator.bounding_box()
    if box is None:
        raise RuntimeError(f"Control is not visible: {test_id}")

    x = round(box["x"] + box["width"] / 2)
    y = round(box["y"] + box["height"] / 2)
    step_record = execute_coordinate_click(
        page,
        x,
        y,
        fault_mode,
        fault_state,
    )

    screenshot_name = f"step_{len(trace) + 1:02d}.png"
    page.screenshot(path=str(output_dir / screenshot_name))
    step_record.update({
        "script_target": test_id,
        "observation": screenshot_name,
    })
    trace.append(step_record)


def evaluate_task(state, task, termination_reason):
    return (
        termination_reason == "agent_finish"
        and state["saved"][task["target_key"]] == task["target_value"]
        and state["has_unapplied_changes"] is False
        and state["confirmation_visible"] is False
    )


def run_task(
    page,
    task,
    name=None,
    fault_mode=FAULT_NONE,
    plan_test_ids=None,
):
    case_name = name or task["task_id"]
    output_dir = (
        PROJECT_DIR
        / "artifacts"
        / "settings_scripted"
        / case_name
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    page.evaluate(
        "(state) => window.resetSettingsTask(state)",
        task["initial_state"],
    )
    page.screenshot(path=str(output_dir / "step_00.png"))

    trace = []
    fault_state = new_fault_state()
    if plan_test_ids is None:
        plan_test_ids = [
            f"nav-{task['section']}",
            task["control_test_id"],
            "save-changes",
            "confirm-apply",
        ]

    for test_id in plan_test_ids:
        click_test_id(
            page,
            test_id,
            trace,
            output_dir,
            fault_mode,
            fault_state,
        )

    trace.append({"action": {"type": "finish"}})

    state = page.evaluate("() => window.getSettingsEvaluationState()")
    termination_reason = "agent_finish"
    success = evaluate_task(state, task, termination_reason)

    result = {
        "case": case_name,
        "task": task,
        "success": success,
        "termination_reason": termination_reason,
        "steps": len(trace),
        "fault_mode": fault_mode,
        "fault_triggered": fault_state["triggered"],
        "final_state": state,
        "trace": trace,
    }
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    return result


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page(
            viewport={"width": 980, "height": 644},
            device_scale_factor=1,
        )
        page.goto((PROJECT_DIR / "environment" / "settings.html").as_uri())

        for seed in range(3):
            task = generate_settings_task(seed)
            result = run_task(page, task)
            print(
                f"{task['task_id']}: success={result['success']}, "
                f"steps={result['steps']}"
            )
            assert result["success"], (
                f"Settings task failed: {task['task_id']}"
            )

        fault_task = generate_settings_task(seed=1)
        no_retry = run_task(
            page,
            fault_task,
            name="settings_fault_without_retry",
            fault_mode=FAULT_DROP_FIRST_SETTING_CHANGE,
            plan_test_ids=[
                f"nav-{fault_task['section']}",
                fault_task["control_test_id"],
            ],
        )
        dropped_step = no_retry["trace"][1]

        assert no_retry["fault_triggered"] is True
        assert dropped_step["execution_status"] == "dropped_by_fault"
        assert (
            dropped_step["evaluator_state_before"]
            == dropped_step["evaluator_state_after"]
        ), "A dropped setting click must leave state unchanged."
        assert no_retry["success"] is False

        with_retry = run_task(
            page,
            fault_task,
            name="settings_fault_with_scripted_retry",
            fault_mode=FAULT_DROP_FIRST_SETTING_CHANGE,
            plan_test_ids=[
                f"nav-{fault_task['section']}",
                fault_task["control_test_id"],
                fault_task["control_test_id"],
                "save-changes",
                "confirm-apply",
            ],
        )

        assert with_retry["fault_triggered"] is True
        assert with_retry["success"] is True

        print(
            "settings_fault_without_retry: "
            f"success={no_retry['success']}, "
            f"fault_triggered={no_retry['fault_triggered']}"
        )
        print(
            "settings_fault_with_scripted_retry: "
            f"success={with_retry['success']}, "
            f"fault_triggered={with_retry['fault_triggered']}"
        )

        browser.close()

    print("All settings-app scripted checks passed.")


if __name__ == "__main__":
    main()
