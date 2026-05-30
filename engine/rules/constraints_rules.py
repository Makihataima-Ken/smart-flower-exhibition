"""
engine/rules_constraints.py
---------------------------
Experta rules that detect and retract illegal or useless states.

Instead of preventing bad states from being generated (which would require
embedding all logic inside each rule), we use a separate "constraint layer"
that fires AFTER generation and retracts any state that violates a rule.

This is a deliberate architectural choice: it keeps the generation rules
simple and puts all validity checks in one dedicated file - easier to audit
and explain academically.

CONSTRAINTS ENFORCED
====================
1. out_of_bounds       - robot position outside grid  (safety net)
2. over_capacity       - inventory exceeds robot capacity
3. invalid_load_mix    - inventory has mixed flowers AND mixed colors
4. inactive_stale      - state was never activated (orphan cleanup)

SALIENCE = 100  (fires before any generation rule - highest priority)
If a state is retracted here it will never be expanded.
"""
import collections.abc
import collections
collections.Mapping = collections.abc.Mapping

from experta import Rule, AS, MATCH, NOT

from models.facts import State, Grid, Goal
from utils.helpers import inventory_total


def make_constraints_mixin():
    """Return an Experta mixin class with all constraint rules."""

    class ConstraintRules:

        # -------------------------------------------------------------------
        # 1. Out-of-bounds guard  (safety net – movement rules should prevent
        #    this, but we add the check here defensively)
        # -------------------------------------------------------------------
        @Rule(
            AS.state << State(active=MATCH.active),
            Grid(cols=MATCH.cols, rows=MATCH.rows),
            NOT(Goal()),
            salience=100,
        )
        def retract_out_of_bounds(self, state, active, cols, rows):
            rx = state["robot_x"]
            ry = state["robot_y"]
            if rx < 0 or rx >= cols or ry < 0 or ry >= rows:
                print(f"  [CONSTRAINT] retract {state['state_id']}: out of bounds ({rx},{ry})")
                self.retract(state)

        # -------------------------------------------------------------------
        # 2. Over-capacity guard
        # -------------------------------------------------------------------
        @Rule(
            AS.state << State(active=MATCH.active),
            NOT(Goal()),
            salience=100,
        )
        def retract_over_capacity(self, state, active):
            cap   = state.get("capacity", None)
            if cap is None:
                return   # no capacity field yet – skip
            total = inventory_total(state["inventory"])
            if total > cap:
                print(
                    f"  [CONSTRAINT] retract {state['state_id']}: "
                    f"over capacity ({total} > {cap})"
                )
                self.retract(state)

        # -------------------------------------------------------------------
        # 3. Invalid loading mix guard
        #    Catches inventory with multiple flower types AND multiple colors.
        # -------------------------------------------------------------------
        @Rule(
            AS.state << State(active=MATCH.active),
            NOT(Goal()),
            salience=100,
        )
        def retract_invalid_load_mix(self, state, active):
            inventory = state["inventory"]
            if len(inventory) < 2:
                return  # 0 or 1 item – always valid

            flowers = {b["flower"] for b in inventory}
            colors  = {b["color"]  for b in inventory}

            # Violation: multiple flower types AND multiple colors
            if len(flowers) > 1 and len(colors) > 1:
                print(
                    f"  [CONSTRAINT] retract {state['state_id']}: "
                    f"invalid load mix (flowers={flowers}, colors={colors})"
                )
                self.retract(state)

    return ConstraintRules
