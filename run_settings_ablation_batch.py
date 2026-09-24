import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from environment.settings_tasks import generate_settings_task
from run_settings_agent import PROJECT_DIR, VIEWPORT, run_episode
from src.settings_ablation_summary import summarize_run
from src.settings_executor import VALID_FAULT_MODES


DEFAULT_OUTPUT_ROOT = PROJECT_DIR / "artifacts" / "settings_ablation_runs"


def parse_seeds(value):
    seeds = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            raise ValueError("Empty seed item")
        if ":" in item:
            parts = item.split(":")
            if len(parts) not in {2, 3}:
                raise ValueError(f"Invalid seed range: {item}")
            numbers = [int(part) for part in parts]
            selected = range(*numbers)
            if not selected:
                raise ValueError(f"Empty seed range: {item}")
            seeds.extend(selected)
        else:
            seeds.append(int(item))
    if any(seed < 0 for seed in seeds):
        raise ValueError("Seeds must be non-negative")
    return list(dict.fromkeys(seeds))


def result_path(run_dir, arm, fault_mode, task_id):
    strategy_dir = "settings_agent" if arm == "A" else f"settings_clean_{arm}"
    return Path(run_dir) / strategy_dir / fault_mode / task_id / "result.json"


def build_plan(seeds, fault_modes, arms, run_dir, resume=False):
    plan = []
    for seed in seeds:
        task = generate_settings_task(seed)
        for fault_mode in fault_modes:
            for arm in arms:
                path = result_path(run_dir, arm, fault_mode, task["task_id"])
                if resume and path.exists():
                    continue
                plan.append({
                    "seed": seed,
                    "task": task,
                    "fault_mode": fault_mode,
                    "arm": arm,
                    "result_path": path,
                })
    return plan


def prepare_run_dir(output_root, run_id, resume=False):
    run_dir = Path(output_root) / run_id
    if run_dir.exists() and not resume:
        raise FileExistsError(
            f"Run already exists: {run_dir}. Choose a new --run-id or use --resume."
        )
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_or_validate_manifest(run_dir, manifest, resume=False):
    path = Path(run_dir) / "manifest.json"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        comparable_fields = (
            "run_id", "seeds", "fault_modes", "arms", "max_steps", "model_id"
        )
        mismatches = [
            field for field in comparable_fields
            if existing.get(field) != manifest.get(field)
        ]
        if mismatches:
            raise ValueError(
                "Resume configuration differs from manifest: "
                + ", ".join(mismatches)
            )
        if resume:
            return existing
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--seeds", default="0:12",
        help="Comma-separated seeds/ranges; e.g. 0:12 or 0,2,5:8",
    )
    parser.add_argument(
        "--fault-modes", nargs="+", choices=sorted(VALID_FAULT_MODES),
        default=sorted(VALID_FAULT_MODES),
    )
    parser.add_argument(
        "--arms", nargs="+", choices=["A", "B", "C"],
        default=["A", "B", "C"],
    )
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--model-id", default=None)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    seeds = parse_seeds(args.seeds)
    run_id = args.run_id or datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    run_dir = prepare_run_dir(args.output_root, run_id, args.resume)
    plan = build_plan(
        seeds, args.fault_modes, args.arms, run_dir, args.resume
    )
    manifest = {
        "run_id": run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "seeds": seeds,
        "fault_modes": args.fault_modes,
        "arms": args.arms,
        "max_steps": args.max_steps,
        "model_id": args.model_id,
        "planned_episode_count": len(seeds) * len(args.fault_modes) * len(args.arms),
    }
    write_or_validate_manifest(run_dir, manifest, args.resume)

    if not plan:
        print("All requested episodes already exist.")
        summarize_run(run_dir)
        return

    from playwright.sync_api import sync_playwright
    from src.qwen_settings_agent import DEFAULT_MODEL_ID, QwenSettingsAgent
    from src.qwen_settings_verifier import QwenSettingsVerifier

    model_id = args.model_id or DEFAULT_MODEL_ID
    print("Loading model once:", model_id)
    actor = QwenSettingsAgent(model_id)
    verifier = QwenSettingsVerifier(actor)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed)
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=1)
        page.goto((PROJECT_DIR / "environment" / "settings.html").as_uri())
        for index, item in enumerate(plan, start=1):
            print(
                f"[{index}/{len(plan)}] seed={item['seed']} "
                f"fault={item['fault_mode']} arm={item['arm']}"
            )
            result = run_episode(
                page=page,
                agent=actor,
                verifier=verifier if item["arm"] != "A" else None,
                task=item["task"],
                fault_mode=item["fault_mode"],
                max_steps=args.max_steps,
                strategy=item["arm"],
                output_root=run_dir,
            )
            print(
                "  success=", result["task_state_success"],
                " correct_stop=", result["agent_terminated_correctly"],
                " termination=", result["termination_reason"],
                sep="",
            )
            summarize_run(run_dir)
        browser.close()

    summary = summarize_run(run_dir)
    print("Completed episodes:", summary["episode_count"])
    print("Results:", run_dir)


if __name__ == "__main__":
    main()
