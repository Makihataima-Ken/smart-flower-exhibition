"""
utils/printer.py
----------------
All terminal output helpers.
Zero explicit if-statements or loops – uses comprehensions and builtins.
"""

from typing import List, Dict
from models.state import StateNode, STATE_REGISTRY, get_solution_path


def print_state_node(node: StateNode) -> None:
    inv_str = ", ".join(
        f"{b['flower']} {b['color']}×{b['quantity']}" for b in node.inventory
    ) or "empty"
    needs_str = " | ".join(
        f"{pid}:["
        + ", ".join(
            f"{b['flower']} {b['color']}×{b['quantity']}"
            for b in blist
            if b["quantity"] > 0
        )
        + "]"
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


def print_search_tree() -> None:
    nodes = sorted(STATE_REGISTRY.values(), key=lambda n: int(n.state_id[1:]))
    print("\n" + "=" * 80)
    print("SEARCH TREE  (all generated states)")
    print("=" * 80)
    [print_state_node(n) for n in nodes]
    print(f"\nTotal states generated: {len(nodes)}")
    print("=" * 80)


def _format_step(step: int, node: StateNode) -> str:
    inv_str = ", ".join(
        f"{b['flower']} {b['color']}×{b['quantity']}" for b in node.inventory
    ) or "empty"
    needs_lines = "\n".join(
        f"          {pid}: FULFILLED ✓"
        if not any(b["quantity"] > 0 for b in blist)
        else "          " + pid + " still needs: " + ", ".join(
            f"{b['flower']} {b['color']}×{b['quantity']}"
            for b in blist if b["quantity"] > 0
        )
        for pid, blist in node.needs.items()
    )
    return (
        f"\n  Step {step:>2d}  [{node.state_id}]  action={node.action!r}\n"
        f"          pos=({node.robot_x},{node.robot_y})  g={node.g_cost}\n"
        f"          inventory: {inv_str}\n"
        f"{needs_lines}"
    )


def print_solution(goal_state_id: str) -> None:
    path = get_solution_path(goal_state_id)
    print("\n" + "=" * 80)
    print("SOLUTION PATH")
    print("=" * 80)
    [print(_format_step(i, n)) for i, n in enumerate(path)] or print("  (no path found)")
    print(f"\n  Total cost (g): {path[-1].g_cost}" if path else "")
    print("=" * 80)


def print_grid(
    rows: int, cols: int,
    robot_x: int, robot_y: int,
    warehouse_x: int, warehouse_y: int,
    pavilions: List[Dict],
) -> None:
    """Draw an ASCII grid showing R (robot), W (warehouse), and pavilion IDs."""
    symbols: Dict[tuple, str] = {
        (warehouse_x, warehouse_y): "W",
        (robot_x, robot_y): "R",
        **{(p["x"], p["y"]): p["pavilion_id"] for p in pavilions},
    }

    col_width = 4
    header    = "    " + "".join(f"{c:>{col_width}}" for c in range(cols))
    separator = "    " + "+---" * cols + "+"

    print(header)
    [
        (
            print(separator),
            print(
                f" {r:>2} "
                + "".join(f"| {symbols.get((c, r), ' '):<2}" for c in range(cols))
                + "|"
            ),
        )
        for r in range(rows)
    ]
    print(separator)
