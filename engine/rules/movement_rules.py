"""
engine/rules_movement.py
------------------------
Experta rule for expanding a State by moving the robot in all four
cardinal directions: up, down, left, right.

KEY DESIGN DECISION: ONE RULE, ALL DIRECTIONS
=============================================
Experta fires a rule once per matching activation.  If we wrote four
separate rules (one per direction) they would compete for the same
active State fact: whichever fires first would call self.modify(state,
active=False), deactivating the state before the other three can fire.

Solution: a SINGLE rule that iterates over all four directions inside
its body, generating up to four child states per call.  This guarantees
complete expansion of every state.

SALIENCE = 10  (lowest – movement is the fallback action)
"""
import collections.abc
import collections
collections.Mapping = collections.abc.Mapping

from experta import Rule, MATCH, NOT, AS

from models.facts import State, Grid, Goal
from models.state import (
    StateNode, next_state_id, register_state,
    clone_inventory, clone_needs,
)
from engine.heuristic import compute_heuristic
from utils.helpers import is_valid_position, state_hash, DIRECTIONS
from utils.search_tree import is_closed, push_open


def _try_move(engine, current, action, grid_cols, grid_rows, pavilion_positions):
    """Attempt one movement direction and assert a child State if valid."""
    dx, dy = DIRECTIONS[action]
    new_x = current["robot_x"] + dx
    new_y = current["robot_y"] + dy

    if not is_valid_position(new_x, new_y, grid_cols, grid_rows):
        return  # out of bounds

    new_inv   = clone_inventory(current["inventory"])
    new_needs = clone_needs(current["needs"])

    sh = state_hash(new_x, new_y, new_inv, new_needs)
    if is_closed(sh):
        return  # already expanded

    new_g = current["g_cost"] + 1
    new_h = compute_heuristic(new_x, new_y, new_needs, pavilion_positions)
    new_f = new_g + new_h
    sid   = next_state_id()
    cap   = current.get("capacity", 999)

    node = StateNode(
        state_id  = sid,
        parent_id = current["state_id"],
        action    = action,
        robot_x   = new_x,
        robot_y   = new_y,
        inventory = new_inv,
        needs     = new_needs,
        g_cost    = new_g,
        h_cost    = new_h,
        f_cost    = new_f,
    )
    register_state(node)
    push_open(new_f, sid)

    engine.declare(State(
        state_id  = sid,
        parent_id = current["state_id"],
        action    = action,
        robot_x   = new_x,
        robot_y   = new_y,
        inventory = new_inv,
        needs     = new_needs,
        g_cost    = new_g,
        h_cost    = new_h,
        f_cost    = new_f,
        active    = False,
        capacity  = cap,
    ))
    print(f"    → generated child {sid} via {action!r} pos=({new_x},{new_y}) f={new_f:.1f}")


def make_movement_mixin(pavilion_positions: dict):
    """Return a mixin with a single movement rule that tries all 4 directions."""

    class MovementRules:

        @Rule(
            AS.state << State(active=True),
            Grid(cols=MATCH.cols, rows=MATCH.rows),
            NOT(Goal()),
            salience=10,
        )
        def expand_movements(self, state, cols, rows):
            """Generate child states for all valid movement directions."""
            for action in ("move_up", "move_down", "move_left", "move_right"):
                _try_move(self, state, action, cols, rows, pavilion_positions)
            # Deactivate AFTER all directions are tried
            self.modify(state, active=False)

    return MovementRules
