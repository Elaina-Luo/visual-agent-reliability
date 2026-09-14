import csv

from src.progress_transition_dataset import PROGRESS_LABELS


REFERENCE_LABELS = PROGRESS_LABELS
PREDICTION_LABELS = PROGRESS_LABELS + ("uncertain",)


def empty_confusion_matrix():
    return {
        reference: {prediction: 0 for prediction in PREDICTION_LABELS}
        for reference in REFERENCE_LABELS
    }


def safe_divide(numerator, denominator):
    return numerator / denominator if denominator else 0.0


def summarize_progress_predictions(records):
    matrix = empty_confusion_matrix()
    for record in records:
        reference = record["reference_label"]
        prediction = record["predicted_label"]
        if reference not in REFERENCE_LABELS:
            raise ValueError(f"Unknown reference label: {reference}")
        if prediction not in PREDICTION_LABELS:
            raise ValueError(f"Unknown predicted label: {prediction}")
        matrix[reference][prediction] += 1

    per_class = {}
    for label in REFERENCE_LABELS:
        true_positive = matrix[label][label]
        support = sum(matrix[label].values())
        predicted_count = sum(
            matrix[reference][label] for reference in REFERENCE_LABELS
        )
        precision = safe_divide(true_positive, predicted_count)
        recall = safe_divide(true_positive, support)
        per_class[label] = {
            "support": support,
            "correct": true_positive,
            "precision": precision,
            "recall": recall,
            "f1": safe_divide(2 * precision * recall, precision + recall),
        }

    sample_count = len(records)
    correct_count = sum(
        record["reference_label"] == record["predicted_label"]
        for record in records
    )
    prediction_distribution = {
        label: sum(
            matrix[reference][label] for reference in REFERENCE_LABELS
        )
        for label in PREDICTION_LABELS
    }
    return {
        "sample_count": sample_count,
        "correct_count": correct_count,
        "accuracy": safe_divide(correct_count, sample_count),
        "macro_f1": safe_divide(
            sum(metrics["f1"] for metrics in per_class.values()),
            len(REFERENCE_LABELS),
        ),
        "uncertain_count": prediction_distribution["uncertain"],
        "prediction_distribution": prediction_distribution,
        "per_class": per_class,
        "confusion_matrix": matrix,
        "error_sample_ids": [
            record["sample_id"]
            for record in records
            if record["reference_label"] != record["predicted_label"]
        ],
    }


def write_confusion_csv(matrix, output_path):
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["reference\\predicted", *PREDICTION_LABELS])
        for reference in REFERENCE_LABELS:
            writer.writerow([
                reference,
                *(matrix[reference][label] for label in PREDICTION_LABELS),
            ])


def plot_confusion_matrix(matrix, output_path):
    import matplotlib.pyplot as plt

    values = [
        [matrix[reference][prediction] for prediction in PREDICTION_LABELS]
        for reference in REFERENCE_LABELS
    ]
    figure, axis = plt.subplots(figsize=(9.0, 6.2))
    image = axis.imshow(values, cmap="Blues", vmin=0)
    axis.set_xticks(range(len(PREDICTION_LABELS)), PREDICTION_LABELS)
    axis.set_yticks(range(len(REFERENCE_LABELS)), REFERENCE_LABELS)
    axis.set_xlabel("Predicted label")
    axis.set_ylabel("Reference label")
    axis.set_title("Goal-Progress Verifier P0 confusion matrix")
    plt.setp(axis.get_xticklabels(), rotation=35, ha="right")

    maximum = max((value for row in values for value in row), default=0)
    for row_index, row in enumerate(values):
        for column_index, value in enumerate(row):
            axis.text(
                column_index,
                row_index,
                str(value),
                ha="center",
                va="center",
                color="white" if maximum and value > maximum / 2 else "black",
            )

    figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    figure.tight_layout()
    figure.savefig(output_path, dpi=180)
    plt.close(figure)
