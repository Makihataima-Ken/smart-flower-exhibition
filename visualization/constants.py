"""Visualization constants for Smart Flower Exhibition.

Defines layout, timing and color constants used by the renderer
and animator.
"""
from typing import Tuple

# Grid cell size in pixels
CELL_SIZE: int = 64

# Frames per second for the pygame loop
FPS: int = 60

# Duration of each replay step in milliseconds
STEP_DURATION: int = 1000

# Extra padding around the grid to leave room for panels
WINDOW_PADDING: int = 200

# Colors (R, G, B)
WHITE: Tuple[int, int, int] = (255, 255, 255)
BLACK: Tuple[int, int, int] = (0, 0, 0)
GRAY: Tuple[int, int, int] = (200, 200, 200)
BLUE: Tuple[int, int, int] = (66, 133, 244)
GREEN: Tuple[int, int, int] = (34, 139, 34)
ORANGE: Tuple[int, int, int] = (255, 165, 0)
RED: Tuple[int, int, int] = (220, 20, 60)
YELLOW: Tuple[int, int, int] = (255, 215, 0)
