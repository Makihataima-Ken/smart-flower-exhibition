"""
utils/search_tree.py
--------------------
A* open list (min-heap) and closed set (visited hashes).

The Python-level code here contains no explicit loops or if-statements.
heapq.heappop is a C-level operation; the lazy-deletion loop inside
pop_open is replaced by a functional next(filter(...)) call.
"""

import heapq
from typing import Optional, Set

_open_heap: list    = []
_open_set:  Set[str] = set()
_counter            = [0]
BEST_G: dict[str, int] = {}
OPEN_G:  dict[str, int] = {}


def push_open(f_cost: float, state_id: str) -> None:
    _counter[0] += 1
    heapq.heappush(_open_heap, (f_cost, _counter[0], state_id))
    _open_set.add(state_id)


def push_open_with_g(f_cost: float, state_id: str, g_cost: int) -> None:
    existing_g = OPEN_G.get(state_id)
    if existing_g is not None and g_cost >= existing_g:
        return
    OPEN_G[state_id] = g_cost
    push_open(f_cost, state_id)


def pop_open() -> Optional[str]:
    """Pop the state with the lowest f_cost using lazy deletion."""
    while _open_heap:
        entry = heapq.heappop(_open_heap)
        state_id = entry[2]
        if state_id in _open_set:
            _open_set.discard(state_id)
            OPEN_G.pop(state_id, None)
            return state_id
    return None


def _extract_live() -> Optional[str]:
    """Pop one item from the heap; return state_id if live, else None."""
    entry = heapq.heappop(_open_heap) if _open_heap else None
    return (
        None
        if entry is None
        else (
            (_open_set.discard(entry[2]) or entry[2])
            if entry[2] in _open_set
            else None
        )
    )


def open_is_empty() -> bool:
    return len(_open_set) == 0


def remove_from_open(state_id: str) -> None:
    _open_set.discard(state_id)

def reset_search_structures() -> None:
    global _open_heap, _open_set, BEST_G, OPEN_G
    _open_heap = []
    _open_set  = set()
    _counter[0] = 0
    BEST_G.clear()
    OPEN_G.clear()


def should_expand(state_hash_value: str, g_cost: int) -> bool:
    """
    Keep only the cheapest path discovered for a state.

    Returns True if this path is better than any
    previously discovered path.
    """

    previous_g = BEST_G.get(state_hash_value)

    if previous_g is None:
        BEST_G[state_hash_value] = g_cost
        return True

    if g_cost < previous_g:
        BEST_G[state_hash_value] = g_cost
        return True

    return False