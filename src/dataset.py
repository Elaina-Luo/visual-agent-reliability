from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from datasets import load_dataset


OUTPUT_PATH = Path("results/screenspot_sample_0.png")


def main():
    print("Loading ScreenSpot...")

    dataset = load_dataset(
        "bevaya/ScreenSpot",
        split="test",
        streaming=True,
    )

    sample = next(iter(dataset))

    image = sample["image"].convert("RGB")
    width, height = image.size

    # ScreenSpot stores normalized bbox coordinates:
    # [x1, y1, x2, y2], where each value is between 0 and 1.
    x1_norm, y1_norm, x2_norm, y2_norm = sample["bbox"]

    x1 = x1_norm * width
    y1 = y1_norm * height
    x2 = x2_norm * width
    y2 = y2_norm * height

    print(f"Instruction: {sample['instruction']}")
    print(f"Normalized bbox: {sample['bbox']}")
    print(f"Image size: {image.size}")
    print(f"Pixel bbox: [{x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f}]")

    figure, axis = plt.subplots(figsize=(12, 7))

    axis.imshow(image)

    target_box = Rectangle(
        (x1, y1),
        x2 - x1,
        y2 - y1,
        linewidth=3,
        edgecolor="red",
        facecolor="none",
    )

    axis.add_patch(target_box)
    axis.set_title(f"Instruction: {sample['instruction']}")
    axis.axis("off")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(OUTPUT_PATH, bbox_inches="tight")

    print(f"Saved visualization to: {OUTPUT_PATH}")

    plt.show()


if __name__ == "__main__":
    main()