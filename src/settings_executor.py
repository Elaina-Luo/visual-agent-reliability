FAULT_NONE = "none"
FAULT_DROP_FIRST_SETTING_CHANGE = "drop_first_setting_change"
VALID_FAULT_MODES = {
    FAULT_NONE,
    FAULT_DROP_FIRST_SETTING_CHANGE,
}


def new_fault_state():
    return {"triggered": False}


def wait_for_render(page):
    page.evaluate(
        """
        () => new Promise(resolve => {
            requestAnimationFrame(() => requestAnimationFrame(resolve));
        })
        """
    )


def click_hits_setting_control(page, x, y):
    return page.evaluate(
        """
        ([clickX, clickY]) => {
            const element = document.elementFromPoint(clickX, clickY);
            return Boolean(
                element && element.closest(".switch, .segment")
            );
        }
        """,
        [x, y],
    )


def execute_coordinate_click(page, x, y, fault_mode, fault_state):
    if fault_mode not in VALID_FAULT_MODES:
        raise ValueError(f"Unknown fault mode: {fault_mode}")

    state_before = page.evaluate(
        "() => window.getSettingsEvaluationState()"
    )
    should_drop = (
        fault_mode == FAULT_DROP_FIRST_SETTING_CHANGE
        and not fault_state["triggered"]
        and click_hits_setting_control(page, x, y)
    )

    if should_drop:
        fault_state["triggered"] = True
        execution_status = "dropped_by_fault"
    else:
        page.mouse.click(x, y)
        execution_status = "executed"

    wait_for_render(page)
    state_after = page.evaluate(
        "() => window.getSettingsEvaluationState()"
    )

    return {
        "action": {"type": "click", "x": x, "y": y},
        "execution_status": execution_status,
        "fault_triggered": should_drop,
        # Evaluator-only audit fields. Never include these in Agent input.
        "evaluator_state_before": state_before,
        "evaluator_state_after": state_after,
    }
