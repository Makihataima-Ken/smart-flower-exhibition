# Smart Flower Exhibition — Knowledge-Based System

A rule-based expert system implemented with **Python + Experta** that plans
optimal flower bouquet deliveries for an autonomous robot on a 2D grid.

---

## Table of Contents
1. [Problem Description](#problem-description)
2. [System Architecture](#system-architecture)
3. [How It Works](#how-it-works)
4. [Search Algorithm](#search-algorithm)
5. [Loading Constraints](#loading-constraints)
6. [Heuristic Function](#heuristic-function)
7. [Project Structure](#project-structure)
8. [Running the System](#running-the-system)
9. [Sample Scenario](#sample-scenario)
10. [Academic Discussion](#academic-discussion)

---

## Problem Description

A robot operates on a rectangular 2D grid containing:

- **One warehouse** — source of all flower bouquets
- **Multiple pavilions** — destinations that each require specific flower bouquets
- **One robot** — starts empty, loads from the warehouse, delivers to pavilions

**Objective:** satisfy every pavilion's bouquet requirement with minimum total cost (moves + loads + unloads), ending with an empty robot inventory.

**Action costs:** every action (move, load, unload) costs **1** unit.

---

## System Architecture

```
smart-flower-exhibition/
│
├── main.py                      # Entry point
├── engine/
|   ├── rules/
│   │   ├── rules_movement.py        # Robot movement rule
|   │   ├── rules_loading.py         # Warehouse loading rule
|   │   ├── rules_unloading.py       # Pavilion unloading rule
|   │   ├── rules_constraints.py     # Validation / pruning rules
|   │   └── rules_goal.py            # Goal detection rule
│   ├── knowledge_engine.py      # Engine factory + A* search loop
│   └── heuristic.py             # A* heuristic h(n)
│
├── models/
│   ├── facts.py                 # Experta Fact classes
│   ├── state.py                 # StateNode dataclass + global registry
│   └── enums.py                 # Flower types and valid colors
│
├── utils/
│   ├── helpers.py               # Pure validation + hashing functions
│   ├── printer.py               # Output formatting
│   └── search_tree.py           # Open list (min-heap) + closed set
│
└── data/
    └── sample_case.py           # Concrete scenario definition
```

### Design Principles

| Principle | Implementation |
|-----------|----------------|
| Separation of concerns | Rules split into 5 separate files by concern |
| Thin rules | Heavy logic lives in `helpers.py`; rules delegate to helpers |
| Immutable state | Each action creates a NEW State fact; old states are never mutated |
| Duplicate detection | State hashing in `helpers.state_hash()` + closed set |
| Modular engine | Rule classes built as mixins, composed via Python multiple inheritance |

---

## How It Works

### Experta Forward-Chaining

Experta is a Python port of the CLIPS expert system shell. It stores
**facts** in a *Working Memory* and continuously applies **rules** whose
**left-hand sides** (LHS) match those facts. When all LHS conditions are
satisfied, the rule **fires**, executing its **right-hand side** (RHS) body.

In this system:
- **Facts** represent the current state of the world (robot position, inventory,
  pavilion needs, grid dimensions).
- **Rules** expand the current search state by generating successor states for
  every valid action.

### State Expansion Flow

```
Main Loop
│
├── Pop state with lowest f_cost from open heap
├── Mark as active (active=True) in working memory
├── engine.run()  ← Experta fires all matching rules in salience order:
│   │
│   ├── detect_goal       (salience 200) — halt if goal reached
│   ├── Constraint rules  (salience 100) — retract illegal states
│   ├── expand_unloads    (salience  30) — generate unload children
│   ├── expand_loads      (salience  20) — generate load children
│   └── expand_movements  (salience  10) — generate move children + deactivate
│
└── Repeat until goal found or open list empty
```

**Key design choice:** Loading and unloading rules do NOT deactivate the
current state. Only the movement rule (lowest salience) deactivates it after
all other rules have had their chance. This ensures a state at the warehouse
simultaneously generates *both* loading children and movement children.

---

## Search Algorithm

### A* Search

The system implements **A\*** (A-star) search:

```
f(n) = g(n) + h(n)
```

| Term | Meaning |
|------|---------|
| `g(n)` | Actual cost from root to node `n` (number of actions taken) |
| `h(n)` | Heuristic estimate of cost from `n` to goal |
| `f(n)` | Total estimated cost through `n` |

The **open list** is a min-heap (priority queue) sorted by `f(n)`.
The **closed set** stores hashed state signatures to avoid re-expanding
already-visited states.

Experta's **salience** ordering simulates A\* *within* a single expansion:
higher-salience rules (goal detection, constraints) fire before lower-salience
generation rules, preventing wasted work on invalid or terminal states.

### State Hash

Two states are considered identical if they share:
- Robot position `(x, y)`
- Inventory contents (flower, color, quantity)
- Remaining pavilion needs (per pavilion)

The hash is computed with `json.dumps` on a canonically sorted representation.

---

## Loading Constraints

The robot's inventory must satisfy ONE of two loading modes at all times:

### Mode A — Different flower types, same color
```
Rose      Red  ×1
Tulip     Red  ×2
Orchid    Red  ×1
```
All items share the color "Red"; flower types differ.

### Mode B — Same flower type, different colors
```
Rose  Red    ×2
Rose  White  ×1
Rose  Pink   ×1
```
All items are "Rose"; colors differ.

**Invalid** combinations mix both different flower types and different colors.

The `can_load()` helper in `utils/helpers.py` enforces these rules before any
loading action is added to a child state.

### Robot Capacity

The maximum robot capacity is set to:
```
capacity = max(total demand of pavilion P1, total demand of pavilion P2, ...)
```
This guarantees the robot can always carry enough flowers to serve any single
pavilion in one trip (if the loading mode is compatible).

---

## Heuristic Function

```python
h(n) = remaining_units + distance_to_nearest_needy_pavilion
```

Where:
- `remaining_units` = sum of all bouquet quantities still needed by all pavilions
- `distance_to_nearest_needy_pavilion` = Manhattan distance from robot to the
  closest pavilion that still has unsatisfied needs

### Admissibility Proof

A heuristic `h` is **admissible** if it never overestimates the true cost.

- Every remaining bouquet unit requires at least 1 unload action → `remaining_units` ≤ actual unload cost ✓
- The robot must travel at least `distance_to_nearest_needy_pavilion` steps → Manhattan distance ≤ actual travel ✓
- Sum of two lower bounds is still a lower bound → `h(n)` is admissible ✓

Because `h` is admissible, A* with this heuristic is guaranteed to find the
**optimal** solution path.

---

## Flower Types and Colors

| Type | Valid Colors |
|------|-------------|
| Rose | Red, Pink, White, Yellow, Burgundy |
| Tulip | Red, Yellow, Purple, Orange, Green, Mauve, Violet |
| Orchid | Purple, White, Pink, Rosy |
| Rose Goliat | Gold, Light Pink, Yellow |

---

## Project Structure Details

### `models/facts.py`
Defines all Experta `Fact` subclasses:
- `Grid` — grid dimensions
- `Warehouse` — location and stock
- `Robot` — current position and inventory
- `Pavilion` — location and requirements
- `State` — search tree node (the main unit of search)
- `Goal` — signals the goal state was reached
- `Visited` — duplicate tracking

### `models/state.py`
- `StateNode` — a plain Python dataclass mirroring `State`
- `STATE_REGISTRY` — global dict of all generated states (for path reconstruction)
- `clone_inventory()` / `clone_needs()` — safe deep-copy that unwraps Experta's
  internal `frozenlist`/`frozendict` types

### `utils/helpers.py`
Pure functions with no Experta dependency:
- `can_load()` — validates loading mode constraints
- `can_unload()` — validates unloading against pavilion needs
- `state_hash()` — deterministic string hash for duplicate detection
- `is_goal()` — checks if all needs are met and inventory is empty
- `manhattan_distance()` — used by the heuristic

### `engine/knowledge_engine.py`
- `build_engine()` — creates the composed `KnowledgeEngine` via multiple inheritance
- `run_search()` — initialises the search, declares world facts, runs the A* loop

---

## Running the System

### Prerequisites

```bash
pip install experta
```

> **Note for Python 3.10+:** If you see `AttributeError: module 'collections' has no attribute 'Mapping'`,
> apply the following one-line patch:
> ```bash
> python -c "
> import frozendict, re, pathlib
> p = pathlib.Path(frozendict.__file__)
> p.write_text(re.sub(r'import collections\b', 'import collections\nimport collections.abc', p.read_text()))
> "
> ```

### Run

```bash
python main.py
```

### Expected Output

1. Scenario summary
2. ASCII grid layout
3. Per-iteration expansion log
4. **GOAL REACHED** message when the goal is found
5. Final grid layout
6. Step-by-step **solution path**
7. Full **search tree** table

---

## Sample Scenario

```
Grid: 5×5

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

W  = Warehouse at (0,0)
R  = Robot starts at (2,2)   [empty inventory]
P1 = Pavilion 1 at (4,3)    needs: Rose Red×2, Rose White×1
P2 = Pavilion 2 at (1,4)    needs: Tulip Red×2
```

**Robot capacity:** 3 (= max pavilion demand)

**Optimal strategy:**
1. Move to warehouse (W)
2. Load Tulip Red×2 → deliver to P2
3. Return to warehouse
4. Load Rose Red×2 + Rose White×1 (Mode B: same flower, different colors)
5. Deliver to P1
6. Return empty → goal ✓

---

## Academic Discussion

### Why Experta for Search?

Traditional search algorithms (BFS, Dijkstra, A*) are implemented as imperative
loops over a graph. Experta re-frames the problem as **rule-based inference**:

- The search *state* is a fact in working memory
- Each *action* is encoded as a rule that generates successor state facts
- The *evaluation order* (A* priority) is controlled by salience
- *Constraint enforcement* is declarative — illegal states are retracted by rules

This approach separates the **what** (rules) from the **how** (engine), making
the knowledge base modular and inspectable.

### Challenges of Rule-Based Search

1. **State isolation:** Experta shares working memory across all states.
   We solve this by making each State fact immutable and generating new facts
   for every successor.

2. **Open list management:** Experta has no built-in priority queue. We
   implement A\* externally (in `utils/search_tree.py`) and use `active=True`
   to selectively trigger rule expansion for one state at a time.

3. **frozendict/frozenlist:** Experta freezes all fact field values for safety.
   Our `clone_inventory()` and `clone_needs()` explicitly convert these back to
   mutable Python objects before manipulation.

### Complexity

- **State space:** O(G × I × N) where G = grid cells, I = inventory combinations,
  N = need configurations
- **Time:** A* explores O(b^d) states where b = branching factor, d = solution depth
- **Admissible heuristic → optimal:** The chosen h(n) never overestimates,
  so A* is guaranteed to find the shortest-cost solution

---
