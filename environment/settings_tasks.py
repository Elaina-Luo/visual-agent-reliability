import random


DEFAULT_SETTINGS = {
    "theme": "system",
    "density": "comfortable",
    "push_notifications": True,
    "sound_alerts": True,
    "weekly_summary": False,
    "analytics_sharing": True,
    "crash_reports": True,
    "activity_history": True,
}


TASK_SPECS = [
    {
        "section": "appearance",
        "target_key": "density",
        "target_value": "compact",
        "goal": "Open Appearance, select Compact density, and save the changes.",
        "control_test_id": "density-compact",
    },
    {
        "section": "notifications",
        "target_key": "sound_alerts",
        "target_value": False,
        "goal": "Open Notifications, turn off Sound alerts, and save the changes.",
        "control_test_id": "sound-alerts",
    },
    {
        "section": "privacy",
        "target_key": "analytics_sharing",
        "target_value": False,
        "goal": "Open Privacy, turn off Analytics sharing, and save the changes.",
        "control_test_id": "analytics-sharing",
    },
]


def generate_settings_task(seed: int) -> dict:
    rng = random.Random(seed)
    spec = TASK_SPECS[seed % len(TASK_SPECS)]
    initial_state = dict(DEFAULT_SETTINGS)

    # Randomize non-target settings without changing the target's required move.
    initial_state["theme"] = rng.choice(["light", "dark", "system"])
    initial_state["weekly_summary"] = rng.choice([True, False])
    initial_state["activity_history"] = rng.choice([True, False])

    target_key = spec["target_key"]
    target_value = spec["target_value"]
    if isinstance(target_value, bool):
        initial_state[target_key] = not target_value
    elif target_key == "density":
        initial_state[target_key] = "comfortable"

    return {
        "seed": seed,
        "task_id": f"settings_{seed:03d}_{target_key}",
        "goal": spec["goal"],
        "section": spec["section"],
        "target_key": target_key,
        "target_value": target_value,
        "control_test_id": spec["control_test_id"],
        "initial_state": initial_state,
    }
