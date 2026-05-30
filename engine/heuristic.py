"""
engine/heuristic.py
-------------------
Implements the admissible heuristic h(n) used in the A* search.

h(n) estimates the minimum remaining cost to reach the goal from state n.

HEURISTIC DESIGN
================
We combine two sources of remaining cost:

  1. Remaining delivery cost
     Each unit of bouquet still needed by any pavilion will require at
     least 1 unload action.  Summing all remaining quantities gives a
     lower bound on the unload actions still needed.

  2. Travel cost lower bound
     If any pavilion still has unmet needs, the robot must travel to it
     at least once.  We use the Manhattan distance from the current robot
     position to the *nearest* pavilion that still needs delivery.
     This is admissible because Manhattan distance never overestimates
     movement cost on a grid (cost = 1 per step).

  h(n) = remaining_units + distance_to_nearest_needy_pavilion

WHY ADMISSIBLE?
Both components are lower bounds:
  • remaining_units ≤ actual unload actions needed.
  • nearest-pavilion distance ≤ actual travel steps needed.
  • We never overestimate → h is admissible → A* finds optimal path.

The heuristic does NOT account for loading steps (also a lower bound),
keeping it simple and clearly admissible.
"""

from typing import List, Dict
from utils.helpers import manhattan_distance, pavilions_still_needing


def compute_heuristic(
    robot_x: int,
    robot_y: int,
    needs: Dict[str, List[Dict]],
    pavilion_positions: Dict[str, Dict],   # {pavilion_id: {"x": int, "y": int}}
) -> float:
    """Compute h(n) for the current state.

    Args:
        robot_x, robot_y: current robot position
        needs: {pavilion_id -> list of {flower, color, quantity}}
        pavilion_positions: lookup table of pavilion coordinates

    Returns:
        A non-negative float representing the estimated remaining cost.
    """
    # -----------------------------------------------------------------------
    # Component 1: total remaining bouquet units to deliver
    # -----------------------------------------------------------------------
    remaining_units = 0
    for blist in needs.values():
        for b in blist:
            remaining_units += b["quantity"]

    # If nothing left to deliver, heuristic is 0
    if remaining_units == 0:
        return 0.0

    # -----------------------------------------------------------------------
    # Component 2: Manhattan distance to nearest pavilion still needing delivery
    # -----------------------------------------------------------------------
    needy_ids = pavilions_still_needing(needs)

    if not needy_ids:
        return 0.0  # no needy pavilions → goal reached

    min_dist = min(
        manhattan_distance(
            robot_x, robot_y,
            pavilion_positions[pid]["x"],
            pavilion_positions[pid]["y"],
        )
        for pid in needy_ids
        if pid in pavilion_positions
    )

    # -----------------------------------------------------------------------
    # Combined lower bound
    # -----------------------------------------------------------------------
    return float(remaining_units + min_dist)
