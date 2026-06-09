import collections.abc
import collections
collections.Mapping = collections.abc.Mapping

from experta import Fact, Field


class Grid(Fact):
    """Describes the rectangular grid dimensions.

    Fields:
        rows (int): number of rows  (y-axis, 0 = top)
        cols (int): number of columns (x-axis, 0 = left)
    """
    rows = Field(int, mandatory=True)
    cols = Field(int, mandatory=True)


class Warehouse(Fact):
    """Location of the single warehouse on the grid.

    Fields:
        x (int): column index
        y (int): row index
        stock (list[dict]): available bouquets
            Each entry: {"flower": str, "color": str, "quantity": int}
    """
    x    = Field(int,  mandatory=True)
    y    = Field(int,  mandatory=True)
    stock = Field(list, mandatory=True)


class Robot(Fact):
    """Current robot state.

    Fields:
        x         (int):  column
        y         (int):  row
        inventory (list): loaded bouquets - same dict schema as warehouse stock
        capacity  (int):  maximum total bouquet units the robot can carry
    """
    x         = Field(int,  mandatory=True)
    y         = Field(int,  mandatory=True)
    inventory = Field(list, mandatory=True)
    capacity  = Field(int,  mandatory=True)


class Pavilion(Fact):
    """A delivery destination with a bouquet requirement.

    Fields:
        pavilion_id (str):  unique name, e.g. "P1"
        x           (int):  column
        y           (int):  row
        needs       (list): required bouquets
            Each entry: {"flower": str, "color": str, "quantity": int}
    """
    pavilion_id = Field(str,  mandatory=True)
    x           = Field(int,  mandatory=True)
    y           = Field(int,  mandatory=True)
    needs       = Field(list, mandatory=True)


class State(Fact):
    """Represents one node in the search tree.

    This fact drives the forward-chaining search: the engine fires rules
    against the *current* (lowest-f_cost) state and generates children.

    Fields:
        state_id   (str):  unique identifier
        parent_id  (str):  parent state_id  (None for root)
        action     (str):  action that produced this state
        robot_x    (int):  robot column
        robot_y    (int):  robot row
        inventory  (list): robot inventory at this state
        needs      (dict): {pavilion_id -> list of remaining need dicts}
        g_cost     (int):  cost from root
        h_cost     (float):heuristic estimate to goal
        f_cost     (float):g + h
        active     (bool): True = still in the open list
    """
    state_id  = Field(str,   mandatory=True)
    parent_id = Field(object, mandatory=True)   # str or None
    action    = Field(str,   mandatory=True)
    robot_x   = Field(int,   mandatory=True)
    robot_y   = Field(int,   mandatory=True)
    inventory = Field(list,  mandatory=True)
    needs     = Field(dict,  mandatory=True)
    g_cost    = Field(int,   mandatory=True)
    h_cost    = Field(float, mandatory=True)
    f_cost    = Field(float, mandatory=True)
    active    = Field(bool,  mandatory=True)
    capacity  = Field(int,    mandatory=False)


class Visited(Fact):
    """Tracks already-explored state hashes to avoid re-expansion.

    Fields:
        state_hash (str): hash string produced by utils/helpers.py
    """
    state_hash = Field(str, mandatory=True)


class SearchCycle(Fact):
    """Phase marker for the pure-Experta A* control loop."""
    phase = Field(str, mandatory=True)


class CurrentNode(Fact):
    """The single node being expanded right now."""
    state_id = Field(str, mandatory=True)


class NoSolution(Fact):
    """Asserted when the frontier is empty and no goal was found."""
    pass


class Goal(Fact):
    """Marks that the goal has been reached.

    Fields:
        state_id (str): the winning state
    """
    state_id = Field(str, mandatory=True)