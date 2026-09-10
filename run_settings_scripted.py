import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from environment.settings_tasks import generate_settings_task


PROJECT_DIR = Path(__file__).resolve().parent


def click_test_id(page, test_id, trace, output_dir):
    locator = page.locator(f'[data-testid="{test_id}"]')
    box = locator.bounding_box()
    if box is None:
        raise RuntimeError(f"Control is not visible: {test_id}")

    x = round(box["x"] + box["width"] / 2)
    y = round(box["y"] + box["height"] / 2)
    page.mouse.click(x, y)
    page.evaluate(
        """
        () => new Promise(resolve => {
            requestAnimationFrame(() => requestAnimationFrame(resolve));
        })
        """
    )

    screenshot_name = f"step_{len(trace) + 1:02d}.png"
    page.screenshot(path=str(output_dir / screenshot_name))
    trace.append({
        "action": {"type": "click", "x": x, "y": y},
        "script_target": test_id,
        "observation": screenshot_name,
    })


def run_task(page, task):
    output_dir = (
        PROJECT_DIR
        / "artifacts"
        / "settings_scripted"
        / task["task_id"]
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    page.evaluate(
        "(state) => window.resetSettingsTask(state)",
        task["initial_state"],
    )
    page.screenshot(path=str(output_dir / "step_00.png"))

    trace = []
    click_test_id(page, f"nav-{task['section']}", trace, output_dir)
    click_test_id(page, task["control_test_id"], trace, output_dir)
    click_test_id(page, "save-changes", trace, output_dir)
    click_test_id(page, "confirm-apply", trace, output_dir)
    trace.append({"action": {"type": "finish"}})

    state = page.evaluate("() => window.getSettingsEvaluationState()")
    success = (
        state["saved"][task["target_key"]] == task["target_value"]
        and state["has_unapplied_changes"] is False
        and state["confirmation_visible"] is False
    )

    result = {
        "task": task,
        "success": success,
        "termination_reason": "agent_finish",
        "steps": len(trace),
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
            viewport={"width": 960, "height": 640},
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

        browser.close()

    print("All settings-app scripted checks passed.")


if __name__ == "__main__":
    main()
