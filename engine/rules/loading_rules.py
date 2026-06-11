"""
engine/rules/loading_rules.py
-----------------------------
Experta rule that expands all valid loading actions from the warehouse.

Salience 20 (above movement=10, below unloading=30).
"""
import collections.abc
import collections
collections.Mapping = collections.abc.Mapping

from experta import Rule, AS, MATCH, NOT

from models.facts import State, Warehouse, Goal
from utils.helpers import can_load, add_to_inventory, inventory_total
from utils.search_tree import push_open


def _try_load(engine, node, flower, color, qty, cap, pavilion_positions, warehouse_pos):
    """Try loading qty units of (flower,color) and register a child if valid."""
    new_inv   = [{"flower": b["flower"], "color": b["color"], "quantity": b["quantity"]} for b in node["inventory"]]
    new_needs = {p: [{"flower": b["flower"], "color": b["color"], "quantity": b["quantity"]} for b in blist] for p, blist in node["needs"].items()}
    ok, _ = can_load(new_inv, flower, color, qty, cap)
    ok and add_to_inventory(new_inv, flower, color, qty)
    ok and _make_child(
        engine, node, f"load {flower} {color} {qty}",
        node["robot_x"], node["robot_y"],
        new_inv, new_needs, pavilion_positions, cap, warehouse_pos,
    )
    return ok


def _make_child(engine, current, action, new_x, new_y, new_inv, new_needs,
                pavilion_positions, cap, warehouse_pos):
    from engine.heuristic import compute_heuristic
    from models.state import StateNode, next_state_id, register_state
    from utils.helpers import state_hash
    from utils.search_tree import should_expand

    sh = state_hash(new_x, new_y, new_inv, new_needs)
    new_g = current["g_cost"] + 1
    if not should_expand(sh, new_g):
        return
    new_h = compute_heuristic(new_x, new_y, new_inv, new_needs, pavilion_positions, warehouse_pos, cap)
    new_f = new_g + new_h
    sid = next_state_id()
    register_state(StateNode(
        state_id=sid, parent_id=current["state_id"], action=action,
        robot_x=new_x, robot_y=new_y,
        inventory=new_inv, needs=new_needs,
        g_cost=new_g, h_cost=new_h, f_cost=new_f,
    ))
    push_open(new_f, sid)
    # print(f"    → child {sid} via {action!r} pos=({new_x},{new_y}) f={new_f:.1f}")
    return sid


def make_loading_mixin(pavilion_positions: dict, warehouse_pos: dict):
    """Return loading mixin closed over pavilion positions and warehouse position."""

    class LoadingRules:

        @Rule(
            AS.node << State(active=True),
            Warehouse(x=MATCH.rx, y=MATCH.ry),
            NOT(Goal()),
            salience=20,
        )
        def expand_loads(self, node, rx, ry):
            if node["robot_x"] != rx or node["robot_y"] != ry:
                return

            current_load = inventory_total(node["inventory"])
            remaining_capacity = node["capacity"] - current_load

            if remaining_capacity <= 0:
                return

            for pavilion_needs in node["needs"].values():
                for item in pavilion_needs:
                    needed_qty = item["quantity"]
                    if needed_qty <= 0:
                        continue
                    qty = min(needed_qty, remaining_capacity)
                    if qty > 0:
                        _try_load(self, node, item["flower"], item["color"], qty, node["capacity"], pavilion_positions, warehouse_pos)

    return LoadingRules
