import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from environment.tasks import generate_task


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    task = generate_task(args.seed)

    project_dir = Path(__file__).resolve().parent
    page_path = project_dir / "environment" / "index.html"
    output_dir = project_dir / "artifacts" / f"seed_{args.seed}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save the full task for reproducibility, not for Agent input.
    (output_dir / "task.json").write_text(
        json.dumps(task, indent=2),
        encoding="utf-8",
    )

    # The page needs object appearance, but not the correct answer.
    display_objects = [
        {
            "id": obj["id"],
            "color": obj["color"],
            "shape": obj["shape"],
        }
        for obj in task["objects"]
    ]

    print(f"Seed: {task['seed']}")
    print(f"Goal: {task['goal']}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(
            viewport={"width": 960, "height": 640},
            device_scale_factor=1,
        )

        page.goto(page_path.as_uri())

        page.evaluate(
            "(objects) => window.resetTask(objects)",
            display_objects,
        )
        page.screenshot(path=str(output_dir / "initial.png"))

        input("Select objects and submit. Press Enter here to reset.")

        page.evaluate(
            "(objects) => window.resetTask(objects)",
            display_objects,
        )
        page.screenshot(path=str(output_dir / "reset.png"))

        input("Inspect the reset page. Press Enter here to close.")
        browser.close()


if __name__ == "__main__":
    main()