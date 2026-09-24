"""Metrics and tabular outputs for clean Settings A/B/C runs."""

import csv
import json
from collections import defaultdict
from pathlib import Path

from src.episode_evaluator import task_state_succeeded


ARMS = ("A", "B", "C")
RATE_FIELDS = (
    "task_state_success",
    "agent_terminated_correctly",
    "false_completion_termination",
)
MEAN_FIELDS = (
    "retry_count",
    "steps",
    "action_count",
    "click_count",
    "actor_latency_seconds",
    "verifier_latency_seconds",
)


def _mean(values):
    return sum(values) / len(values) if values else 0.0


def load_episode_results(run_dir):
    results = []
    for path in sorted(Path(run_dir).glob("**/result.json")):
        result = json.loads(path.read_text(encoding="utf-8"))
        if result.get("ablation_arm") not in ARMS:
            continue
        result["_result_path"] = str(path.relative_to(run_dir))
        results.append(result)
    return results


def episode_row(result):
    task = result["task"]
    complete_predictions = 0
    false_complete_predictions = 0
    for record in result.get("trace", []):
        verification = record.get("verification") or {}
        if verification.get("status") != "complete":
            continue
        complete_predictions += 1
        state_after = record.get("evaluator_state_after")
        if state_after is None:
            state_after = result["final_state"]
        if not task_state_succeeded(state_after, task):
            false_complete_predictions += 1

    termination_reason = result["termination_reason"]
    return {
        "seed": task["seed"],
        "task_id": task["task_id"],
        "target_key": task["target_key"],
        "fault_mode": result["fault_mode"],
        "arm": result["ablation_arm"],
        "task_state_success": int(result["task_state_success"]),
        "agent_terminated_correctly": int(
            result["agent_terminated_correctly"]
        ),
        "termination_reason": termination_reason,
        "false_completion_termination": int(
            termination_reason == "verifier_complete"
            and not result["task_state_success"]
        ),
        "retry_count": result.get("retry_count", 0),
        "steps": result["steps"],
        "action_count": result.get("action_count", 0),
        "click_count": result.get("click_count", 0),
        "actor_latency_seconds": result.get("actor_latency_seconds", 0.0),
        "verifier_latency_seconds": result.get(
            "verifier_latency_seconds", 0.0
        ),
        "verifier_complete_predictions": complete_predictions,
        "false_complete_predictions": false_complete_predictions,
        "result_path": result["_result_path"],
    }


def aggregate_rows(episode_rows):
    groups = defaultdict(list)
    for row in episode_rows:
        groups[(row["fault_mode"], row["arm"])].append(row)

    aggregates = []
    for (fault_mode, arm), rows in sorted(groups.items()):
        aggregate = {
            "fault_mode": fault_mode,
            "arm": arm,
            "episode_count": len(rows),
        }
        for field in RATE_FIELDS:
            aggregate[f"{field}_rate"] = _mean(
                [row[field] for row in rows]
            )
        for field in MEAN_FIELDS:
            aggregate[f"mean_{field}"] = _mean(
                [row[field] for row in rows]
            )
        aggregate["verifier_complete_predictions"] = sum(
            row["verifier_complete_predictions"] for row in rows
        )
        aggregate["false_complete_predictions"] = sum(
            row["false_complete_predictions"] for row in rows
        )
        aggregates.append(aggregate)
    return aggregates


def paired_rows(episode_rows):
    groups = defaultdict(dict)
    for row in episode_rows:
        groups[(row["seed"], row["fault_mode"])][row["arm"]] = row

    paired = []
    for (seed, fault_mode), arms in sorted(groups.items()):
        row = {"seed": seed, "fault_mode": fault_mode}
        for arm in ARMS:
            episode = arms.get(arm)
            row[f"{arm}_present"] = int(episode is not None)
            for field in (
                "task_state_success",
                "agent_terminated_correctly",
                "false_completion_termination",
                "retry_count",
                "steps",
                "termination_reason",
            ):
                row[f"{arm}_{field}"] = (
                    episode[field] if episode is not None else ""
                )
        row["C_minus_A_task_state_success"] = (
            arms["C"]["task_state_success"]
            - arms["A"]["task_state_success"]
            if "A" in arms and "C" in arms
            else ""
        )
        paired.append(row)
    return paired


def _write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def summarize_run(run_dir):
    run_dir = Path(run_dir)
    episodes = [episode_row(result) for result in load_episode_results(run_dir)]
    aggregates = aggregate_rows(episodes)
    pairs = paired_rows(episodes)
    summary = {
        "run_dir": str(run_dir),
        "episode_count": len(episodes),
        "episodes": episodes,
        "aggregates": aggregates,
        "paired": pairs,
    }
    _write_csv(run_dir / "episodes.csv", episodes)
    _write_csv(run_dir / "aggregate.csv", aggregates)
    _write_csv(run_dir / "paired.csv", pairs)
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary
