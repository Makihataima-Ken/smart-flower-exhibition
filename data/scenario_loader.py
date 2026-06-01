import json
from pathlib import Path


def compute_capacity(pavilions):
    """
    Capacity = largest pavilion demand.
    """

    return max(
        sum(item["quantity"] for item in pavilion["needs"])
        for pavilion in pavilions
    )


def load_scenario(path):
    """
    Load scenario JSON and enrich it with derived values.
    """

    path = Path(path)

    with open(path, "r", encoding="utf-8") as f:
        scenario = json.load(f)

    scenario["robot_capacity"] = compute_capacity(
        scenario["pavilions"]
    )

    return scenario