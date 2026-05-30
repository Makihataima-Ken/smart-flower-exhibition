"""
engine/rules_goal.py
--------------------
Experta rules that detect when the goal state has been reached and
assert a Goal fact to halt the search.

GOAL CONDITION
==============
A state is a goal when:
  1. ALL pavilion needs are fully satisfied (every quantity = 0).
  2. The robot's inventory is empty (no flowers left on board).

WHY SALIENCE = 200?
===================
Goal detection must fire before expansion rules so that as soon as
a goal state is activated, we stop and record the solution without
generating unnecessary children.

SIDE EFFECTS
============
When goal is detected:
  • A Goal fact is asserted - this blocks all other rules via NOT(Goal()).
  • The solution path is printed immediately.
  • The search tree is printed.
"""
import collections.abc
import collections
collections.Mapping = collections.abc.Mapping

from experta import Rule, AS, NOT

from models.facts import State, Goal
from utils.helpers import is_goal
from utils.printer import print_solution, print_search_tree, print_grid


def make_goal_mixin(grid_info: dict, warehouse_info: dict, pavilion_list: list):
    """Return an Experta mixin class with the goal detection rule.

    grid_info:      {"rows": int, "cols": int}
    warehouse_info: {"x": int, "y": int}
    pavilion_list:  [{"pavilion_id", "x", "y", "needs"}]
    """

    class GoalRules:

        @Rule(
            AS.state << State(active=True),
            NOT(Goal()),
            salience=200,   # fires first – before any generation rule
        )
        def detect_goal(self, state):
            """Check whether the active state satisfies the goal condition."""
            if not is_goal(state["inventory"], state["needs"]):
                return   # not yet a goal – let other rules fire

            # ----------------------------------------------------------------
            # Goal reached!
            # ----------------------------------------------------------------
            sid = state["state_id"]
            print(f"\n{'='*60}")
            print(f"  GOAL REACHED at state {sid}  (g_cost = {state['g_cost']})")
            print(f"{'='*60}")

            # Assert Goal fact → blocks all other rules via NOT(Goal())
            self.declare(Goal(state_id=sid))

            # Print final grid layout
            print("\n  Final grid layout:")
            print_grid(
                rows         = grid_info["rows"],
                cols         = grid_info["cols"],
                robot_x      = state["robot_x"],
                robot_y      = state["robot_y"],
                warehouse_x  = warehouse_info["x"],
                warehouse_y  = warehouse_info["y"],
                pavilions    = pavilion_list,
            )

            # Print solution path and full search tree
            print_solution(sid)
            print_search_tree()

            # Deactivate the goal state (no further expansion needed)
            self.modify(state, active=False)

    return GoalRules
