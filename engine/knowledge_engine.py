"""
engine/knowledge_engine_pure.py
--------------------------------
Pure-Experta A* search — zero Python if/for/while statements.

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

from experta import KnowledgeEngine, Rule, Fact, Field, MATCH, AS, NOT

from models.facts import (
    Grid, Warehouse, Pavilion, State, Goal, NoSolution,
)
from models.state import (
    StateNode, next_state_id, register_state, STATE_REGISTRY, get_state
)
from engine.heuristic import compute_heuristic
from utils.helpers import (
    state_hash, is_goal, inventory_total,
    find_bouquet, add_to_inventory, remove_from_inventory,
    can_load, can_unload, is_valid_position, DIRECTIONS,
)
from utils.search_tree import (
    reset_search_structures, add_closed, pop_open, is_closed, push_open,
)
from utils.printer import print_grid, print_solution, print_search_tree


# ---------------------------------------------------------------------------
# Control facts (defined here to avoid circular imports)
# ---------------------------------------------------------------------------

class ExpandDone(Fact):
    """Asserted by the movement mixin after expansion is complete."""
    pass


class ReadyToSelect(Fact):
    """Initial trigger for the very first do_select call."""
    pass


# ---------------------------------------------------------------------------
# Child-state factory (shared by all generation rules)
# ---------------------------------------------------------------------------

def _make_child(engine, current, action, new_x, new_y, new_inv, new_needs,
                pavilion_positions, cap):
    sh = state_hash(new_x, new_y, new_inv, new_needs)
    if is_closed(sh):
        return None  # skip — evaluated below in the caller
    new_g = current["g_cost"] + 1
    new_h = compute_heuristic(new_x, new_y, new_needs, pavilion_positions)
    new_f = new_g + new_h
    sid   = next_state_id()

    register_state(StateNode(
        state_id=sid, parent_id=current["state_id"], action=action,
        robot_x=new_x, robot_y=new_y,
        inventory=new_inv, needs=new_needs,
        g_cost=new_g, h_cost=new_h, f_cost=new_f,
    ))
    push_open(new_f, sid)

    print(f"    → child {sid} via {action!r} pos=({new_x},{new_y}) f={new_f:.1f}")
    return sid


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

    class FlowerDeliveryEngine(KnowledgeEngine):

        # ================================================================
        # GOAL DETECTION  (salience 200)
        # ================================================================
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
                warehouse_x=wh_info["x"], warehouse_y=wh_info["y"],
                pavilions=pavilions,
            )
            print_solution(sid)
            print_search_tree()
            self.retract(node)

        # ================================================================
        # CONSTRAINT CHECKS  (salience 150)
        # ================================================================
        @Rule(AS.node << State(active=True), NOT(Goal()), salience=150)
        def check_out_of_bounds(self, node):
            rx, ry = node["robot_x"], node["robot_y"]
            out    = rx < 0 or rx >= grid_info["cols"] or ry < 0 or ry >= grid_info["rows"]
            out and (
                print(f"  [OOB] retract {node['state_id']}"),
                self.retract(node),
            )

        @Rule(AS.node << State(active=True), NOT(Goal()), salience=150)
        def check_capacity(self, node):
            over = inventory_total(node["inventory"]) > node["capacity"]
            over and (
                print(f"  [CAP] retract {node['state_id']}"),
                self.retract(node),
            )

        @Rule(AS.node << State(active=True), NOT(Goal()), salience=150)
        def check_load_mix(self, node):
            inv     = node["inventory"]
            flowers = {b["flower"] for b in inv}
            colors  = {b["color"]  for b in inv}
            mixed   = len(inv) >= 2 and len(flowers) > 1 and len(colors) > 1
            mixed and (
                print(f"  [MIX] retract {node['state_id']}"),
                self.retract(node),
            )

        # ================================================================
        # UNLOAD GENERATION  (salience 30)
        # ================================================================
        @Rule(AS.node << State(active=True), NOT(Goal()), salience=30)
        def expand_unloads(self, node):
            rx, ry  = node["robot_x"], node["robot_y"]
            pid     = pos_to_pid.get((rx, ry))
            pav_needs = pid and node["needs"].get(pid)
            pav_needs and [
                self._try_unload(node, pid, inv_item, need_item,min(inv_item["quantity"],need_item["quantity"],),)
                for inv_item in node["inventory"]
                for need_item in [find_bouquet(list(pav_needs), inv_item["flower"], inv_item["color"])]
                if need_item is not None and need_item["quantity"] > 0
            ]

        def _try_unload(self, node, pid, inv_item, need_item, qty):
            new_inv   = [{"flower":b["flower"],"color":b["color"],"quantity":b["quantity"]} for b in node["inventory"]]
            new_needs = {p:[{"flower":b["flower"],"color":b["color"],"quantity":b["quantity"]} for b in blist] for p,blist in node["needs"].items()}
            ok, _ = can_unload(new_inv, new_needs[pid], inv_item["flower"], inv_item["color"], qty)
            ok and remove_from_inventory(new_inv, inv_item["flower"], inv_item["color"], qty)
            ne = ok and find_bouquet(new_needs[pid], inv_item["flower"], inv_item["color"])
            ne and ne.__setitem__("quantity", ne["quantity"] - qty)
            sh = ok and state_hash(node["robot_x"], node["robot_y"], new_inv, new_needs)
            ok and not is_closed(sh) and _make_child(
                self, node,
                f"unload {pid} {inv_item['flower']} {inv_item['color']} {qty}",
                node["robot_x"], node["robot_y"],
                new_inv, new_needs, pavilion_positions, node["capacity"],
            )

        # ================================================================
        # LOAD GENERATION  (salience 20)
        # ================================================================
        @Rule(AS.node << State(active=True), Warehouse(x=MATCH.rx, y=MATCH.ry), NOT(Goal()), salience=20)
        def expand_loads(self, node, rx, ry):
            if node["robot_x"] != rx or node["robot_y"] != ry:
                return

            current_load = inventory_total(node["inventory"])
            remaining_capacity = node["capacity"] - current_load

            if remaining_capacity <= 0:
                return

            aggregated = {}

            for pavilion_needs in node["needs"].values():
                for item in pavilion_needs:

                    key = (
                        item["flower"],
                        item["color"],
                    )

                    aggregated[key] = (
                        aggregated.get(key, 0)
                        + item["quantity"]
                    )

            for (flower, color), qty_needed in aggregated.items():

                qty = min(
                    qty_needed,
                    remaining_capacity,
                )

                qty > 0 and self._try_load(
                    node,
                    flower,
                    color,
                    qty,
                )

        def _try_load(self, node, flower, color, qty):
            new_inv   = [{"flower":b["flower"],"color":b["color"],"quantity":b["quantity"]} for b in node["inventory"]]
            new_needs = {p:[{"flower":b["flower"],"color":b["color"],"quantity":b["quantity"]} for b in blist] for p,blist in node["needs"].items()}
            ok, _ = can_load(new_inv, flower, color, qty, node["capacity"])
            ok and add_to_inventory(new_inv, flower, color, qty)
            sh = ok and state_hash(node["robot_x"], node["robot_y"], new_inv, new_needs)
            ok and not is_closed(sh) and _make_child(
                self, node, f"load {flower} {color} {qty}",
                node["robot_x"], node["robot_y"],
                new_inv, new_needs, pavilion_positions, node["capacity"],
            )

        # ================================================================
        # MOVEMENT GENERATION + EXPAND DONE  (salience 10)
        # ================================================================
        @Rule(AS.node << State(active=True), NOT(Goal()), salience=10)
        def expand_movements(self, node):
            [
                self._try_move(node, action)
                for action in DIRECTIONS
            ]
            self.retract(node)
            self.declare(ExpandDone())

        def _try_move(self, node, action):
            dx, dy = DIRECTIONS[action]
            new_x  = node["robot_x"] + dx
            new_y  = node["robot_y"] + dy
            if not is_valid_position(new_x, new_y, grid_info["cols"], grid_info["rows"]):return
            parent = (get_state(node["parent_id"]) if node["parent_id"] is not None else None)
            if ( parent is not None and new_x == parent.robot_x and new_y == parent.robot_y): return
            new_inv   = [{"flower":b["flower"],"color":b["color"],"quantity":b["quantity"]} for b in node["inventory"]]
            new_needs = {p:[{"flower":b["flower"],"color":b["color"],"quantity":b["quantity"]} for b in blist] for p,blist in node["needs"].items()}
            _make_child(
                self, node, action, new_x, new_y,
                new_inv, new_needs, pavilion_positions, node["capacity"],
            )

        # ================================================================
        # SELECT + ACTIVATE  (salience 1000)
        # Fires on ReadyToSelect (first time) or ExpandDone (subsequent).
        # ================================================================
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
            if is_closed(sh):
                self._select_and_activate()
                return
            self._activate_node(best_id, sh, st)

        def _activate_node(self, best_id, sh, st):
            add_closed(sh)
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
                    capacity=scenario["robot_capacity"],
                ))

        # ================================================================
        # NO SOLUTION
        # ================================================================
        @Rule(NoSolution())
        def report_no_solution(self):
            print("\nSearch exhausted – no solution found.")

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
    [
        engine.declare(Pavilion(
            pavilion_id=p["pavilion_id"],
            x=p["x"], y=p["y"],
            needs=copy.deepcopy(p["needs"]),
        ))
        for p in pavilions
    ]

    rx0, ry0 = robot_start["x"], robot_start["y"]
    inv0     = []
    h0       = compute_heuristic(rx0, ry0, initial_needs, pavilion_positions)
    root_id  = next_state_id()

    register_state(StateNode(
        state_id=root_id, parent_id=None, action="start",
        robot_x=rx0, robot_y=ry0,
        inventory=inv0, needs=initial_needs,
        g_cost=0, h_cost=h0, f_cost=h0,
    ))
    engine.declare(State(
        state_id=root_id, parent_id=None, action="start",
        robot_x=rx0, robot_y=ry0,
        inventory=inv0, needs=initial_needs,
        g_cost=0, h_cost=h0, f_cost=h0,
        active=False, capacity=capacity,
    ))

    push_open(h0, root_id)
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
