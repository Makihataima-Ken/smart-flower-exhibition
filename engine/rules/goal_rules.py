"""
engine/rules/goal_rules.py
--------------------------
Experta rules that detect when the goal state has been reached and
assert a Goal fact to halt the search.

Salience 1000 — fires first, before any generation rule.
"""
import collections.abc
import collections
collections.Mapping = collections.abc.Mapping

from experta import Rule, AS, NOT

from models.facts import State, Goal
from utils.helpers import is_goal
from utils.printer import print_solution, print_search_tree, print_grid


def make_goal_mixin(grid_info: dict, warehouse_info: dict, pavilion_list: list):
    """Return an Experta mixin class with the goal detection rule."""

    class GoalRules:

        @Rule(
            AS.node << State(active=True),
            NOT(Goal()),
            salience=200,
        )
        def detect_goal(self, node):
            is_goal(node["inventory"], node["needs"]) and self._declare_goal(node)

        def _declare_goal(self, node):
            sid = node["state_id"]
            print(f"\n{'='*60}\n  GOAL REACHED at {sid}  (g={node['g_cost']})\n{'='*60}")
            # Record goal id on the engine instance so callers can access it
            setattr(self, "_goal_state_id", sid)
            self.declare(Goal(state_id=sid))
            print_grid(
                rows=grid_info["rows"], cols=grid_info["cols"],
                robot_x=node["robot_x"], robot_y=node["robot_y"],
                warehouse_x=warehouse_info["x"], warehouse_y=warehouse_info["y"],
                pavilions=pavilion_list,
            )
            print_solution(sid)
            # print_search_tree()
            self.retract(node)

    return GoalRules
