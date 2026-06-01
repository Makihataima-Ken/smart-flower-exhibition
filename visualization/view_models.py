"""ViewModel layer: convert internal StateNode objects into plain dicts
that the renderer can draw. This isolates Experta/search internals from
the visualization code.
"""
from typing import Dict, Any
from models.state import StateNode


def state_to_view_model(state: StateNode, scenario: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a StateNode into a rendering-friendly view model.

    Args:
        state: The StateNode (search-tree node) to convert.
        scenario: The scenario dict (from the scenario loader).

    Returns:
        A plain dict with keys used by the renderer.
    """
    vm = {
        "robot_position": (state.robot_x, state.robot_y),
        "inventory": [
            {"flower": b["flower"], "color": b["color"], "quantity": b["quantity"]}
            for b in state.inventory
        ],
        "remaining_needs": {
            pid: [
                {"flower": b["flower"], "color": b["color"], "quantity": b["quantity"]}
                for b in blist
            ]
            for pid, blist in state.needs.items()
        },
        "action": state.action,
        "g_cost": state.g_cost,
        "h_cost": state.h_cost,
        "f_cost": state.f_cost,
        # include scenario elements needed for layout
        "scenario_grid": scenario.get("grid", {}),
        "warehouse": scenario.get("warehouse", {}),
        "pavilions": scenario.get("pavilions", []),
        "robot_capacity": scenario.get("robot_capacity"),
    }

    return vm
