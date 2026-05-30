"""
models/enums.py
---------------
Defines all valid flower types and their associated colors.

Using plain string constants (not Python Enum class) keeps the code
beginner-friendly and easy to inspect during an oral discussion.
All validation in the system compares against these sets.
"""

# ---------------------------------------------------------------------------
# Flower types
# ---------------------------------------------------------------------------
FLOWER_TYPES = ["Rose", "Tulip", "Orchid", "Rose Goliat"]

# ---------------------------------------------------------------------------
# Valid colors per flower type
# ---------------------------------------------------------------------------
FLOWER_COLORS = {
    "Rose":       ["Red", "Pink", "White", "Yellow", "Burgundy"],
    "Tulip":      ["Red", "Yellow", "Purple", "Orange", "Green", "Mauve", "Violet"],
    "Orchid":     ["Purple", "White", "Pink", "Rosy"],
    "Rose Goliat":["Gold", "Light Pink", "Yellow"],
}

# ---------------------------------------------------------------------------
# Helper: collect ALL colors that appear in any flower type
# (used by the loading-mode validator)
# ---------------------------------------------------------------------------
ALL_COLORS = sorted({
    color
    for colors in FLOWER_COLORS.values()
    for color in colors
})


def is_valid_flower(flower: str, color: str) -> bool:
    """Return True if (flower, color) is a known combination."""
    return flower in FLOWER_COLORS and color in FLOWER_COLORS[flower]
