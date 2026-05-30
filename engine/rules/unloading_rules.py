"""
engine/rules_unloading.py
-------------------------
Single Experta rule that expands all valid unloading actions at a
pavilion in one rule firing.

UNLOADING RULES
===============
• Robot must be at the pavilion's cell.
• Flower type AND color must match the pavilion's need exactly.
• Partial delivery allowed (qty <= remaining need).

SALIENCE = 30  (highest generation priority - deliver first)
"""
import collections.abc
import collections
collections.Mapping = collections.abc.Mapping

from experta import Rule, AS, MATCH, NOT

from models.facts import State, Goal
from models.state import (
    StateNode, next_state_id, register_state,
    clone_inventory, clone_needs,
)
from engine.heuristic import compute_heuristic
from utils.helpers import (
    can_unload, remove_from_inventory, find_bouquet, state_hash,
)
from utils.search_tree import is_closed, push_open


def _try_unload(engine, current, pavilion_id, flower, color, qty, pavilion_positions):
    """Try unloading qty units at the given pavilion and assert a child if valid."""
    new_inv   = clone_inventory(current["inventory"])
    new_needs = clone_needs(current["needs"])

    ok, _ = can_unload(new_inv, new_needs[pavilion_id], flower, color, qty)
    if not ok:
        return

    remove_from_inventory(new_inv, flower, color, qty)
    need_entry = find_bouquet(new_needs[pavilion_id], flower, color)
    need_entry["quantity"] -= qty

    sh = state_hash(current["robot_x"], current["robot_y"], new_inv, new_needs)
    if is_closed(sh):
        return

    new_g  = current["g_cost"] + 1
    new_h  = compute_heuristic(
        current["robot_x"], current["robot_y"], new_needs, pavilion_positions
    )
    new_f  = new_g + new_h
    action = f"unload {pavilion_id} {flower} {color} {qty}"
    sid    = next_state_id()
    cap    = current.get("capacity", 999)

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


def make_unloading_mixin(pavilion_list: list, pavilion_positions: dict):
    """Return unloading mixin closed over pavilion data."""

    # Map (x, y) → pavilion_id for fast lookup inside the rule
    pos_to_pid = {(p["x"], p["y"]): p["pavilion_id"] for p in pavilion_list}

    class UnloadingRules:

        @Rule(
            AS.state << State(
                active=True,
                robot_x=MATCH.rx,
                robot_y=MATCH.ry,
                needs=MATCH.needs,
            ),
            NOT(Goal()),
            salience=30,
        )
        def expand_unloads(self, state, rx, ry, needs):
            """Generate one child per feasible (flower, color, qty) unload action."""
            pid = pos_to_pid.get((rx, ry))
            if pid is None:
                return   # not a pavilion cell

            pav_needs = needs.get(pid)
            if not pav_needs:
                return   # pavilion not in needs dict

            for inv_item in state["inventory"]:
                flower = inv_item["flower"]
                color  = inv_item["color"]
                need_item = find_bouquet(list(pav_needs), flower, color)
                if need_item is None or need_item["quantity"] <= 0:
                    continue
                max_deliver = min(inv_item["quantity"], need_item["quantity"])
                for qty in range(1, max_deliver + 1):
                    _try_unload(
                        self, state, pid, flower, color, qty, pavilion_positions
                    )
            # NOTE: do NOT deactivate here – movement rule (salience=10) fires
            # last and deactivates the state after all generation rules finish.

    return UnloadingRules
