"""
engine/rules/unloading_rules.py
-------------------------------
Experta rule that expands all valid unloading actions at a pavilion.

Salience 30 (highest generation priority - deliver first).
"""
import collections.abc
import collections
collections.Mapping = collections.abc.Mapping

from experta import Rule, AS, MATCH, NOT

from models.facts import State, Goal
from utils.helpers import (
    can_unload, remove_from_inventory, find_bouquet,
)


def _try_unload(engine, node, pid, inv_item, need_item, qty, pavilion_positions, warehouse_pos):
    new_inv   = [{"flower": b["flower"], "color": b["color"], "quantity": b["quantity"]} for b in node["inventory"]]
    new_needs = {p: [{"flower": b["flower"], "color": b["color"], "quantity": b["quantity"]} for b in blist] for p, blist in node["needs"].items()}
    ok, _ = can_unload(new_inv, new_needs[pid], inv_item["flower"], inv_item["color"], qty)
    ok and remove_from_inventory(new_inv, inv_item["flower"], inv_item["color"], qty)
    ne = ok and find_bouquet(new_needs[pid], inv_item["flower"], inv_item["color"])
    ne and ne.__setitem__("quantity", ne["quantity"] - qty)
    ok and _make_child(
        engine, node,
        f"unload {pid} {inv_item['flower']} {inv_item['color']} {qty}",
        node["robot_x"], node["robot_y"],
        new_inv, new_needs, pavilion_positions, node["capacity"], warehouse_pos,
    )
    return ok


def _make_child(engine, current, action, new_x, new_y, new_inv, new_needs,
                pavilion_positions, cap, warehouse_pos):
    from engine.heuristic import compute_heuristic
    from models.state import StateNode, next_state_id, register_state
    from utils.helpers import state_hash
    from utils.search_tree import should_expand, push_open

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
    print(f"    → child {sid} via {action!r} pos=({new_x},{new_y}) f={new_f:.1f}")
    return sid


def make_unloading_mixin(pavilion_positions: dict, warehouse_pos: dict, pos_to_pid:dict):
    """Return unloading mixin closed over pavilion data."""

    class UnloadingRules:

        @Rule(
            AS.node << State(active=True),
            NOT(Goal()),
            salience=30,
        )
        def expand_unloads(self, node):
            rx, ry  = node["robot_x"], node["robot_y"]
            pid = pos_to_pid.get((rx, ry))
            pav_needs = pid and node["needs"].get(pid)
            if not pav_needs:
                return
            for inv_item in node["inventory"]:
                if inv_item["quantity"] <= 0:
                    continue
                need_item = find_bouquet(list(pav_needs), inv_item["flower"], inv_item["color"])
                if need_item is None or need_item["quantity"] <= 0:
                    continue
                max_qty = min(inv_item["quantity"], need_item["quantity"])
                _try_unload(self, node, pid, inv_item, need_item, max_qty, pavilion_positions, warehouse_pos)

    return UnloadingRules
