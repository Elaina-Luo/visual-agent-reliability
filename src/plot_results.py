from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def save_grouped_bar(
    csv_name: str,
    output_name: str,
    index_column: str,
    title: str,
    x_label: str,
) -> None:
    table = pd.read_csv(RESULTS / csv_name).set_index(index_column)
    plot_data = table[["Native resolution", "Capped resolution"]]

    axis = plot_data.plot(
        kind="bar",
        figsize=(9, 5),
        width=0.72,
        color=["#4C78A8", "#F58518"],
    )
    axis.set_title(title, fontsize=14)
    axis.set_xlabel(x_label)
    axis.set_ylabel("Accuracy (%)")
    axis.set_ylim(0, 100)
    axis.legend(title="Input condition")
    axis.grid(axis="y", linestyle="--", alpha=0.3)
    axis.tick_params(axis="x", rotation=0)

    for container in axis.containers:
        axis.bar_label(container, fmt="%.1f", padding=3, fontsize=9)

    plt.tight_layout()
    plt.savefig(RESULTS / output_name, dpi=200, bbox_inches="tight")
    plt.close()


def main() -> None:
    save_grouped_bar(
        csv_name="accuracy_by_target_size.csv",
        output_name="accuracy_by_target_size.png",
        index_column="size_group",
        title="GUI Grounding Accuracy by Target Size",
        x_label="Target size group",
    )
    save_grouped_bar(
        csv_name="accuracy_by_target_type.csv",
        output_name="accuracy_by_target_type.png",
        index_column="data_type",
        title="GUI Grounding Accuracy by Target Type",
        x_label="Target type",
    )
    print(f"Saved plots to {RESULTS}")


if __name__ == "__main__":
    main()
