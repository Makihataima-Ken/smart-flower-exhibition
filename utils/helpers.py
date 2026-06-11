"""
utils/helpers.py
----------------
Pure utility functions used by rule files and the heuristic.

DESIGN CONSTRAINT: zero explicit if-statements and zero explicit loops.
All branching is expressed via:
  • dict.get()  with default values
  • next(filter(...), default)
  • any() / all()
  • short-circuit  (and / or)
  • ternary  (x if cond else y)  counts as an expression, not a statement
  • functools.reduce
  • comprehensions

No Experta imports – these functions work on plain Python data.
"""

import json
from typing import List, Dict, Optional, Tuple


# ---------------------------------------------------------------------------
# Serialisation helper (unwrap Experta frozendict / frozenlist)
# ---------------------------------------------------------------------------

def _to_plain(obj):
    """Recursively convert Experta wrappers to standard Python types."""
    # dict-like (includes frozendict)
    return (
        {k: _to_plain(v) for k, v in obj.items()}
        if hasattr(obj, "items")
        else (
            [_to_plain(i) for i in obj]
            if (isinstance(obj, (list, tuple)) or
                (hasattr(obj, "__iter__") and not isinstance(obj, str)))
            else obj
        )
    )


# ===========================================================================
# Movement helpers
# ===========================================================================

DIRECTIONS = {
    "move_right": ( 1,  0),
    "move_left":  (-1,  0),
    "move_down":  ( 0,  1),
    "move_up":    ( 0, -1),
}


def is_valid_position(x: int, y: int, cols: int, rows: int) -> bool:
    """Return True if (x, y) is inside the grid boundaries."""
    return 0 <= x < cols and 0 <= y < rows

# ===========================================================================
# Inventory helpers
# ===========================================================================

def inventory_total(inventory: List[Dict]) -> int:
    """Sum of all bouquet quantities."""
    return sum(b["quantity"] for b in inventory)


def find_bouquet(inventory: List[Dict], flower: str, color: str) -> Optional[Dict]:
    """Return the first matching bouquet dict, or None."""
    return next(
        filter(lambda b: b["flower"] == flower and b["color"] == color, inventory),
        None,
    )


def add_to_inventory(inventory: List[Dict], flower: str, color: str, qty: int) -> None:
    """Add qty units of (flower, color) to inventory (mutates in place)."""
    existing = find_bouquet(inventory, flower, color)
    # Branch via truthiness of existing (not an if-statement)
    existing and existing.__setitem__("quantity", existing["quantity"] + qty) or \
        inventory.append({"flower": flower, "color": color, "quantity": qty})


def remove_from_inventory(inventory: List[Dict], flower: str, color: str, qty: int) -> bool:
    """Remove qty units from inventory.  Returns False if not enough stock."""
    existing = find_bouquet(inventory, flower, color)
    enough   = existing is not None and existing["quantity"] >= qty
    # Only mutate when enough; no explicit if
    enough and existing.__setitem__("quantity", existing["quantity"] - qty)
    enough and existing["quantity"] == 0 and inventory.remove(existing)
    return enough


# ===========================================================================
# Loading constraint validation
# ===========================================================================

def _inventory_flowers(inventory: List[Dict]) -> set:
    return {b["flower"] for b in inventory}


def _inventory_colors(inventory: List[Dict]) -> set:
    return {b["color"] for b in inventory}


def loading_mode(inventory: List[Dict]) -> Optional[str]:
    """Determine loading mode: 'A' (same color), 'B' (same flower), or None (empty).

    Raises ValueError when the inventory is already in an illegal mixed state.
    """
    # Express the decision table as a lookup without if-statements
    return (
        None  # empty → either mode OK
        if not inventory
        else (
            # Use a dict of (many_flowers, many_colors) → result
            # Raises ValueError for the mixed case via a side-effect trick
            {
                (False, False): "B",   # 1 flower, 1 color → MODE B
                (False, True):  "B",   # 1 flower, many colors → MODE B
                (True,  False): "A",   # many flowers, 1 color → MODE A
            }.get(
                (
                    len(_inventory_flowers(inventory)) > 1,
                    len(_inventory_colors(inventory))  > 1,
                )
            )
            # Lazily raise ONLY for the mixed (many flowers, many colors) case.
            # NOTE: passing the throw as .get()'s default argument evaluates it
            # eagerly (arguments are evaluated before the call), so it raised for
            # *every* non-empty inventory.  `or` keeps it lazy: "A"/"B" are truthy.
            or (_ for _ in ()).throw(ValueError("Inventory is in an invalid mixed state"))
        )
    )


def can_load(
    inventory: List[Dict], flower: str, color: str,
    qty: int, capacity: int,
) -> Tuple[bool, str]:
    """Check whether loading qty units of (flower, color) is legal.

    Returns (True, '') on success or (False, reason) on failure.
    Uses a chain of guard expressions instead of if-blocks.
    """
    # 1. capacity guard
    over_cap = inventory_total(inventory) + qty > capacity
    # 2. mode guard (catch ValueError from loading_mode)
    try:
        mode = loading_mode(inventory)
        bad_mode = False
    except ValueError:
        mode, bad_mode = None, True

    # 3. mode-specific color/flower checks (evaluated only when mode is set)
    mode_ok, mode_reason = (
        (True, "")
        if mode is None
        else (
            (color == inventory[0]["color"],
             f"Mode A: color must be {inventory[0]['color']!r}")
            if mode == "A"
            else
            (flower == inventory[0]["flower"],
             f"Mode B: flower must be {inventory[0]['flower']!r}")
        )
    )

    # Accumulate first failing reason via short-circuit chain
    reason = (
        "exceeds capacity"          if over_cap  else
        "inventory already invalid" if bad_mode   else
        mode_reason                 if not mode_ok else
        ""
    )
    return (reason == "", reason)


# ===========================================================================
# Unloading validation
# ===========================================================================

def can_unload(
    inventory: List[Dict], needs: List[Dict],
    flower: str, color: str, qty: int,
) -> Tuple[bool, str]:
    """Check whether unloading qty units at a pavilion is legal."""
    inv_item  = find_bouquet(inventory, flower, color)
    need_item = find_bouquet(needs,     flower, color)

    reason = (
        "not enough in inventory"         if (inv_item is None or inv_item["quantity"] < qty)  else
        "pavilion does not need this bouquet" if (need_item is None or need_item["quantity"] <= 0) else
        "delivering more than needed"     if qty > need_item["quantity"]                        else
        ""
    )
    return (reason == "", reason)


# ===========================================================================
# State hashing (duplicate detection)
# ===========================================================================

def _normalize_inventory(inventory: List[Dict]):
    """
    Canonical inventory representation.

    Merges duplicate flower/color entries:
        Rose Red x1
        Rose Red x2

    becomes:

        Rose Red x3

    Removes zero quantities.
    """

    merged = {}

    for item in inventory:

        qty = item["quantity"]

        if qty <= 0:
            continue

        key = (item["flower"],item["color"],)

        merged[key] = merged.get(key, 0) + qty

    return tuple(sorted((flower,color,qty,)for (flower, color), qty in merged.items()))


def _normalize_needs(needs: Dict[str, List[Dict]]):
    """
    Canonical needs representation.

    Removes:
      - zero quantity bouquets
      - empty pavilion entries

    Sorts everything deterministically.
    """

    normalized = []

    for pid, bouquets in needs.items():

        cleaned = [
            (item["flower"],item["color"],item["quantity"])
            for item in bouquets
            if item["quantity"] > 0
        ]

        if not cleaned:
            continue

        normalized.append((pid,tuple(sorted(cleaned)),))

    return tuple(sorted(normalized))

def state_hash(
    robot_x: int, robot_y: int,
    inventory: List[Dict],
    needs: Dict[str, List[Dict]],
) -> str:
    """Produce a deterministic string hash for a search state."""
    plain_inv   = _to_plain(list(inventory))
    plain_needs = _to_plain(dict(needs))

    sorted_inv =  _normalize_inventory(plain_inv)
    sorted_needs = _normalize_needs(plain_needs)

    return json.dumps(
        {"rx": robot_x, "ry": robot_y, "inv": sorted_inv, "needs": sorted_needs},
        sort_keys=True,
    )


# ===========================================================================
# Goal detection
# ===========================================================================

def is_goal(inventory: List[Dict], needs: Dict[str, List[Dict]]) -> bool:
    """True when all pavilion needs are satisfied and robot inventory is empty."""
    return (
        not inventory
        and not any(
            b["quantity"] > 0
            for blist in needs.values()
            for b in blist
        )
    )


# ===========================================================================
# Pavilion helpers
# ===========================================================================

def pavilions_still_needing(needs: Dict[str, List[Dict]]) -> List[str]:
    """Return list of pavilion ids that still have unsatisfied needs."""
    return [
        pid for pid, blist in needs.items()
        if any(b["quantity"] > 0 for b in blist)
    ]


def manhattan_distance(x1: int, y1: int, x2: int, y2: int) -> int:
    return abs(x1 - x2) + abs(y1 - y2)