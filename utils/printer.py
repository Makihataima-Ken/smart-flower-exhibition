"""
utils/printer.py
----------------
Handles all terminal output:
  • print_state_node  – one-line summary of a single search node
  • print_search_tree – table of all generated states
  • print_solution    – step-by-step solution path
  • print_grid        – ASCII visualisation of the grid at a given state
"""

from typing import List, Dict
from models.state import StateNode, STATE_REGISTRY, get_solution_path


# ---------------------------------------------------------------------------
# Single node summary
# ---------------------------------------------------------------------------
def print_state_node(node: StateNode) -> None:
    """Print a compact one-line summary of a StateNode."""
    inv_str = ", ".join(
        f"{b['flower']} {b['color']}×{b['quantity']}"
        for b in node.inventory
    ) or "empty"
    needs_str = " | ".join(
        f"{pid}:[" + ", ".join(
            f"{b['flower']} {b['color']}×{b['quantity']}"
            for b in blist if b["quantity"] > 0
        ) + "]"
        for pid, blist in node.needs.items()
    )
    print(
        f"  [{node.state_id}] parent={node.parent_id} "
        f"action={node.action!r:20s} "
        f"pos=({node.robot_x},{node.robot_y}) "
        f"inv=[{inv_str}] "
        f"needs={{{needs_str}}} "
        f"g={node.g_cost} h={node.h_cost:.1f} f={node.f_cost:.1f}"
    )


# ---------------------------------------------------------------------------
# Full search tree
# ---------------------------------------------------------------------------
def print_search_tree() -> None:
    """Print all states stored in STATE_REGISTRY, ordered by state_id number."""
    nodes = sorted(STATE_REGISTRY.values(), key=lambda n: int(n.state_id[1:]))
    print("\n" + "=" * 80)
    print("SEARCH TREE  (all generated states)")
    print("=" * 80)
    for node in nodes:
        print_state_node(node)
    print(f"\nTotal states generated: {len(nodes)}")
    print("=" * 80)


# ---------------------------------------------------------------------------
# Solution path
# ---------------------------------------------------------------------------
def print_solution(goal_state_id: str) -> None:
    """Reconstruct and print the solution path from root to goal."""
    path = get_solution_path(goal_state_id)

    print("\n" + "=" * 80)
    print("SOLUTION PATH")
    print("=" * 80)

    if not path:
        print("  (no path found)")
        return

    total_cost = path[-1].g_cost
    for step, node in enumerate(path):
        print(f"\n  Step {step:>2d}  [{node.state_id}]  action={node.action!r}")
        print(f"          pos=({node.robot_x},{node.robot_y})  g={node.g_cost}")
        inv_str = ", ".join(
            f"{b['flower']} {b['color']}×{b['quantity']}"
            for b in node.inventory
        ) or "empty"
        print(f"          inventory: {inv_str}")
        for pid, blist in node.needs.items():
            rem = [b for b in blist if b["quantity"] > 0]
            if rem:
                rem_str = ", ".join(
                    f"{b['flower']} {b['color']}×{b['quantity']}" for b in rem
                )
                print(f"          {pid} still needs: {rem_str}")
            else:
                print(f"          {pid}: FULFILLED ✓")

    print(f"\n  Total cost (g): {total_cost}")
    print("=" * 80)


# ---------------------------------------------------------------------------
# ASCII grid visualiser
# ---------------------------------------------------------------------------
def print_grid(
    rows: int, cols: int,
    robot_x: int, robot_y: int,
    warehouse_x: int, warehouse_y: int,
    pavilions: List[Dict],       # [{"pavilion_id", "x", "y"}]
) -> None:
    """Draw an ASCII grid showing robot (R), warehouse (W), pavilions (P)."""

    # Build a symbol table
    symbols: Dict[tuple, str] = {}
    symbols[(warehouse_x, warehouse_y)] = "W"
    symbols[(robot_x, robot_y)] = "R"
    for p in pavilions:
        symbols[(p["x"], p["y"])] = p["pavilion_id"]

    col_width = 4
    header = "    " + "".join(f"{c:>{col_width}}" for c in range(cols))
    separator = "    " + "+---" * cols + "+"

    print(header)
    for r in range(rows):
        print(separator)
        row_cells = ""
        for c in range(cols):
            sym = symbols.get((c, r), " ")
            row_cells += f"| {sym:<2}"
        print(f" {r:>2} {row_cells}|")
    print(separator)
