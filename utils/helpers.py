"""
utils/helpers.py
----------------
Pure utility functions used by rule files and the heuristic.

Design principle: keep rules thin.  Every non-trivial decision (is this
move valid? is this load combination legal?) lives here as a testable
helper function with a clear docstring.

No Experta imports – these functions work on plain Python data.
"""

import json
from typing import List, Dict, Optional, Tuple


def _to_plain(obj):
    """Recursively convert Experta's frozendict / frozenlist wrappers (and
    plain dicts/lists/tuples) to standard Python dicts and lists so that
    json.dumps can serialise them.

    Experta internally stores dict fields as frozendict and list fields as
    frozenlist – both are non-JSON-serialisable.  We unwrap everything here
    before hashing.
    """
    # dict-like objects (includes frozendict)
    if hasattr(obj, 'items'):
        return {k: _to_plain(v) for k, v in obj.items()}
    # list-like / tuple-like objects (includes frozenlist)
    if isinstance(obj, (list, tuple)) or hasattr(obj, '__iter__') and not isinstance(obj, str):
        try:
            return [_to_plain(i) for i in obj]
        except TypeError:
            pass
    return obj


# ===========================================================================
# Movement helpers
# ===========================================================================

def is_valid_position(x: int, y: int, cols: int, rows: int) -> bool:
    """Return True if (x, y) is inside the grid boundaries.

    Args:
        x: column index (0-based)
        y: row index    (0-based)
        cols: total columns
        rows: total rows
    """
    return 0 <= x < cols and 0 <= y < rows


DIRECTIONS = {
    "move_right": ( 1,  0),
    "move_left":  (-1,  0),
    "move_down":  ( 0,  1),   # row increases downward
    "move_up":    ( 0, -1),
}


def apply_move(x: int, y: int, action: str) -> Tuple[int, int]:
    """Return the new (x, y) after applying a movement action."""
    dx, dy = DIRECTIONS[action]
    return x + dx, y + dy


# ===========================================================================
# Inventory helpers
# ===========================================================================

def inventory_total(inventory: List[Dict]) -> int:
    """Sum of all bouquet quantities in an inventory list."""
    return sum(b["quantity"] for b in inventory)


def find_bouquet(inventory: List[Dict], flower: str, color: str) -> Optional[Dict]:
    """Return the first matching bouquet dict in an inventory, or None."""
    for b in inventory:
        if b["flower"] == flower and b["color"] == color:
            return b
    return None


def add_to_inventory(inventory: List[Dict], flower: str, color: str, qty: int) -> None:
    """Add qty units of (flower, color) to inventory (mutates in place)."""
    existing = find_bouquet(inventory, flower, color)
    if existing:
        existing["quantity"] += qty
    else:
        inventory.append({"flower": flower, "color": color, "quantity": qty})


def remove_from_inventory(inventory: List[Dict], flower: str, color: str, qty: int) -> bool:
    """Remove qty units from inventory.  Returns False if not enough stock."""
    existing = find_bouquet(inventory, flower, color)
    if existing is None or existing["quantity"] < qty:
        return False
    existing["quantity"] -= qty
    if existing["quantity"] == 0:
        inventory.remove(existing)
    return True


# ===========================================================================
# Loading constraint validation
# ===========================================================================

def loading_mode(inventory: List[Dict]) -> Optional[str]:
    """Determine which loading mode the current inventory satisfies.

    MODE A – different flower types, same color.
    MODE B – same flower type, different colors.
    Returns 'A', 'B', or None if the inventory is empty (either mode OK).
    Raises ValueError if the inventory is already mixed-invalid.
    """
    if not inventory:
        return None  # empty: both modes are open

    flowers = {b["flower"] for b in inventory}
    colors  = {b["color"]  for b in inventory}

    if len(flowers) == 1:
        return "B"  # one flower type → MODE B
    if len(colors) == 1:
        return "A"  # one color → MODE A
    # multiple flowers AND multiple colors → illegal state (should not happen
    # if validation is applied before every load)
    raise ValueError("Inventory is in an invalid mixed state")


def can_load(inventory: List[Dict], flower: str, color: str,
             qty: int, capacity: int) -> Tuple[bool, str]:
    """Check whether loading qty units of (flower, color) is legal.

    Returns (True, "") on success or (False, reason) on failure.
    """
    # 1. Capacity check
    if inventory_total(inventory) + qty > capacity:
        return False, "exceeds capacity"

    # 2. Determine current loading mode
    try:
        mode = loading_mode(inventory)
    except ValueError:
        return False, "inventory already invalid"

    if mode is None:
        return True, ""   # empty inventory: any single item is fine

    if mode == "A":
        # All items must share the same color → new item must match that color
        existing_color = inventory[0]["color"]
        if color != existing_color:
            return False, f"Mode A: color must be {existing_color!r}"
        # New flower type must differ from all existing types
        existing_flowers = {b["flower"] for b in inventory}
        if flower in existing_flowers:
            # Same flower+color → just adding quantity to existing, that's fine
            pass
        return True, ""

    if mode == "B":
        # All items must share the same flower type → new item must match
        existing_flower = inventory[0]["flower"]
        if flower != existing_flower:
            return False, f"Mode B: flower must be {existing_flower!r}"
        # New color must differ from all existing colors (or same → add qty)
        return True, ""

    return False, "unknown mode"


# ===========================================================================
# Unloading validation
# ===========================================================================

def can_unload(inventory: List[Dict], needs: List[Dict],
               flower: str, color: str, qty: int) -> Tuple[bool, str]:
    """Check whether unloading qty units of (flower, color) at a pavilion is legal.

    Args:
        inventory: robot's current inventory
        needs:     remaining bouquet needs of the pavilion
        flower, color, qty: the bouquet being unloaded
    """
    # Must have the item in inventory
    inv_item = find_bouquet(inventory, flower, color)
    if inv_item is None or inv_item["quantity"] < qty:
        return False, "not enough in inventory"

    # Pavilion must actually need this item
    need_item = find_bouquet(needs, flower, color)
    if need_item is None or need_item["quantity"] <= 0:
        return False, "pavilion does not need this bouquet"

    # Partial unloading is allowed → qty <= need_item["quantity"]
    if qty > need_item["quantity"]:
        return False, "delivering more than needed"

    return True, ""


# ===========================================================================
# State hashing (duplicate detection)
# ===========================================================================

def state_hash(robot_x: int, robot_y: int,
               inventory: List[Dict],
               needs: Dict[str, List[Dict]]) -> str:
    """Produce a deterministic string hash for a search state.

    The hash captures exactly the information that distinguishes two states:
    robot position, sorted inventory, and sorted remaining needs.
    Two states with the same hash are considered duplicates.
    """
    # Convert frozendict/frozenset wrappers added by Experta to plain Python
    plain_inv   = _to_plain(list(inventory))
    plain_needs = _to_plain(dict(needs))

    # Sort inventory for canonical form
    sorted_inv = sorted(plain_inv, key=lambda b: (b["flower"], b["color"]))

    # Sort needs dict and each needs list
    sorted_needs = {
        pid: sorted(blist, key=lambda b: (b["flower"], b["color"]))
        for pid, blist in sorted(plain_needs.items())
    }

    payload = {
        "rx": robot_x,
        "ry": robot_y,
        "inv": sorted_inv,
        "needs": sorted_needs,
    }
    return json.dumps(payload, sort_keys=True)


# ===========================================================================
# Goal detection
# ===========================================================================

def is_goal(inventory: List[Dict], needs: Dict[str, List[Dict]]) -> bool:
    """Return True when all pavilion needs are satisfied and robot is empty."""
    if inventory:
        return False
    for blist in needs.values():
        for b in blist:
            if b["quantity"] > 0:
                return False
    return True


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
    """Standard Manhattan distance between two grid cells."""
    return abs(x1 - x2) + abs(y1 - y2)
