"""
main.py
-------
Entry point for the Smart Flower Exhibition Knowledge-Based System.

Examples:

    python main.py

    python main.py --scenario data/scenarios/sample_case.json

    python main.py --scenario data/scenarios/sample_case.json --visualize
"""

import sys
import argparse

# Force UTF-8 output on supported streams
[
    (
        lambda s:
        hasattr(s, "reconfigure")
        and s.reconfigure(encoding="utf-8")
    )(stream)
    for stream in (sys.stdout, sys.stderr)
]

from data.scenario_loader import load_scenario
from engine.knowledge_engine import run_search
from models.state import get_solution_path

try:
    from visualization.animator import SolutionAnimator
except Exception:
    SolutionAnimator = None


def parse_args():
    """
    Parse command-line arguments.
    """

    parser = argparse.ArgumentParser(
        description="Smart Flower Exhibition Knowledge-Based System"
    )

    parser.add_argument(
        "--scenario",
        default="data/scenarios/sample_case.json",
        help="Path to scenario JSON file"
    )

    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Replay solution using pygame visualization"
    )

    return parser.parse_args()


def print_scenario_summary(scenario):
    """
    Pretty-print scenario information.
    """

    warehouse = scenario["warehouse"]
    robot = scenario["robot_start"]

    print(
        "\nScenario summary:\n"
        f"  Grid:        {scenario['grid']['cols']} cols × "
        f"{scenario['grid']['rows']} rows\n"
        f"  Warehouse:   ({warehouse['x']}, {warehouse['y']})\n"
        f"  Robot start: ({robot['x']}, {robot['y']})\n"
        f"  Capacity:    {scenario['robot_capacity']}\n"
        f"  Pavilions:   {len(scenario['pavilions'])}"
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


def launch_visualization(scenario, goal_state_id):
    """
    Replay the solution path using pygame.
    """

    if SolutionAnimator is None:
        print(
            "\nVisualization unavailable "
            "(pygame not installed or failed to import)."
        )
        return

    solution_path = get_solution_path(goal_state_id)

    animator = SolutionAnimator(
        scenario,
        solution_path
    )

    try:
        animator.run()

    except RuntimeError as exc:
        print(f"Failed to start visualizer: {exc}")


def main():
    """
    Program entry point.
    """

    args = parse_args()

    print("=" * 60)
    print("  Smart Flower Exhibition – Knowledge-Based System")
    print("  Using Experta (Python Expert System)")
    print("=" * 60)

    scenario = load_scenario(args.scenario)

    print_scenario_summary(scenario)

    print("\nStarting A* search...\n")

    goal_state_id = run_search(scenario)

    if not goal_state_id:
        print("\nNo solution found.")
        return

    if args.visualize:
        launch_visualization(
            scenario,
            goal_state_id
        )


if __name__ == "__main__":
    main()