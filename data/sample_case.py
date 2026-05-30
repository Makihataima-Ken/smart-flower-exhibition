"""
data/sample_case.py
-------------------
Defines one concrete scenario used to demonstrate and test the system.

SCENARIO DESCRIPTION
====================

Grid:  5 columns × 5 rows  (indices 0–4)

    0   1   2   3   4
  +---+---+---+---+---+
0 | W |   |   |   |   |
  +---+---+---+---+---+
1 |   |   |   |   |   |
  +---+---+---+---+---+
2 |   |   | R |   |   |
  +---+---+---+---+---+
3 |   |   |   |   | P1|
  +---+---+---+---+---+
4 |   | P2|   |   |   |
  +---+---+---+---+---+

  W  = Warehouse at (0, 0)
  R  = Robot starts at (2, 2)
  P1 = Pavilion 1 at (4, 3)
  P2 = Pavilion 2 at (1, 4)

WAREHOUSE STOCK
===============
  - Rose Red      ×3
  - Rose White    ×2
  - Tulip Red     ×2
  - Orchid Purple ×1

PAVILION NEEDS
==============
  P1 needs:
    - Rose Red  ×2   (MODE B compatible with Rose White)
    - Rose White×1

  P2 needs:
    - Tulip Red ×2

LOADING ANALYSIS
================
  For P1: Rose Red + Rose White → same flower (Rose), different colors → MODE B ✓
  For P2: Tulip Red alone → MODE B trivially ✓
  Full trip attempt (P1 items first):
    Rose Red ×2 + Rose White ×1  → MODE B (all Rose) → capacity = 3 → OK
    Cannot add Tulip Red (different flower, different color from White/Red mix) → second trip

MAX CAPACITY
============
  P1 total demand = 3  (Rose Red ×2 + Rose White ×1)
  P2 total demand = 2  (Tulip Red ×2)
  max(3, 2) = 3  → robot capacity = 3
"""

# ---------------------------------------------------------------------------
# Grid
# ---------------------------------------------------------------------------
GRID = {
    "rows": 5,
    "cols": 5,
}

# ---------------------------------------------------------------------------
# Warehouse
# ---------------------------------------------------------------------------
WAREHOUSE = {
    "x": 0,
    "y": 0,
    "stock": [
        {"flower": "Rose",   "color": "Red",    "quantity": 3},
        {"flower": "Rose",   "color": "White",  "quantity": 2},
        {"flower": "Tulip",  "color": "Red",    "quantity": 2},
        {"flower": "Orchid", "color": "Purple", "quantity": 1},
    ],
}

# ---------------------------------------------------------------------------
# Pavilions
# ---------------------------------------------------------------------------
PAVILIONS = [
    {
        "pavilion_id": "P1",
        "x": 4,
        "y": 3,
        "needs": [
            {"flower": "Rose", "color": "Red",   "quantity": 2},
            {"flower": "Rose", "color": "White",  "quantity": 1},
        ],
    },
    {
        "pavilion_id": "P2",
        "x": 1,
        "y": 4,
        "needs": [
            {"flower": "Tulip", "color": "Red", "quantity": 2},
        ],
    },
]

# ---------------------------------------------------------------------------
# Robot start position (starts with empty inventory)
# ---------------------------------------------------------------------------
ROBOT_START = {
    "x": 2,
    "y": 2,
}

# ---------------------------------------------------------------------------
# Derived: robot capacity = max pavilion total demand
# ---------------------------------------------------------------------------
def compute_capacity(pavilions):
    """Compute the robot capacity from the scenario pavilion list."""
    return max(
        sum(b["quantity"] for b in p["needs"])
        for p in pavilions
    )

ROBOT_CAPACITY = compute_capacity(PAVILIONS)   # → 3
