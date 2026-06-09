"""
main.py
-------
Entry point for the Smart Flower Exhibition Knowledge-Based System.

Zero explicit if-statements or loops – all branching via short-circuit
expressions, ternary expressions, and comprehensions.
"""

import sys

# Force UTF-8 output (side-effect call, no if needed)
[
    (lambda s: (hasattr(s, "reconfigure") and s.reconfigure(encoding="utf-8")))(stream)
    for stream in (sys.stdout, sys.stderr)
]

from data.scenario_loader import load_scenario
from engine.knowledge_engine import run_search
from models.state import get_solution_path

try:
    from visualization.animator import SolutionAnimator
except Exception:
    SolutionAnimator = None


def main():
    print("=" * 60)
    print("  Smart Flower Exhibition – Knowledge-Based System")
    print("  Using Experta (Python Expert System)")
    print("=" * 60)

    scenario = load_scenario("data/scenarios/sample_case.json")

    warehouse = scenario["warehouse"]
    robot     = scenario["robot_start"]

    print(
        "\nScenario summary:\n"
        f"  Grid:        {scenario['grid']['cols']} cols × {scenario['grid']['rows']} rows\n"
        f"  Warehouse:   ({warehouse['x']}, {warehouse['y']})\n"
        f"  Robot start: ({robot['x']}, {robot['y']})\n"
        f"  Capacity:    {scenario['robot_capacity']}\n"
        f"  Pavilions:   {len(scenario['pavilions'])}"
    )

    [
        print(
            f"    {p['pavilion_id']} at ({p['x']},{p['y']}): needs ["
            + ", ".join(
                f"{item['flower']} {item['color']}×{item['quantity']}"
                for item in p["needs"]
            )
            + "]"
        )
        for p in scenario["pavilions"]
    ]

    print("\nStarting A* search...\n")

    goal_state_id = run_search(scenario)

    # Launch visualiser only when a goal was found and pygame is available
    goal_state_id and SolutionAnimator and _animate(scenario, goal_state_id)
    goal_state_id and (SolutionAnimator is None) and print(
        "Visualization not available (pygame may be missing). Skipping replay."
    )


def _animate(scenario, goal_state_id):
    solution_path = get_solution_path(goal_state_id)
    animator      = SolutionAnimator(scenario, solution_path)
    try:
        animator.run()
    except RuntimeError as e:
        print("Failed to start visualizer:", e)


if __name__ == "__main__":
    main()