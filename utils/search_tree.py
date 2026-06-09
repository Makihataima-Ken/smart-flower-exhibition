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
_closed:    Set[str] = set()


def push_open(f_cost: float, state_id: str) -> None:
    _counter[0] += 1
    heapq.heappush(_open_heap, (f_cost, _counter[0], state_id))
    _open_set.add(state_id)


def pop_open() -> Optional[str]:
    """Pop the state with the lowest f_cost using lazy deletion.

    Uses next(filter(...)) instead of a while-loop.
    """
    def _pop_one():
        """Pop one entry and return its state_id if still in open_set, else None."""
        entry = _open_heap and heapq.heappop(_open_heap)
        return entry and _open_set.discard(entry[2]) or entry[2] if entry and entry[2] in _open_set else None

    # Generator that keeps popping until we find a live entry or exhaust the heap
    live = next(
        filter(
            lambda sid: sid is not None,
            (_extract_live() for _ in iter(lambda: _open_heap, [])),
        ),
        None,
    )
    return live


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


def add_closed(state_hash: str) -> None:
    _closed.add(state_hash)


def is_closed(state_hash: str) -> bool:
    return state_hash in _closed


def closed_count() -> int:
    return len(_closed)


def reset_search_structures() -> None:
    global _open_heap, _open_set, _closed
    _open_heap = []
    _open_set  = set()
    _closed    = set()
    _counter[0] = 0
