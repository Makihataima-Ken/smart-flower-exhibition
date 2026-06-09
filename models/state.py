"""
models/state.py
---------------
StateNode dataclass, global STATE_REGISTRY, and all helper functions
that work on states.

ZERO if-statements, ZERO explicit loops in this file.
All control flow expressed through comprehensions, builtins, and
short-circuit operators (:= walrus not needed; we use functional style).
"""

from dataclasses import dataclass
from typing import List, Dict, Optional


# ---------------------------------------------------------------------------
# StateNode
# ---------------------------------------------------------------------------
@dataclass
class StateNode:
    """One node in the search tree, mirroring the State Fact schema."""
    state_id:  str
    parent_id: Optional[str]
    action:    str
    robot_x:   int
    robot_y:   int
    inventory: List[Dict]
    needs:     Dict[str, List[Dict]]
    g_cost:    int
    h_cost:    float
    f_cost:    float

    def __repr__(self) -> str:
        inv_total     = sum(b["quantity"] for b in self.inventory)
        needs_summary = {
            pid: sum(b["quantity"] for b in blist)
            for pid, blist in self.needs.items()
        }
        return (
            f"StateNode(id={self.state_id}, parent={self.parent_id}, "
            f"action={self.action!r}, pos=({self.robot_x},{self.robot_y}), "
            f"inv_total={inv_total}, remaining={needs_summary}, "
            f"f={self.f_cost:.1f})"
        )


# ---------------------------------------------------------------------------
# Global search-tree registry
# ---------------------------------------------------------------------------
STATE_REGISTRY: Dict[str, StateNode] = {}

_COUNTER = [0]


def next_state_id() -> str:
    sid = f"S{_COUNTER[0]}"
    _COUNTER[0] += 1
    return sid


def register_state(node: StateNode) -> None:
    STATE_REGISTRY[node.state_id] = node


def get_solution_path(goal_state_id: str) -> List[StateNode]:
    """Walk parent pointers from goal back to root; return root-to-goal order.

    Implemented without explicit while-loop using a generator + list trick:
    we accumulate nodes by following .parent_id chain via a recursive helper
    turned into an iterator.
    """
    def _ancestors(sid):
        node = STATE_REGISTRY.get(sid)
        return (
            [*_ancestors(node.parent_id), node]
            if node is not None
            else []
        )

    return _ancestors(goal_state_id)


# ---------------------------------------------------------------------------
# Inventory / needs cloning helpers
# ---------------------------------------------------------------------------

def clone_inventory(inventory) -> List[Dict]:
    """Deep-copy an inventory, unwrapping Experta's frozendict wrappers."""
    return [
        {"flower": b["flower"], "color": b["color"], "quantity": b["quantity"]}
        for b in inventory
    ]


def clone_needs(needs) -> Dict[str, List[Dict]]:
    """Deep-copy a needs dict, unwrapping Experta's frozendict wrappers."""
    return {
        pid: [
            {"flower": b["flower"], "color": b["color"], "quantity": b["quantity"]}
            for b in blist
        ]
        for pid, blist in needs.items()
    }
