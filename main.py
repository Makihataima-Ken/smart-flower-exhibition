"""
main.py
-------
Entry point for the Smart Flower Exhibition Knowledge-Based System.

Run with:
    python main.py

This file:
  1. Loads the sample scenario from data/sample_case.py
  2. Packages it into a scenario dict
  3. Calls run_search() to start the A* search engine
"""

import sys

# Force UTF-8 on stdout/stderr so Unicode glyphs (e.g. →) print on Windows
# consoles that default to a legacy code page like cp1252.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

from data.sample_case import (
    GRID, WAREHOUSE, PAVILIONS, ROBOT_START, ROBOT_CAPACITY
)
from engine.knowledge_engine import run_search


def main():
    print("=" * 60)
    print("  Smart Flower Exhibition – Knowledge-Based System")
    print("  Using Experta (Python Expert System)")
    print("=" * 60)

    # Package scenario data into a single dict for the engine
    scenario = {
        "grid":           GRID,
        "warehouse":      WAREHOUSE,
        "pavilions":      PAVILIONS,
        "robot_start":    ROBOT_START,
        "robot_capacity": ROBOT_CAPACITY,
    }

    print(f"\nScenario summary:")
    print(f"  Grid:       {GRID['cols']} cols × {GRID['rows']} rows")
    print(f"  Warehouse:  ({WAREHOUSE['x']}, {WAREHOUSE['y']})")
    print(f"  Robot start:({ROBOT_START['x']}, {ROBOT_START['y']})")
    print(f"  Capacity:   {ROBOT_CAPACITY}")
    print(f"  Pavilions:  {len(PAVILIONS)}")
    for p in PAVILIONS:
        needs_str = ", ".join(
            f"{b['flower']} {b['color']}×{b['quantity']}"
            for b in p["needs"]
        )
        print(f"    {p['pavilion_id']} at ({p['x']},{p['y']}): needs [{needs_str}]")

    print("\nStarting A* search...\n")
    run_search(scenario)


if __name__ == "__main__":
    main()
