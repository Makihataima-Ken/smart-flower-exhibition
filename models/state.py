import copy
import json


def create_state(
    state_id,
    parent_id,
    action,
    robot_x,
    robot_y,
    inventory,
    remaining_needs,
    g_cost=0,
    h_cost=0,
):
    """
    Create a normalized state dictionary.
    """

    return {
        "state_id": state_id,
        "parent_id": parent_id,
        "action": action,

        "robot_x": robot_x,
        "robot_y": robot_y,

        "inventory": copy.deepcopy(inventory),

        "remaining_needs": copy.deepcopy(remaining_needs),

        "g_cost": g_cost,
        "h_cost": h_cost,
        "f_cost": g_cost + h_cost,
    }


def calculate_f_cost(state):
    """
    Update f(n) = g(n) + h(n)
    """

    state["f_cost"] = state["g_cost"] + state["h_cost"]

    return state["f_cost"]


def state_signature(state):
    """
    Generate immutable unique signature for duplicate detection.

    Used inside visited set.
    """

    inventory_signature = tuple(
        sorted(
            (
                item["flower"],
                item["color"],
                item["quantity"]
            )
            for item in state["inventory"]
        )
    )

    needs_signature = tuple(
        sorted(
            (
                pavilion_id,
                tuple(
                    sorted(color_needs.items())
                )
            )
            for pavilion_id, color_needs
            in state["remaining_needs"].items()
        )
    )

    return (
        state["robot_x"],
        state["robot_y"],
        inventory_signature,
        needs_signature,
    )


def serialize_state(state):
    """
    Convert state into pretty printable JSON string.
    """

    return json.dumps(state, indent=4, ensure_ascii=False)


def clone_state(state):
    """
    Deep copy state safely.
    """

    return copy.deepcopy(state)


def is_goal_state(state):
    """
    Goal conditions:

    1. All pavilion needs satisfied
    2. Robot inventory empty
    """

    inventory_empty = len(state["inventory"]) == 0

    all_done = True

    for pavilion_needs in state["remaining_needs"].values():

        for quantity in pavilion_needs.values():

            if quantity > 0:
                all_done = False
                break

    return inventory_empty and all_done