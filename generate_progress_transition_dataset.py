import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from environment.settings_tasks import generate_settings_task
from src.progress_audit import classify_settings_transition
from src.progress_transition_dataset import (
    build_transition_specs,
    nav_selector,
    regression_selector,
    target_selector,
    unrelated_selector,
    validate_balanced_specs,
)
from src.settings_executor import wait_for_render


PROJECT_DIR = Path(__file__).resolve().parent
VIEWPORT = {"width": 980, "height": 644}


def evaluation_state(page):
    return page.evaluate("() => window.getSettingsEvaluationState()")


def click_and_settle(page, selector):
    page.locator(selector).click()
    page.wait_for_timeout(180)


def click_action_for(page, selector):
    box = page.locator(selector).bounding_box()
    if box is None:
        raise RuntimeError(f"Control is not visible: {selector}")
    return {
        "type": "click",
        "x": round(box["x"] + box["width"] / 2),
        "y": round(box["y"] + box["height"] / 2),
    }


def prepare_transition(page, task, label):
    page.evaluate(
        "(state) => window.resetSettingsTask(state)",
        task["initial_state"],
    )
    wait_for_render(page)
    click_and_settle(page, nav_selector(task))

    if label == "regression":
        click_and_settle(page, target_selector(task))
        return regression_selector(task)

    if label == "irrelevant":
        state = evaluation_state(page)
        return unrelated_selector(task, state["draft"])

    if label == "complete":
        click_and_settle(page, target_selector(task))
        click_and_settle(page, '[data-testid="save-changes"]')
        return '[data-testid="confirm-apply"]'

    if label == "no_effect":
        # The heading is visible but has no click handler.
        return "#page-title"

    if label == "progress":
        return target_selector(task)

    raise ValueError(f"Unknown transition label: {label}")


def generate_sample(page, output_dir, spec):
    task = spec["task"]
    label = spec["label"]
    sample_dir = output_dir / spec["sample_id"]
    sample_dir.mkdir(parents=True, exist_ok=True)

    action_selector = prepare_transition(page, task, label)
    requested_action = click_action_for(page, action_selector)
    before_state = evaluation_state(page)
    page.screenshot(path=str(sample_dir / "before.png"), type="png")

    page.mouse.click(requested_action["x"], requested_action["y"])
    page.wait_for_timeout(180)

    after_state = evaluation_state(page)
    page.screenshot(path=str(sample_dir / "after.png"), type="png")
    audit_label = classify_settings_transition(before_state, after_state, task)
    if audit_label != label:
        raise RuntimeError(
            f"{spec['sample_id']}: expected {label}, audited {audit_label}"
        )

    public_record = {
        "sample_id": spec["sample_id"],
        "task_id": task["task_id"],
        "seed": task["seed"],
        "goal": task["goal"],
        "requested_action": requested_action,
        "before_screenshot": f"{spec['sample_id']}/before.png",
        "after_screenshot": f"{spec['sample_id']}/after.png",
        "label": label,
    }
    audit_record = {
        "sample_id": spec["sample_id"],
        "label": label,
        "before_state": before_state,
        "after_state": after_state,
    }
    return public_record, audit_record


def generate_dataset(page, output_dir, tasks):
    specs = build_transition_specs(tasks)
    counts = validate_balanced_specs(specs)
    records = []
    audit_records = []
    for spec in specs:
        public_record, audit_record = generate_sample(page, output_dir, spec)
        records.append(public_record)
        audit_records.append(audit_record)

    manifest = {
        "dataset": "settings_goal_progress_controlled_v1",
        "labels": list(counts),
        "samples_per_label": next(iter(counts.values())),
        "sample_count": len(records),
        "records": records,
    }
    audit_manifest = {
        "warning": "Evaluator-only state; never include in model prompts.",
        "records": audit_records,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    (output_dir / "audit_manifest.json").write_text(
        json.dumps(audit_manifest, indent=2),
        encoding="utf-8",
    )
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            PROJECT_DIR / "artifacts" / "progress_transition_dataset_v1"
        ),
    )
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = [generate_settings_task(seed) for seed in range(3)]

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed)
        page = browser.new_page(
            viewport=VIEWPORT,
            device_scale_factor=1,
        )
        page.goto(
            (PROJECT_DIR / "environment" / "settings.html").as_uri()
        )
        manifest = generate_dataset(page, output_dir, tasks)
        browser.close()

    print("Dataset:", manifest["dataset"])
    print("Samples:", manifest["sample_count"])
    print("Samples per label:", manifest["samples_per_label"])
    print("Saved:", output_dir / "manifest.json")


if __name__ == "__main__":
    main()
