"""
engine/knowledge_engine_pure.py
--------------------------------
Pure-Experta A* search

ARCHITECTURE (clean, active-state selection):

  Selected search nodes are activated via State(active=True).  Generation
  rules fire on the active state.  The movement rule (last, salience 10)
  deactivates the state and asserts ExpandDone.  do_select fires on
  ExpandDone (or at the very start on ReadyToSelect).

  This keeps one focused active node while preserving State facts for
  path reconstruction.
"""

import copy

try:
    import collections.abc, collections
    collections.Mapping = collections.abc.Mapping
except (ImportError, AttributeError):
    pass

from experta import KnowledgeEngine

from models.facts import (
    Grid, Warehouse, State, ReadyToSelect
)
from models.state import (
    StateNode, next_state_id, register_state, STATE_REGISTRY
)
from engine.heuristic import compute_heuristic
from utils.helpers import (
    state_hash,
)
from utils.search_tree import (
    reset_search_structures, push_open_with_g, should_expand
)
from utils.printer import print_grid
from engine.rules.constraints_rules import make_constraints_mixin
from engine.rules.goal_rules import make_goal_mixin
from engine.rules.loading_rules import make_loading_mixin
from engine.rules.unloading_rules import make_unloading_mixin
from engine.rules.movement_rules import make_movement_mixin
from engine.rules.search_control import make_search_control_mixin

def build_engine(scenario: dict) -> "FlowerDeliveryEngine":
    grid      = scenario["grid"]
    warehouse = scenario["warehouse"]
    pavilions = scenario["pavilions"]
    capacity  = scenario["robot_capacity"]

    pavilion_positions = {
        p["pavilion_id"]: {"x": p["x"], "y": p["y"]}
        for p in pavilions
    }
    pos_to_pid = {(p["x"], p["y"]): p["pavilion_id"] for p in pavilions}

    grid_info  = {"rows": grid["rows"], "cols": grid["cols"]}
    wh_info    = {"x": warehouse["x"], "y": warehouse["y"]}

    ConstraintRulesMixin = make_constraints_mixin()
    GoalRulesMixin = make_goal_mixin(grid_info, wh_info, pavilions)
    LoadingRulesMixin = make_loading_mixin(pavilion_positions, wh_info)
    UnloadingRulesMixin = make_unloading_mixin(pavilion_positions, wh_info, pos_to_pid)
    MovementRulesMixin = make_movement_mixin(pavilion_positions, grid_info, wh_info)
    SearchControlRulesMixin = make_search_control_mixin(capacity)

    class FlowerDeliveryEngine(KnowledgeEngine, ConstraintRulesMixin, GoalRulesMixin, UnloadingRulesMixin, LoadingRulesMixin, MovementRulesMixin, SearchControlRulesMixin):

        # ================================================================
        # GOAL DETECTION  (salience 200)  —  imported from
        # engine/rules/goal_rules.py via GoalRulesMixin.
        # ================================================================

        # ================================================================
        # CONSTRAINT CHECKS  (salience 150)  —  now imported from
        # engine/rules/constraints_rules.py via ConstraintRulesMixin.
        # They are mixed in at class creation, so they fire automatically.
        # ================================================================

        # ================================================================
        # UNLOAD GENERATION  (salience 30)  —  imported from
        # engine/rules/unloading_rules.py via UnloadingRulesMixin.
        # ================================================================

        # ================================================================
        # LOAD GENERATION  (salience 20)  —  imported from
        # engine/rules/loading_rules.py via LoadingRulesMixin.
        # ================================================================

        # ================================================================
        # MOVEMENT GENERATION + EXPAND DONE  (salience 10)  —  imported from
        # engine/rules/movement_rules.py via MovementRulesMixin.
        # ================================================================

        # ================================================================
        # SELECT + ACTIVATE  (salience 1000)  —  imported from
        # engine/rules/search_control.py via SearchControlRulesMixin.
        # ================================================================
        pass

    engine = FlowerDeliveryEngine()
    # initialize holder for found goal id (None when no goal found)
    setattr(engine, "_goal_state_id", None)
    return engine


def run_search(scenario: dict) -> None:
    reset_search_structures()
    STATE_REGISTRY.clear()
    from models import state as _s
    _s._COUNTER[0] = 0

    grid        = scenario["grid"]
    warehouse   = scenario["warehouse"]
    pavilions   = scenario["pavilions"]
    robot_start = scenario["robot_start"]
    capacity    = scenario["robot_capacity"]
    
    wh_info    = {"x": warehouse["x"], "y": warehouse["y"]}

    pavilion_positions = {
        p["pavilion_id"]: {"x": p["x"], "y": p["y"]}
        for p in pavilions
    }
    initial_needs = {
        p["pavilion_id"]: copy.deepcopy(p["needs"])
        for p in pavilions
    }

    engine = build_engine(scenario)
    engine.reset()

    engine.declare(Grid(rows=grid["rows"], cols=grid["cols"]))
    engine.declare(Warehouse(
        x=warehouse["x"], y=warehouse["y"]
    ))

    rx0, ry0 = robot_start["x"], robot_start["y"]
    inv0     = []
    h0       = compute_heuristic(rx0, ry0, inv0, initial_needs, pavilion_positions, wh_info, capacity)
    root_id  = next_state_id()

    register_state(StateNode(
        state_id=root_id, parent_id=None, action="start",
        robot_x=rx0, robot_y=ry0,
        inventory=inv0, needs=initial_needs,
        g_cost=0, h_cost=h0, f_cost=h0,
    ))
    
    root_hash = state_hash( rx0, ry0, inv0, initial_needs)
    should_expand(root_hash, 0)
    
    engine.declare(State(
        state_id=root_id, parent_id=None, action="start",
        robot_x=rx0, robot_y=ry0,
        inventory=inv0, needs=initial_needs,
        g_cost=0, h_cost=h0, f_cost=h0,
        active=False, capacity=capacity,
    ))

    push_open_with_g(h0, root_id, 0)
    engine.declare(ReadyToSelect())

    print("\nInitial grid layout:")
    print_grid(
        rows=grid["rows"], cols=grid["cols"],
        robot_x=rx0, robot_y=ry0,
        warehouse_x=warehouse["x"], warehouse_y=warehouse["y"],
        pavilions=pavilions,
    )
    print(f"\nRobot capacity: {capacity}")
    print(f"Root: {root_id}  h={h0:.1f}\n")

    engine.run()
    # After execution, engine._goal_state_id holds the found goal id or None
    return getattr(engine, "_goal_state_id", None)
