"""
engine/rules_loading.py
-----------------------
Single Experta rule that expands all valid loading actions from the
warehouse in one rule firing.

LOADING CONSTRAINTS (see assignment spec)
=========================================
MODE A: different flower types, same color
MODE B: same flower type, different colors
Mixing is forbidden.  can_load() in helpers.py enforces this.

SALIENCE = 20  (above movement=10, below unloading=30)
"""
import collections.abc
import collections
collections.Mapping = collections.abc.Mapping

from experta import Rule, AS, MATCH, NOT

from models.facts import State, Warehouse, Goal
from models.state import (
    StateNode, next_state_id, register_state,
    clone_inventory, clone_needs,
)
from engine.heuristic import compute_heuristic
from utils.helpers import can_load, add_to_inventory, state_hash
from utils.search_tree import is_closed, push_open


def _try_load(engine, current, flower, color, qty, cap, pavilion_positions, warehouse_pos):
    """Try loading qty units of (flower,color) and assert a child if valid."""
    new_inv   = clone_inventory(current["inventory"])
    new_needs = clone_needs(current["needs"])

    ok, reason = can_load(new_inv, flower, color, qty, cap)
    if not ok:
        return

    add_to_inventory(new_inv, flower, color, qty)

    sh = state_hash(current["robot_x"], current["robot_y"], new_inv, new_needs)
    if is_closed(sh):
        return

    new_g  = current["g_cost"] + 1
    new_h  = compute_heuristic(
        current["robot_x"], current["robot_y"], new_inv, new_needs, pavilion_positions, warehouse_pos, cap
    )
    new_f  = new_g + new_h
    action = f"load {flower} {color} {qty}"
    sid    = next_state_id()

    register_state(StateNode(
        state_id  = sid,
        parent_id = current["state_id"],
        action    = action,
        robot_x   = current["robot_x"],
        robot_y   = current["robot_y"],
        inventory = new_inv,
        needs     = new_needs,
        g_cost    = new_g,
        h_cost    = new_h,
        f_cost    = new_f,
    ))
    push_open(new_f, sid)

    engine.declare(State(
        state_id  = sid,
        parent_id = current["state_id"],
        action    = action,
        robot_x   = current["robot_x"],
        robot_y   = current["robot_y"],
        inventory = new_inv,
        needs     = new_needs,
        g_cost    = new_g,
        h_cost    = new_h,
        f_cost    = new_f,
        active    = False,
        capacity  = cap,
    ))
    print(f"    → generated child {sid} via {action!r} f={new_f:.1f}")


def make_loading_mixin(pavilion_positions: dict, warehouse_pos: dict):
    """Return loading mixin closed over warehouse stock and pavilion positions."""

    class LoadingRules:

        @Rule(
            AS.state << State(
                active=True,
                robot_x=MATCH.rx,
                robot_y=MATCH.ry,
                capacity=MATCH.cap,
            ),
            Warehouse(x=MATCH.rx, y=MATCH.ry),
            NOT(Goal()),
            salience=20,
        )
        def expand_loads(self, state, rx, ry, cap):
            """Generate one child per feasible (flower, color, qty) load action.

            NOTE: We do NOT deactivate the state here.  The movement rule
            (salience=10) runs after this and deactivates the state once all
            generation rules have fired.  This ensures movement children are
            also generated for warehouse cells.
            """
            for pavillion_needs in state["needs"].values():
                for item in pavillion_needs:
                    _try_load(self, state, item["flower"], item["color"], item["quantity"], cap, pavilion_positions, warehouse_pos)

    return LoadingRules
