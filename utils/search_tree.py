"""
utils/search_tree.py
--------------------
Manages the A* open list (frontier) and closed set (visited hashes).

We implement the open list as a min-heap ordered by f_cost so that the
engine always expands the most promising node first.

The closed set stores state hashes to detect and skip duplicates.

These structures live *outside* Experta's working memory so they can be
inspected and manipulated by helper code without needing a rule context.
The knowledge engine calls push/pop and records visits through this module.
"""

import heapq
from typing import Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Open list  (min-heap on f_cost)
# ---------------------------------------------------------------------------
# Each entry: (f_cost, tie-breaker counter, state_id)
# The counter ensures stable ordering when f_costs are equal.

_open_heap: list = []
_open_set: Set[str] = set()   # state_ids currently in the heap
_counter = [0]                 # tie-breaker


def push_open(f_cost: float, state_id: str) -> None:
    """Add state_id to the open list with priority f_cost."""
    _counter[0] += 1
    heapq.heappush(_open_heap, (f_cost, _counter[0], state_id))
    _open_set.add(state_id)


def pop_open() -> Optional[str]:
    """Remove and return the state_id with the lowest f_cost.
    Returns None if the open list is empty.
    Skips state_ids that were already removed (lazy deletion).
    """
    while _open_heap:
        _f, _c, state_id = heapq.heappop(_open_heap)
        if state_id in _open_set:
            _open_set.discard(state_id)
            return state_id
    return None


def open_is_empty() -> bool:
    """Return True when no states remain to be expanded."""
    return len(_open_set) == 0


def remove_from_open(state_id: str) -> None:
    """Mark a state_id as removed (lazy deletion – it stays in heap but
    will be skipped on pop)."""
    _open_set.discard(state_id)


# ---------------------------------------------------------------------------
# Closed set (visited hashes)
# ---------------------------------------------------------------------------
_closed: Set[str] = set()


def add_closed(state_hash: str) -> None:
    """Record a state hash as visited/expanded."""
    _closed.add(state_hash)


def is_closed(state_hash: str) -> bool:
    """Return True if this hash was already expanded."""
    return state_hash in _closed


def closed_count() -> int:
    return len(_closed)


# ---------------------------------------------------------------------------
# Reset (useful for running multiple scenarios in one session)
# ---------------------------------------------------------------------------
def reset_search_structures() -> None:
    """Clear the open list and closed set."""
    global _open_heap, _open_set, _closed
    _open_heap = []
    _open_set = set()
    _closed = set()
    _counter[0] = 0
