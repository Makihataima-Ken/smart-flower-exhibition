from math import inf


def manhattan_distance(x1, y1, x2, y2):
    """
    Manhattan distance for grid movement.
    """

    return abs(x1 - x2) + abs(y1 - y2)


def is_inside_grid(x, y, width, height):
    """
    Check if position is inside grid boundaries.
    """

    return (
        0 <= x < width and
        0 <= y < height
    )


def total_inventory_quantity(inventory):
    """
    Count total bouquets carried by robot.
    """

    return sum(
        item["quantity"]
        for item in inventory
    )


def valid_inventory_combination(inventory):
    """
    Check loading constraints.

    Valid if:
    1. Same flower type with different colors
    OR
    2. Same color with different flower types
    """

    if not inventory:
        return True

    flower_types = {
        item["flower"]
        for item in inventory
    }

    colors = {
        item["color"]
        for item in inventory
    }

    same_flower = len(flower_types) == 1
    same_color = len(colors) == 1

    return same_flower or same_color


def exceeds_capacity(inventory, max_capacity):
    """
    Check robot max load.
    """

    return (
        total_inventory_quantity(inventory)
        > max_capacity
    )


def can_unload_to_pavilion(
    inventory_item,
    pavilion_flower_type,
    pavilion_needs
):
    """
    Check if bouquet can be unloaded.
    """

    same_flower = (
        inventory_item["flower"]
        == pavilion_flower_type
    )

    needed_color = (
        inventory_item["color"]
        in pavilion_needs
    )

    remaining_quantity = (
        pavilion_needs.get(
            inventory_item["color"],
            0
        ) > 0
    )

    return (
        same_flower and
        needed_color and
        remaining_quantity
    )


def heuristic_remaining_bouquets(remaining_needs):
    """
    Simple heuristic:
    Total remaining bouquets.
    """

    total = 0

    for pavilion in remaining_needs.values():

        total += sum(
            pavilion.values()
        )

    return total


def heuristic_nearest_pavilion(
    robot_x,
    robot_y,
    pavilion_positions,
    remaining_needs
):
    """
    Distance to nearest pavilion
    still needing bouquets.
    """

    best_distance = inf

    for pavilion_id, needs in remaining_needs.items():

        remaining = sum(needs.values())

        if remaining <= 0:
            continue

        px, py = pavilion_positions[pavilion_id]

        distance = manhattan_distance(
            robot_x,
            robot_y,
            px,
            py
        )

        best_distance = min(
            best_distance,
            distance
        )

    if best_distance == inf:
        return 0

    return best_distance


def calculate_heuristic(
    robot_x,
    robot_y,
    pavilion_positions,
    remaining_needs
):
    """
    Combined heuristic for A*.
    """

    return (
        heuristic_remaining_bouquets(
            remaining_needs
        )
        +
        heuristic_nearest_pavilion(
            robot_x,
            robot_y,
            pavilion_positions,
            remaining_needs
        )
    )