"""
engine/knowledge_engine.py
--------------------------
Assembles all rule mixins into a single Experta KnowledgeEngine and
drives the A* search loop.

ARCHITECTURE
============
Experta requires all rules to live inside one KnowledgeEngine class.
Because our rules are split across multiple files (for readability), we
use Python's multiple-inheritance to *compose* the engine from mixins:

    class FlowerEngine(GoalRules, ConstraintRules, UnloadingRules,
                       LoadingRules, MovementRules, KnowledgeEngine):
        ...

Each mixin is built by a factory function (make_*_mixin) that closes
over scenario-specific data (grid size, pavilion positions, etc.) so the
rules don't need to perform expensive fact lookups at every firing.

A* SEARCH LOOP
==============
Experta's forward-chaining alone cannot implement A* because Experta
fires rules on ALL matching facts, not just the best-f-cost one.

We solve this with a manual outer loop:
  1. Pop the state with the lowest f_cost from the open heap (search_tree.py).
  2. Activate that one State fact (set active=True).
  3. Call engine.run() – this fires all matching rules for the active state,
     generating child states (with active=False) and asserting them.
  4. Repeat until Goal is asserted or open list is empty.

SALIENCE INSIDE ONE EXPANSION
==============================
Within a single engine.run() call the salience ordering still matters:
  200 - goal detection (fires first; halts if goal)
  100 - constraint retractions (prune illegal children immediately)
   30 - unloading (prefer delivery)
   20 - loading  (prefer loading over moving)
   10 - movement (movement as last resort)
"""

import copy
import collections.abc
import collections
collections.Mapping = collections.abc.Mapping

from experta import KnowledgeEngine

from models.facts import Grid, Warehouse, Pavilion, State, Goal
from models.state import (
    StateNode, next_state_id, register_state, STATE_REGISTRY,
)
from engine.heuristic import compute_heuristic
from engine.rules.movement_rules import make_movement_mixin
from engine.rules.loading_rules import make_loading_mixin
from engine.rules.unloading_rules import make_unloading_mixin
from engine.rules.constraints_rules  import make_constraints_mixin
from engine.rules.goal_rules import make_goal_mixin
from utils.helpers import state_hash, is_goal
from utils.search_tree import (
    push_open, pop_open, open_is_empty,
    add_closed, is_closed, reset_search_structures,
)
from utils.printer import print_grid


# ---------------------------------------------------------------------------
# Engine factory
# ---------------------------------------------------------------------------

def build_engine(scenario: dict) -> "FlowerDeliveryEngine":
    """Construct and return the composed KnowledgeEngine for a scenario.

    Args:
        scenario: dict with keys:
            grid, warehouse, pavilions, robot_start, robot_capacity
    """
    grid        = scenario["grid"]
    warehouse   = scenario["warehouse"]
    pavilions   = scenario["pavilions"]
    robot_start = scenario["robot_start"]
    capacity    = scenario["robot_capacity"]

    # Precompute pavilion position lookup used by heuristic and rules
    pavilion_positions = {
        p["pavilion_id"]: {"x": p["x"], "y": p["y"]}
        for p in pavilions
    }

    # Build mixin classes (each closes over scenario data)
    GoalRules       = make_goal_mixin(grid, warehouse, pavilions)
    ConstraintRules = make_constraints_mixin()
    UnloadingRules  = make_unloading_mixin(pavilions, pavilion_positions)
    LoadingRules    = make_loading_mixin(warehouse["stock"], pavilion_positions)
    MovementRules   = make_movement_mixin(pavilion_positions)

    # Compose engine via multiple inheritance
    # Order matters: Python MRO resolves method lookup left → right
    class FlowerDeliveryEngine(
        GoalRules,
        ConstraintRules,
        UnloadingRules,
        LoadingRules,
        MovementRules,
        KnowledgeEngine,
    ):
        """Composed knowledge engine for the smart flower exhibition."""
        pass

    engine = FlowerDeliveryEngine()

    # Store scenario data on the engine for use by the search loop
    engine._scenario         = scenario
    engine._pavilion_positions = pavilion_positions
    engine._capacity         = capacity

    return engine


# ---------------------------------------------------------------------------
# Search runner
# ---------------------------------------------------------------------------

def run_search(scenario: dict) -> None:
    """Set up and run the A* search for the given scenario.

    1. Resets all global search structures.
    2. Builds the engine and asserts initial facts.
    3. Creates the root state node.
    4. Runs the main A* expansion loop.
    """
    # -- Reset global state --------------------------------------------------
    reset_search_structures()
    STATE_REGISTRY.clear()

    grid        = scenario["grid"]
    warehouse   = scenario["warehouse"]
    pavilions   = scenario["pavilions"]
    robot_start = scenario["robot_start"]
    capacity    = scenario["robot_capacity"]

    pavilion_positions = {
        p["pavilion_id"]: {"x": p["x"], "y": p["y"]}
        for p in pavilions
    }

    # Initial needs dict: {pavilion_id -> deep copy of needs list}
    initial_needs = {
        p["pavilion_id"]: copy.deepcopy(p["needs"])
        for p in pavilions
    }

    # -- Build engine --------------------------------------------------------
    engine = build_engine(scenario)
    engine.reset()

    # Assert static world facts
    engine.declare(Grid(rows=grid["rows"], cols=grid["cols"]))
    engine.declare(Warehouse(
        x     = warehouse["x"],
        y     = warehouse["y"],
        stock = copy.deepcopy(warehouse["stock"]),
    ))
    for p in pavilions:
        engine.declare(Pavilion(
            pavilion_id = p["pavilion_id"],
            x           = p["x"],
            y           = p["y"],
            needs       = copy.deepcopy(p["needs"]),
        ))

    # -- Create root state ---------------------------------------------------
    rx0, ry0 = robot_start["x"], robot_start["y"]
    inv0     = []   # robot starts empty
    h0       = compute_heuristic(rx0, ry0, initial_needs, pavilion_positions)
    root_id  = next_state_id()

    root_node = StateNode(
        state_id  = root_id,
        parent_id = None,
        action    = "start",
        robot_x   = rx0,
        robot_y   = ry0,
        inventory = inv0,
        needs     = initial_needs,
        g_cost    = 0,
        h_cost    = h0,
        f_cost    = h0,
    )
    register_state(root_node)
    push_open(h0, root_id)

    # Assert root State fact into working memory (inactive initially)
    engine.declare(State(
        state_id  = root_id,
        parent_id = None,
        action    = "start",
        robot_x   = rx0,
        robot_y   = ry0,
        inventory = inv0,
        needs     = initial_needs,
        g_cost    = 0,
        h_cost    = h0,
        f_cost    = h0,
        active    = False,
        capacity  = capacity,
    ))

    # -- Print initial grid --------------------------------------------------
    print("\nInitial grid layout:")
    print_grid(
        rows        = grid["rows"],
        cols        = grid["cols"],
        robot_x     = rx0,
        robot_y     = ry0,
        warehouse_x = warehouse["x"],
        warehouse_y = warehouse["y"],
        pavilions   = pavilions,
    )
    print(f"\nRobot capacity: {capacity}")
    print(f"Root state: {root_id}  h0={h0:.1f}\n")

    # -- A* main loop --------------------------------------------------------
    iteration = 0
    while not open_is_empty():
        iteration += 1

        # Pop the best state from the open list
        best_id = pop_open()
        if best_id is None:
            break

        # Retrieve the corresponding State fact from working memory
        best_fact = _find_state_fact(engine, best_id)
        if best_fact is None:
            # State was retracted by a constraint rule
            continue

        # Check if already closed (expanded before)
        sh = state_hash(
            best_fact["robot_x"], best_fact["robot_y"],
            best_fact["inventory"], best_fact["needs"]
        )
        if is_closed(sh):
            continue
        add_closed(sh)

        node = STATE_REGISTRY.get(best_id)
        print(
            f"\n[Iteration {iteration}] Expanding {best_id} "
            f"action={node.action!r} pos=({node.robot_x},{node.robot_y}) "
            f"g={node.g_cost} h={node.h_cost:.1f} f={node.f_cost:.1f}"
        )

        # Check goal before activation
        if is_goal(best_fact["inventory"], best_fact["needs"]):
            # Activate the fact so detect_goal rule fires
            engine.modify(best_fact, active=True)
            engine.run()
            break

        # Activate this state → triggers generation rules
        engine.modify(best_fact, active=True)
        engine.run()

        # Check if goal was asserted during this run
        if _goal_asserted(engine):
            break

    if open_is_empty() and not _goal_asserted(engine):
        print("\nSearch exhausted – no solution found.")


# ---------------------------------------------------------------------------
# Working memory helpers
# ---------------------------------------------------------------------------

def _find_state_fact(engine, state_id: str):
    """Return the State fact with the given state_id from working memory."""
    for fact in engine.facts.values():
        if isinstance(fact, State) and fact.get("state_id") == state_id:
            return fact
    return None


def _goal_asserted(engine) -> bool:
    """Return True if a Goal fact is present in working memory."""
    for fact in engine.facts.values():
        if isinstance(fact, Goal):
            return True
    return False
