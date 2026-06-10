"""
engine/rules/constraints_rules.py
---------------------------------
Experta rules that detect and retract illegal or useless states.

Salience 150 (fires before any generation rule).
If a state is retracted here it will never be expanded.
"""
import collections.abc
import collections
collections.Mapping = collections.abc.Mapping

from experta import Rule, AS, MATCH, NOT

from models.facts import State, Goal, Grid
from utils.helpers import inventory_total

def make_constraints_mixin():
    """Return an Experta mixin class with all constraint rules."""

    class ConstraintRules:

        # -------------------------------------------------------------------
        # 1. Out-of-bounds guard  (safety net – movement rules should prevent
        #    this, but we add the check here defensively)
        # -------------------------------------------------------------------
        
        @Rule(
            AS.node << State(active=True),
            Grid(cols=MATCH.cols, rows=MATCH.rows),
            NOT(Goal()),
            salience=150,
        )
        def check_out_of_bounds(self, node, cols, rows):
            rx, ry = node["robot_x"], node["robot_y"]
            out = rx < 0 or rx >= cols or ry < 0 or ry >= rows
            out and (
                print(f"  [OOB] retract {node['state_id']}"),
                self.retract(node),
            )

        # -------------------------------------------------------------------
        # 2. Over-capacity guard
        # -------------------------------------------------------------------
        
        @Rule(
            AS.node << State(active=True),
            NOT(Goal()),
            salience=150,
        )
        def check_capacity(self, node):
            over = inventory_total(node["inventory"]) > node["capacity"]
            over and (
                print(f"  [CAP] retract {node['state_id']}"),
                self.retract(node),
            )

        # -------------------------------------------------------------------
        # 3. Invalid loading mix safety guard
        #    Catches inventory with multiple flower types AND multiple colors. 
        #    in case can_load fails to catch 
        # -------------------------------------------------------------------
        
        @Rule(
            AS.node << State(active=True),
            NOT(Goal()),
            salience=150,
        )
        def check_load_mix(self, node):
            inv = node["inventory"]
            flowers = {b["flower"] for b in inv}
            colors  = {b["color"]  for b in inv}
            mixed = len(inv) >= 2 and len(flowers) > 1 and len(colors) > 1
            mixed and (
                print(f"  [MIX] retract {node['state_id']}"),
                self.retract(node),
            )

    return ConstraintRules
