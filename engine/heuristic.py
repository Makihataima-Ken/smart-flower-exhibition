"""
engine/heuristic.py
-------------------
Admissible A* heuristic h(n).

  h(n) = total_remaining_units + manhattan_distance_to_nearest_needy_pavilion

Zero explicit if-statements or loops.
"""

from typing import List, Dict, Optional
from math import ceil
from utils.helpers import manhattan_distance, pavilions_still_needing


def compute_heuristic(
    robot_x: int,
    robot_y: int,
    inventory: List[Dict],
    needs: Dict[str, List[Dict]],
    pavilion_positions: Dict[str, Dict],
    warehouse_pos: Dict[str, int],
    capacity: Optional[int] = None,
) -> float:
    """Compute h(n) using the requested formula:

    h = manhattan_d(robot, warehouse)
        + (trips - 1) * (2 * D_avg + 2)
        + D_avg + 2

    Where:
      - trips = ceil(remaining_to_fetch / capacity)
      - remaining_to_fetch = max(0, total_needs - inventory_load)
      - D_avg = average Manhattan distance from warehouse to needy pavilions
    """

    # Totals
    total_needs = sum(b["quantity"] for blist in needs.values() for b in blist)
    inventory_load = sum(b["quantity"] for b in inventory or [])

    remaining_to_fetch = max(0, total_needs - inventory_load)

    # Derive capacity if not provided (safe fallback: largest pavilion demand)
    if capacity is None:
        capacity = max((sum(b["quantity"] for b in blist) for blist in needs.values()), default=1)

    # If nothing to fetch, heuristic is zero
    if remaining_to_fetch <= 0:
        return 0.0

    trips = max(1, ceil(remaining_to_fetch / float(max(1, capacity))))

    # Compute average distance from warehouse to needy pavilions
    needy_ids = pavilions_still_needing(needs)
    wh_x, wh_y = warehouse_pos.get("x", 0), warehouse_pos.get("y", 0)

    dists = [
        manhattan_distance(wh_x, wh_y, pavilion_positions[pid]["x"], pavilion_positions[pid]["y"])
        for pid in needy_ids
        if pid in pavilion_positions
    ]

    D_avg = (sum(dists) / len(dists)) if dists else 0.0

    h = (
        manhattan_distance(robot_x, robot_y, wh_x, wh_y)
        + (trips - 1) * (2 * D_avg + 2)
        + D_avg + 2
    )

    return float(h)
