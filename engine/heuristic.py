"""
engine/heuristic.py
-------------------
Admissible A* heuristic h(n).

  h(n) = total_remaining_units + manhattan_distance_to_nearest_needy_pavilion

Zero explicit if-statements or loops.
"""

from typing import List, Dict
from utils.helpers import manhattan_distance, pavilions_still_needing


def compute_heuristic(
    robot_x: int,
    robot_y: int,
    needs: Dict[str, List[Dict]],
    pavilion_positions: Dict[str, Dict],
) -> float:
    """Compute h(n) for the current state."""

    remaining_units = sum(
        b["quantity"]
        for blist in needs.values()
        for b in blist
    )

    # Short-circuit: nothing left to deliver → h = 0
    needy_ids = pavilions_still_needing(needs)

    min_dist = (
        0
        if not needy_ids
        else min(
            manhattan_distance(
                robot_x, robot_y,
                pavilion_positions[pid]["x"],
                pavilion_positions[pid]["y"],
            )
            for pid in needy_ids
            if pid in pavilion_positions
        )
    )

    return float(remaining_units + min_dist)
