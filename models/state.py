"""
models/state.py
---------------
Provides:
  • StateNode – a plain Python dataclass that mirrors the State Fact but
    lives *outside* Experta's working memory.  It is used by the search
    tree printer and path reconstructor.
  • STATE_REGISTRY – a global dict  {state_id -> StateNode}  that every
    rule file can import and write to when it creates a new state.

Keeping the registry here (rather than inside the engine) means any
module can read the search tree without circular imports.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional


# ---------------------------------------------------------------------------
# StateNode dataclass
# ---------------------------------------------------------------------------
@dataclass
class StateNode:
    """One node in the search tree (mirroring the State Fact schema).

    Stored in STATE_REGISTRY so the printer and path reconstructor can
    access all generated states without querying the Experta engine.
    """
    state_id:  str
    parent_id: Optional[str]
    action:    str
    robot_x:   int
    robot_y:   int
    inventory: List[Dict]
    needs:     Dict[str, List[Dict]]   # {pavilion_id: [{flower,color,qty}]}
    g_cost:    int
    h_cost:    float
    f_cost:    float

    def __repr__(self) -> str:
        inv_summary = sum(b["quantity"] for b in self.inventory)
        needs_summary = {
            pid: sum(b["quantity"] for b in blist)
            for pid, blist in self.needs.items()
        }
        return (
            f"StateNode(id={self.state_id}, parent={self.parent_id}, "
            f"action={self.action!r}, pos=({self.robot_x},{self.robot_y}), "
            f"inv_total={inv_summary}, remaining={needs_summary}, "
            f"f={self.f_cost:.1f})"
        )


# ---------------------------------------------------------------------------
# Global search-tree registry
# ---------------------------------------------------------------------------
# All rule files import this dict and call register_state() to record nodes.
STATE_REGISTRY: Dict[str, StateNode] = {}

# Counter used to generate unique state ids
_COUNTER = [0]


def next_state_id() -> str:
    """Return the next unique state id string, e.g. 'S0', 'S1', …"""
    sid = f"S{_COUNTER[0]}"
    _COUNTER[0] += 1
    return sid


def register_state(node: StateNode) -> None:
    """Add a StateNode to the global registry."""
    STATE_REGISTRY[node.state_id] = node


def get_solution_path(goal_state_id: str) -> List[StateNode]:
    """Walk parent pointers from goal back to root and return the path
    in root-to-goal order.
    """
    path = []
    sid = goal_state_id
    while sid is not None:
        node = STATE_REGISTRY.get(sid)
        if node is None:
            break
        path.append(node)
        sid = node.parent_id
    path.reverse()
    return path


def clone_inventory(inventory) -> List[Dict]:
    """Return a plain-Python deep copy of an inventory, regardless of whether
    the source is a list, frozenlist, or contains frozendict entries.
    Experta stores list/dict fields as frozenlist/frozendict internally.
    """
    return [
        {"flower": b["flower"], "color": b["color"], "quantity": b["quantity"]}
        for b in inventory
    ]


def clone_needs(needs) -> Dict[str, List[Dict]]:
    """Return a plain-Python deep copy of a needs dict."""
    return {
        pid: [
            {"flower": b["flower"], "color": b["color"], "quantity": b["quantity"]}
            for b in blist
        ]
        for pid, blist in needs.items()
    }
