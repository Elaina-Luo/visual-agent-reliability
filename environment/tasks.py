import random


def generate_task(seed: int) -> dict:
    rng = random.Random(seed)

    colors = {
        "red": "#dc2626",
        "blue": "#2563eb",
        "green": "#16a34a",
    }
    shapes = ["circle", "square", "triangle"]

    # Build nine unique color-shape combinations.
    candidates = []

    for color_name, color_value in colors.items():
        for shape in shapes:
            candidates.append({
                "id": f"obj_{len(candidates)}",
                "color_name": color_name,
                "color": color_value,
                "shape": shape,
            })

    # Choose six objects in a randomized display order.
    objects = rng.sample(candidates, k=6)

    # Choose two distinct targets from the displayed objects.
    targets = rng.sample(objects, k=2)

    descriptions = [
        f"the {obj['color_name']} {obj['shape']}"
        for obj in targets
    ]

    return {
        "seed": seed,
        "objects": objects,
        "goal": f"Select {' and '.join(descriptions)}, then submit.",
        "target_ids": [obj["id"] for obj in targets],
    }