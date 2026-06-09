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

from data.scenario_loader import load_scenario
from engine.knowledge_engine import run_search


def main():

    print("=" * 60)
    print("  Smart Flower Exhibition – Knowledge-Based System")
    print("  Using Experta (Python Expert System)")
    print("=" * 60)

    scenario = load_scenario(
        "data/scenarios/sample_case.json"
    )

    print("\nScenario summary:")

    print(
        f"  Grid: "
        f"{scenario['grid']['cols']} cols × "
        f"{scenario['grid']['rows']} rows"
    )

    warehouse = scenario["warehouse"]

    print(
        f"  Warehouse: "
        f"({warehouse['x']}, {warehouse['y']})"
    )

    robot = scenario["robot_start"]

    print(
        f"  Robot start:"
        f"({robot['x']}, {robot['y']})"
    )

    print(
        f"  Capacity: "
        f"{scenario['robot_capacity']}"
    )

    print(
        f"  Pavilions: "
        f"{len(scenario['pavilions'])}"
    )

    for pavilion in scenario["pavilions"]:

        needs_str = ", ".join(
            f"{item['flower']} "
            f"{item['color']}×{item['quantity']}"
            for item in pavilion["needs"]
        )

        print(
            f"    {pavilion['pavilion_id']} "
            f"at ({pavilion['x']},{pavilion['y']}): "
            f"needs [{needs_str}]"
        )

    print("\nStarting A* search...\n")

    run_search(scenario)


if __name__ == "__main__":
    main()
