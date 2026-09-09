from itertools import islice

from datasets import load_dataset

from evaluate import point_in_bbox


NUM_SAMPLES = 10


def bbox_center(bbox):
    """Return the center point of a bounding box."""
    x1, y1, x2, y2 = bbox

    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2

    return [center_x, center_y]


def main():
    dataset = load_dataset(
        "bevaya/ScreenSpot",
        split="test",
        streaming=True,
    )

    correct = 0
    total = 0

    for index, sample in enumerate(islice(dataset, NUM_SAMPLES)):
        bbox = sample["bbox"]

        # Oracle prediction: deliberately uses the ground-truth bbox.
        predicted_point = bbox_center(bbox)

        is_correct = point_in_bbox(predicted_point, bbox)

        correct += int(is_correct)
        total += 1

        print(
            f"Sample {index}: "
            f"instruction={sample['instruction']!r}, "
            f"prediction={predicted_point}, "
            f"correct={is_correct}"
        )

    accuracy = correct / total

    print(f"\nCorrect: {correct}/{total}")
    print(f"Accuracy: {accuracy:.2%}")

    assert accuracy == 1.0
    print("Oracle sanity check passed")


if __name__ == "__main__":
    main()