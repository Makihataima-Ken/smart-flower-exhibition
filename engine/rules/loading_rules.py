"""
engine/rules/loading_rules.py
-----------------------------
Experta rule that expands loading actions from the warehouse.

Salience 20 (above movement=10, below unloading=30).

DESIGN (combination loading)
----------------------------
Instead of emitting one child per individual demand item, the warehouse
expansion now generates *maximal compatible loading combinations*: it fills
the robot as much as the capacity and the Mode-A/Mode-B constraints allow,
and emits one child per maximal combination.

This mirrors the "unload-all" operator in unloading_rules.py: a whole trip's
worth of loading is a single action.  That keeps the cost model consistent
with the heuristic, which charges exactly +1 load and +1 unload per trip.
As a result A* evaluates the true cost of a *full* trip and stops leaving the
warehouse partially loaded / taking redundant trips.
"""
import collections.abc
import collections
collections.Mapping = collections.abc.Mapping

from experta import Rule, AS, MATCH, NOT

from models.facts import State, Warehouse, Goal
from utils.helpers import can_load, add_to_inventory, inventory_total
from utils.search_tree import push_open


# ---------------------------------------------------------------------------
# Step 1 — gather outstanding demand that still needs to be *loaded*
# ---------------------------------------------------------------------------

def _gather_demand(node):
    """Aggregate all outstanding demand the robot still has to load.

    Demand is summed per (flower, color) across every pavilion, then the
    quantity already sitting in the robot's inventory is subtracted (those
    units are loaded already, they only need delivering).  Items with no
    remaining quantity to load are dropped.

    Returns a list of (flower, color, quantity) tuples, e.g.

        [("Rose", "Red", 2), ("Rose", "White", 1), ("Tulip", "Red", 2)]
    """
    need = {}
    for blist in node["needs"].values():
        for item in blist:
            qty = item["quantity"]
            if qty > 0:
                key = (item["flower"], item["color"])
                need[key] = need.get(key, 0) + qty

    held = {}
    for b in node["inventory"]:
        key = (b["flower"], b["color"])
        held[key] = held.get(key, 0) + b["quantity"]

    return [
        (flower, color, need[(flower, color)] - held.get((flower, color), 0))
        for (flower, color) in need
        if need[(flower, color)] - held.get((flower, color), 0) > 0
    ]


# ---------------------------------------------------------------------------
# Step 2 — recursively build every legal loading combination
# ---------------------------------------------------------------------------

def _copy_inventory(inventory):
    return [
        {"flower": b["flower"], "color": b["color"], "quantity": b["quantity"]}
        for b in inventory
    ]


def _generate_combinations(inventory, remaining_capacity, candidates, capacity,
                           start=0):
    """Enumerate legal loading combinations reachable from `inventory`.

    For each candidate (in a fixed forward order so that a given *set* of
    bouquets is produced once, not once per permutation):

      1. compute how much can be added: min(remaining_demand, remaining_cap)
      2. check legality via can_load()  (capacity + Mode-A/Mode-B rules)
      3. add as much as possible and recurse on the *later* candidates
      4. when nothing further can be added, record the resulting inventory

    Because we add "as much as possible" of a candidate, the only branching is
    *which* candidates to include, not how to split their quantities.  The
    set of returned inventories is post-filtered to the maximal ones by the
    caller.
    """
    results = []
    extended = False

    for i in range(start, len(candidates)):
        flower, color, demand = candidates[i]
        addable = min(demand, remaining_capacity)
        if addable <= 0:
            continue

        ok, _ = can_load(inventory, flower, color, addable, capacity)
        if not ok:
            continue

        extended = True
        new_inv = _copy_inventory(inventory)
        add_to_inventory(new_inv, flower, color, addable)
        results.extend(
            _generate_combinations(
                new_inv, remaining_capacity - addable,
                candidates, capacity, i + 1,
            )
        )

    # No forward candidate could be added → this inventory is a leaf.
    if not extended:
        results.append(inventory)

    return results


# ---------------------------------------------------------------------------
# Step 3 — keep only the maximal combinations
# ---------------------------------------------------------------------------

def _inventory_key(inventory):
    """Canonical hashable key for a combination (order-independent)."""
    return tuple(sorted(
        (b["flower"], b["color"], b["quantity"]) for b in inventory
    ))


def _is_maximal(inventory, candidates, capacity):
    """True when no further candidate can legally be added to `inventory`.

    A combination is maximal iff every still-loadable candidate is either
    already fully present or blocked by capacity / loading-mode rules.
    """
    remaining_capacity = capacity - inventory_total(inventory)
    if remaining_capacity <= 0:
        return True

    present = {(b["flower"], b["color"]) for b in inventory}
    return not any(
        (flower, color) not in present
        and min(demand, remaining_capacity) > 0
        and can_load(inventory, flower, color,
                     min(demand, remaining_capacity), capacity)[0]
        for flower, color, demand in candidates
    )


def _maximal_combinations(base_inventory, candidates, capacity):
    """Return the deduplicated, maximal, non-trivial loading combinations."""
    remaining_capacity = capacity - inventory_total(base_inventory)
    raw = _generate_combinations(
        base_inventory, remaining_capacity, candidates, capacity,
    )

    base_load = inventory_total(base_inventory)
    seen = set()
    combos = []
    for inv in raw:
        # must actually load something and must be maximal
        if inventory_total(inv) <= base_load:
            continue
        if not _is_maximal(inv, candidates, capacity):
            continue
        key = _inventory_key(inv)
        if key in seen:
            continue
        seen.add(key)
        combos.append(inv)
    return combos


# ---------------------------------------------------------------------------
# Step 4 — turn each maximal combination into a child state
# ---------------------------------------------------------------------------

def _describe_load(base_inventory, combo):
    """Human-readable action, e.g. 'load Rose Red 2 + Rose White 1'."""
    held = {}
    for b in base_inventory:
        held[(b["flower"], b["color"])] = held.get((b["flower"], b["color"]), 0) + b["quantity"]

    parts = []
    for b in combo:
        delta = b["quantity"] - held.get((b["flower"], b["color"]), 0)
        if delta > 0:
            parts.append(f"{b['flower']} {b['color']} {delta}")
    return "load " + " + ".join(parts)


def _make_child(engine, current, action, new_x, new_y, new_inv, new_needs,
                pavilion_positions, cap, warehouse_pos):
    from engine.heuristic import compute_heuristic
    from models.state import StateNode, next_state_id, register_state
    from utils.helpers import state_hash
    from utils.search_tree import should_expand

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


def make_loading_mixin(pavilion_positions: dict, warehouse_pos: dict):
    """Return loading mixin closed over pavilion positions and warehouse position."""

    class LoadingRules:

        @Rule(
            AS.node << State(active=True),
            Warehouse(x=MATCH.rx, y=MATCH.ry),
            NOT(Goal()),
            salience=20,
        )
        def expand_loads(self, node, rx, ry):
            # Only fire when the robot is actually standing on the warehouse.
            if node["robot_x"] != rx or node["robot_y"] != ry:
                return

            capacity = node["capacity"]
            if capacity - inventory_total(node["inventory"]) <= 0:
                return

            candidates = _gather_demand(node)
            if not candidates:
                return

            base_inventory = _copy_inventory(node["inventory"])
            combos = _maximal_combinations(base_inventory, candidates, capacity)

            # Step 4/5 — one child per maximal combination (replaces the old
            # "one child per individual need item" behaviour).
            for combo in combos:
                new_needs = {
                    p: [
                        {"flower": b["flower"], "color": b["color"], "quantity": b["quantity"]}
                        for b in blist
                    ]
                    for p, blist in node["needs"].items()
                }
                _make_child(
                    self, node,
                    _describe_load(base_inventory, combo),
                    node["robot_x"], node["robot_y"],
                    combo, new_needs,
                    pavilion_positions, capacity, warehouse_pos,
                )

    return LoadingRules
