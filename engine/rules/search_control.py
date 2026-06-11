"""
engine/rules/search_control.py
----------------------------
Experta rules for selecting the next state from the open list and
activating it.  Also handles the NoSolution terminal fact.

Salience 1000 (fires before any generation rule).
"""
import collections.abc
import collections
collections.Mapping = collections.abc.Mapping

from experta import Rule, AS, NOT

from models.facts import State, Goal, NoSolution, ReadyToSelect, ExpandDone
from utils.search_tree import pop_open, BEST_G
from utils.helpers import state_hash
from models.state import STATE_REGISTRY

def make_search_control_mixin(scenario_capacity: int):
    """Return a mixin with the select-and-activate control rules."""

    class SearchControlRules:

        @Rule(AS.trigger << ReadyToSelect(), NOT(Goal()), NOT(NoSolution()), salience=1000)
        def do_select_initial(self, trigger):
            self.retract(trigger)
            self._select_and_activate()

        @Rule(AS.trigger << ExpandDone(), NOT(Goal()), NOT(NoSolution()), salience=1000)
        def do_select(self, trigger):
            self.retract(trigger)
            self._select_and_activate()

        def _select_and_activate(self):
            best_id = pop_open()
            (not best_id) and self.declare(NoSolution())
            best_id and self._try_activate(best_id)

        def _try_activate(self, best_id):
            st = STATE_REGISTRY.get(best_id)
            if st is None:
                self._select_and_activate()
                return
            sh = state_hash(st.robot_x, st.robot_y, st.inventory, st.needs)

            best_g = BEST_G.get(sh)

            if best_g is not None and st.g_cost > best_g:
                self._select_and_activate()
                return
            self._activate_node(best_id, st)

        def _activate_node(self, best_id, st):
            print(f"\n[SELECT] {best_id}  g={st.g_cost} h={st.h_cost:.1f} f={st.f_cost:.1f}"
                  f"  pos=({st.robot_x},{st.robot_y})")
            self.declare(State(
                state_id=best_id,
                parent_id=st.parent_id,
                action=st.action,
                robot_x=st.robot_x,
                robot_y=st.robot_y,
                inventory=st.inventory,
                needs=st.needs,
                g_cost=st.g_cost,
                h_cost=st.h_cost,
                f_cost=st.f_cost,
                active=True,
                capacity=scenario_capacity,
            ))

        @Rule(NoSolution())
        def report_no_solution(self):
            print("\nSearch exhausted – no solution found.")

    return SearchControlRules
