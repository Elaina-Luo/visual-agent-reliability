import argparse
from pathlib import Path

from src.settings_ablation_summary import summarize_run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()

    summary = summarize_run(args.run_dir)
    print("Episodes:", summary["episode_count"])
    for row in summary["aggregates"]:
        print(
            row["fault_mode"],
            row["arm"],
            f"n={row['episode_count']}",
            f"success={row['task_state_success_rate']:.3f}",
            f"correct_stop={row['agent_terminated_correctly_rate']:.3f}",
            f"false_stop={row['false_completion_termination_rate']:.3f}",
        )
    print("Saved:", args.run_dir / "summary.json")


if __name__ == "__main__":
    main()
