from collections import Counter


PROGRESS_LABELS = (
    "progress",
    "regression",
    "irrelevant",
    "no_effect",
    "complete",
)


UNRELATED_CONTROLS = {
    "appearance": {
        "kind": "segment_alternative",
        "key": "theme",
        "values": ("light", "dark"),
    },
    "notifications": {
        "kind": "switch",
        "key": "push_notifications",
    },
    "privacy": {
        "kind": "switch",
        "key": "crash_reports",
    },
}


def transition_id(task, label):
    return f"{task['task_id']}__{label}"


def build_transition_specs(tasks):
    """Build one deterministic sample per task and progress label."""
    return [
        {
            "sample_id": transition_id(task, label),
            "label": label,
            "task": task,
        }
        for task in tasks
        for label in PROGRESS_LABELS
    ]


def label_counts(specs):
    return Counter(spec["label"] for spec in specs)


def validate_balanced_specs(specs):
    counts = label_counts(specs)
    if set(counts) != set(PROGRESS_LABELS):
        raise ValueError("Transition specs must contain every progress label")
    if len(set(counts.values())) != 1:
        raise ValueError(f"Transition specs are not balanced: {dict(counts)}")
    return counts


def nav_selector(task):
    return f'[data-testid="nav-{task["section"]}"]'


def target_selector(task):
    return f'[data-testid="{task["control_test_id"]}"]'


def regression_selector(task):
    if task["target_key"] == "density":
        return '[data-control="density"] [data-value="comfortable"]'
    return target_selector(task)


def unrelated_selector(task, current_draft):
    control = UNRELATED_CONTROLS[task["section"]]
    if control["kind"] == "switch":
        return f'.switch[data-key="{control["key"]}"]'

    current_value = current_draft[control["key"]]
    next_value = next(
        value for value in control["values"] if value != current_value
    )
    return (
        f'[data-control="{control["key"]}"] '
        f'[data-value="{next_value}"]'
    )
