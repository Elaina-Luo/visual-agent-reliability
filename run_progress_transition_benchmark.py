import argparse
import json
from pathlib import Path

from PIL import Image

from src.progress_benchmark_metrics import (
    plot_confusion_matrix,
    summarize_progress_predictions,
    write_confusion_csv,
)
from src.progress_verifier_parser import parse_progress_verification
from src.progress_verifier_prompt import (
    P0_PROMPT_VERSION,
    P1_PROMPT_VERSION,
    PROGRESS_PROMPT_VERSIONS,
)
from src.qwen_progress_verifier import QwenProgressVerifier
from src.qwen_settings_agent import DEFAULT_MODEL_ID, QwenSettingsAgent


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_MANIFEST = (
    PROJECT_DIR
    / "artifacts"
    / "progress_transition_dataset_v1"
    / "manifest.json"
)


def load_rgb(path):
    with Image.open(path) as image:
        return image.convert("RGB")


def load_existing_records(
    output_path,
    resume,
    dataset_name,
    model_id,
    prompt_version,
):
    if not resume or not output_path.exists():
        return []
    result = json.loads(output_path.read_text(encoding="utf-8"))
    if result.get("prompt_version") != prompt_version:
        raise ValueError("Cannot resume results from another prompt version")
    if result.get("dataset") != dataset_name:
        raise ValueError("Cannot resume results from another dataset")
    if result.get("model_id") != model_id:
        raise ValueError("Cannot resume results from another model")
    return result.get("records", [])


def build_result(manifest_path, manifest, verifier, records):
    metrics = summarize_progress_predictions(records)
    return {
        "dataset": manifest["dataset"],
        "source_manifest": str(manifest_path),
        "model_id": verifier.model_id,
        "prompt_version": verifier.prompt_version,
        "mode": "offline_shadow_no_policy_control",
        "evaluated_samples": len(records),
        "total_samples": manifest["sample_count"],
        "total_latency_seconds": sum(
            record.get("latency_seconds") or 0.0 for record in records
        ),
        "metrics": metrics,
        "records": records,
    }


def save_checkpoint(output_path, result):
    output_path.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )


def evaluate_manifest(manifest_path, verifier, output_path, resume=False):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    dataset_dir = manifest_path.parent
    records = load_existing_records(
        output_path,
        resume,
        manifest["dataset"],
        verifier.model_id,
        verifier.prompt_version,
    )
    completed_ids = {record["sample_id"] for record in records}

    for sample in manifest["records"]:
        if sample["sample_id"] in completed_ids:
            print(f"Skip {sample['sample_id']} (checkpoint)")
            continue

        before_image = load_rgb(dataset_dir / sample["before_screenshot"])
        after_image = load_rgb(dataset_dir / sample["after_screenshot"])
        raw_output = None
        latency_seconds = None
        try:
            raw_output, latency_seconds = verifier.verify(
                before_image=before_image,
                after_image=after_image,
                goal=sample["goal"],
                requested_action=sample["requested_action"],
            )
            predicted_label = parse_progress_verification(raw_output)[
                "status"
            ]
            error = None
        except Exception as exception:
            predicted_label = "uncertain"
            error = f"{type(exception).__name__}: {exception}"

        # Read the reference only after inference. It is never passed to Qwen.
        reference_label = sample["label"]
        record = {
            "sample_id": sample["sample_id"],
            "task_id": sample["task_id"],
            "reference_label": reference_label,
            "predicted_label": predicted_label,
            "correct": predicted_label == reference_label,
            "raw_output": raw_output,
            "latency_seconds": latency_seconds,
            "error": error,
        }
        records.append(record)
        result = build_result(manifest_path, manifest, verifier, records)
        save_checkpoint(output_path, result)
        print(
            f"{len(records):02d}/{manifest['sample_count']} "
            f"{sample['sample_id']}: predicted={predicted_label} "
            f"reference={reference_label} correct={record['correct']}"
        )

    result = build_result(manifest_path, manifest, verifier, records)
    save_checkpoint(output_path, result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument(
        "--prompt-version",
        choices=PROGRESS_PROMPT_VERSIONS,
        default=P0_PROMPT_VERSION,
    )
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    output_path = (
        args.output.resolve()
        if args.output
        else manifest_path.with_name(
            "progress_benchmark_p1.json"
            if args.prompt_version == P1_PROMPT_VERSION
            else "progress_benchmark_p0.json"
        )
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print("Dataset:", manifest_path)
    print("Mode: offline shadow; no actions or recovery decisions")
    print("Prompt:", args.prompt_version)
    print("Loading model:", args.model_id)
    actor = QwenSettingsAgent(args.model_id)
    verifier = QwenProgressVerifier(
        actor,
        prompt_version=args.prompt_version,
    )
    result = evaluate_manifest(
        manifest_path,
        verifier,
        output_path,
        resume=args.resume,
    )

    prompt_tag = "p1" if args.prompt_version == P1_PROMPT_VERSION else "p0"
    matrix_path = output_path.with_name(
        f"progress_confusion_matrix_{prompt_tag}.csv"
    )
    figure_path = output_path.with_name(
        f"progress_confusion_matrix_{prompt_tag}.png"
    )
    write_confusion_csv(result["metrics"]["confusion_matrix"], matrix_path)
    plot_confusion_matrix(
        result["metrics"]["confusion_matrix"],
        figure_path,
    )

    metrics = result["metrics"]
    print("Accuracy:", metrics["accuracy"])
    print("Macro F1:", metrics["macro_f1"])
    print("Predictions:", metrics["prediction_distribution"])
    for label, values in metrics["per_class"].items():
        print(
            f"{label}: recall={values['recall']:.3f} "
            f"precision={values['precision']:.3f} "
            f"f1={values['f1']:.3f}"
        )
    print("Saved:", output_path)
    print("Matrix:", matrix_path)
    print("Figure:", figure_path)


if __name__ == "__main__":
    main()
