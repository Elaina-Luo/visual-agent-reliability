import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from environment.tasks import generate_task


PROJECT_DIR = Path(__file__).resolve().parent
MAX_STEPS = 12
FAULT_NONE = "none"
FAULT_DROP_FIRST_CARD_CLICK = "drop_first_card_click"
VALID_FAULT_MODES = {FAULT_NONE, FAULT_DROP_FIRST_CARD_CLICK}


def validate_action(action):
    if not isinstance(action, dict):
        return "Action must be a dictionary."

    if action.get("type") == "finish":
        if set(action) != {"type"}:
            return "Finish must only contain type."
        return None

    if action.get("type") == "click":
        if set(action) != {"type", "x", "y"}:
            return "Click requires type, x, and y."

        x, y = action["x"], action["y"]

        # Reject booleans and other non-integer values.
        if type(x) is not int or type(y) is not int:
            return "Coordinates must be integers."

        if not (0 <= x < 960 and 0 <= y < 640):
            return "Coordinates are outside the viewport."

        return None

    return "Unknown action type."


def evaluate(state, target_ids, termination_reason):
    submitted = state["submitted_ids"]

    return (
        termination_reason == "agent_finish"
        and submitted is not None
        and set(submitted) == set(target_ids)
    )


def click_hits_card(page, action):
    return page.evaluate(
        """
        ([x, y]) => {
            const element = document.elementFromPoint(x, y);
            return Boolean(element && element.closest("button.card"));
        }
        """,
        [action["x"], action["y"]],
    )


def run_episode(page, task, actions, name, fault_mode=FAULT_NONE):
    if fault_mode not in VALID_FAULT_MODES:
        raise ValueError(f"Unknown fault mode: {fault_mode}")

    output_dir = PROJECT_DIR / "artifacts" / "scripted" / name
    output_dir.mkdir(parents=True, exist_ok=True)

    display_objects = [
        {
            "id": obj["id"],
            "color": obj["color"],
            "shape": obj["shape"],
        }
        for obj in task["objects"]
    ]

    page.evaluate(
        "(objects) => window.resetTask(objects)",
        display_objects,
    )
    page.screenshot(path=str(output_dir / "step_00.png"))

    trace = []
    termination_reason = "script_exhausted"
    fault_triggered = False

    for step, action in enumerate(actions[:MAX_STEPS], start=1):
        error = validate_action(action)
        state_before = page.evaluate("() => window.getEvaluationState()")
        execution_status = "rejected"
        fault_triggered_this_step = False

        if error is None:
            if action["type"] == "finish":
                termination_reason = "agent_finish"
                execution_status = "finished"
            else:
                should_drop = (
                    fault_mode == FAULT_DROP_FIRST_CARD_CLICK
                    and not fault_triggered
                    and click_hits_card(page, action)
                )

                if should_drop:
                    fault_triggered = True
                    fault_triggered_this_step = True
                    execution_status = "dropped_by_fault"
                else:
                    page.mouse.click(action["x"], action["y"])
                    execution_status = "executed"

        # Advance rendering without checking whether the action succeeded.
        page.evaluate("""
            () => new Promise(resolve => {
                requestAnimationFrame(() => {
                    requestAnimationFrame(() => resolve());
                });
            })
        """)

        state_after = page.evaluate("() => window.getEvaluationState()")

        screenshot_name = f"step_{step:02d}.png"
        page.screenshot(path=str(output_dir / screenshot_name))

        trace.append({
            "step": step,
            "action": action,
            "validation_error": error,
            "execution_status": execution_status,
            "fault_triggered": fault_triggered_this_step,
            "observation": screenshot_name,
            # Evaluator-only audit fields. Never include these in Agent input.
            "evaluator_state_before": state_before,
            "evaluator_state_after": state_after,
        })

        if termination_reason == "agent_finish":
            break

        if step == MAX_STEPS:
            termination_reason = "budget_exhausted"

    # Read hidden state only for evaluation after the episode.
    state = page.evaluate("() => window.getEvaluationState()")

    result = {
        "case": name,
        "success": evaluate(
            state, task["target_ids"], termination_reason
        ),
        "termination_reason": termination_reason,
        "steps": len(trace),
        "fault_mode": fault_mode,
        "fault_triggered": fault_triggered,
        "final_state": state,
        "target_ids": task["target_ids"],
        "trace": trace,
    }

    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    return result


def main():
    task = generate_task(seed=0)
    print("Goal:", task["goal"])

    # Coordinates for the current fixed CSS layout.
    red_triangle = {"type": "click", "x": 190, "y": 360}
    red_circle = {"type": "click", "x": 750, "y": 190}
    green_circle = {"type": "click", "x": 190, "y": 190}
    submit = {"type": "click", "x": 120, "y": 485}
    finish = {"type": "finish"}

    correct = [red_triangle, red_circle, submit, finish]

    cases = [
        ("correct", correct, True),
        ("missing_object", [red_triangle, submit, finish], False),
        (
            "extra_object",
            [red_triangle, red_circle, green_circle, submit, finish],
            False,
        ),
        ("no_submission", [red_triangle, red_circle, finish], False),
        ("no_finish", [red_triangle, red_circle, submit], False),
        (
            "budget_exhausted",
            [{"type": "click", "x": 10, "y": 10}] * 12 + [finish],
            False,
        ),
        (
            "invalid_then_correct",
            [{"type": "click", "x": -1, "y": 100}] + correct,
            True,
        ),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(
            viewport={"width": 960, "height": 640},
            device_scale_factor=1,
        )

        page.goto(
            (PROJECT_DIR / "environment" / "index.html").as_uri()
        )

        for name, actions, expected_success in cases:
            result = run_episode(page, task, actions, name)

            print(
                f"{name}: success={result['success']}, "
                f"steps={result['steps']}, "
                f"reason={result['termination_reason']}"
            )

            assert result["success"] == expected_success, (
                f"Unexpected result in {name}. Inspect its screenshots."
            )

        no_retry = run_episode(
            page,
            task,
            correct,
            "fault_drop_without_retry",
            fault_mode=FAULT_DROP_FIRST_CARD_CLICK,
        )
        first_step = no_retry["trace"][0]

        assert no_retry["fault_triggered"] is True
        assert first_step["execution_status"] == "dropped_by_fault"
        assert (
            first_step["evaluator_state_before"]
            == first_step["evaluator_state_after"]
        ), "A dropped click must leave the page state unchanged."
        assert no_retry["success"] is False

        retry_actions = [
            red_triangle,
            red_triangle,
            red_circle,
            submit,
            finish,
        ]
        with_retry = run_episode(
            page,
            task,
            retry_actions,
            "fault_drop_with_scripted_retry",
            fault_mode=FAULT_DROP_FIRST_CARD_CLICK,
        )

        assert with_retry["fault_triggered"] is True
        assert with_retry["success"] is True

        print(
            "fault_drop_without_retry: "
            f"success={no_retry['success']}, "
            f"fault_triggered={no_retry['fault_triggered']}"
        )
        print(
            "fault_drop_with_scripted_retry: "
            f"success={with_retry['success']}, "
            f"fault_triggered={with_retry['fault_triggered']}"
        )

        browser.close()

    print("All scripted checks passed.")


if __name__ == "__main__":
    main()
