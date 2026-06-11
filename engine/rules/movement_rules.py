"""
engine/rules/movement_rules.py
------------------------------
Experta rule for expanding movement in all four cardinal directions.

Salience 10 (lowest – movement is the fallback action).
"""
import collections.abc
import collections
collections.Mapping = collections.abc.Mapping

from experta import Rule, NOT, AS

from models.facts import State, Goal, ExpandDone
from utils.helpers import is_valid_position, DIRECTIONS


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
    # print(f"    → child {sid} via {action!r} pos=({new_x},{new_y}) f={new_f:.1f}")
    return sid


def _try_move(engine, node, action, grid_cols, grid_rows, pavilion_positions, warehouse_pos, cap):
    dx, dy = DIRECTIONS[action]
    new_x = node["robot_x"] + dx
    new_y = node["robot_y"] + dy
    if not is_valid_position(new_x, new_y, grid_cols, grid_rows):
        return
    new_inv   = [{"flower": b["flower"], "color": b["color"], "quantity": b["quantity"]} for b in node["inventory"]]
    new_needs = {p: [{"flower": b["flower"], "color": b["color"], "quantity": b["quantity"]} for b in blist] for p, blist in node["needs"].items()}
    _make_child(
        engine, node, action, new_x, new_y,
        new_inv, new_needs, pavilion_positions, cap, warehouse_pos,
    )


def make_movement_mixin(pavilion_positions: dict, grid_info: dict, warehouse_pos: dict):
    """Return a mixin with a single movement rule that tries all 4 directions."""

    class MovementRules:

        @Rule(
            AS.node << State(active=True),
            NOT(Goal()),
            salience=10,
        )
        def expand_movements(self, node):
            for action in DIRECTIONS:
                _try_move(self, node, action, grid_info["cols"], grid_info["rows"],
                          pavilion_positions, warehouse_pos, node["capacity"])
            self.retract(node)
            self.declare(ExpandDone())

    return MovementRules
