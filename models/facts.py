import collections.abc
import collections
collections.Mapping = collections.abc.Mapping

from experta import Fact


class Grid(Fact):
    """
    Grid dimensions.

    Example:
        Grid(width=6, height=6)
    """
    pass


class Warehouse(Fact):
    """
    Warehouse position.

    Example:
        Warehouse(x=2, y=3)
    """
    pass


class Robot(Fact):
    """
    Robot current information.

    Fields:
        x, y           -> current position
        inventory      -> carried bouquets
        load           -> current number of bouquets
        max_load       -> maximum capacity
    """
    pass


class Pavilion(Fact):
    """
    Pavilion information.

    Fields:
        pavilion_id
        flower_type
        x, y
        needs

    Example:
        needs = {
            "Red": 2,
            "White": 1
        }
    """
    pass


class State(Fact):
    """
    Represents one node in the search tree.

    Fields:
        state_id
        parent_id
        action

        robot_x
        robot_y

        inventory

        remaining_needs

        g_cost
        h_cost
        f_cost
    """
    pass


class Visited(Fact):
    """
    Used to avoid duplicate states.
    """
    pass


class Goal(Fact):
    """
    Marks that goal state was reached.
    """
    pass