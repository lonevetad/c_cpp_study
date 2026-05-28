"""
Spreading + Collection example — fcpp_bridge port of spreading_collection.hpp.

Original C++ source:
    fcpp-sample-project/lib/spreading_collection.hpp
    Author: Giorgio Audrito (Copyright © 2023)

Algorithm (same order as C++ MAIN):
    1. rectangle_walk  — nodes move randomly within the 3D deployment area
    2. select_source   — one node is the source (rotates in C++; static here)
    3. abf_distance    — Adaptive Bellman-Ford distance from the source
    4. mp_collection   — collect the network diameter back toward the source
    5. broadcast       — disseminate the diameter from source to the whole network

Log files:
    Per-node logs written to examples/logs/node_<id>_spreading_collection.log
    Each line: round, is_source, calc_distance, source_diameter, diameter

Differences from original C++:
    - Source selection: original rotates the source ID every 50 simulated seconds
      (using node.current_time()); this port uses a static source (node 0).
    - Demo simulation: runs a pure-Python approximation of the algorithm since the
      full C++ compilation pipeline requires FCPP headers and a C++ toolchain.
"""

import math
import random
from dataclasses import dataclass

from fcpp_bridge.python_dsl import aggregate_function, Neighborhood
from fcpp_bridge.examples._example_utils import (
    neighbors_of,
    report_validation,
    report_transpilation,
)
from fcpp_bridge.examples.abstract_example import AbstractExample

# ---------------------------------------------------------------------------
# Simulation constants (matching spreading_collection.hpp)
# ---------------------------------------------------------------------------

SIDE = 200.0        # deployment area side length (units)
HEIGHT = 100.0      # deployment area height (units)
COMM = 100.0        # communication radius (units)
SPEED = 10.0        # node movement speed (units/round)
NUM_NODES = 15      # initial swarm size (nodes can join/leave dynamically)
NUM_ROUNDS = 30     # simulation rounds
SOURCE_ID = 0       # fixed source node (original C++ rotates every 50 seconds)


# ---------------------------------------------------------------------------
# State dataclass — mirrors relevant node storage fields
# ---------------------------------------------------------------------------

@dataclass
class SpreadingState:
    """
    Per-node state for the spreading-collection algorithm.

    Fields mirror the node storage tags declared in spreading_collection.hpp:
        is_source       (bool)   — whether this node is the current source
        calc_distance   (float)  — abf_distance from the source
        source_diameter (float)  — diameter collected at the source via mp_collection
        diameter        (float)  — diameter broadcast to all nodes via broadcast
    """
    is_source: bool = False
    calc_distance: float = math.inf
    source_diameter: float = 0.0
    diameter: float = 0.0


# ---------------------------------------------------------------------------
# Aggregate function — Python DSL definition (transpiles to C++)
# ---------------------------------------------------------------------------

@aggregate_function
class SpreadingCollectionAggregate:
    """
    Aggregate program: distance spreading + collection + broadcast.

    Translated from: fcpp-sample-project/lib/spreading_collection.hpp

    The compute() method below calls FCPP primitives in exactly the same order
    as the original C++ MAIN() function. The fcpp_bridge transpiler converts
    each snake_case primitive call to its C++ counterpart, automatically
    prepending the CALL macro.

    Primitive → C++ mapping:
        rectangle_walk(...)          → rectangle_walk(CALL, ...)   [geometry.hpp]
        abf_distance(...)            → abf_distance(CALL, ...)     [spreading.hpp]
        mp_collection(...)           → mp_collection(CALL, ...)    [collection.hpp]
        broadcast(...)               → broadcast(CALL, ...)        [spreading.hpp]
    """

    def initial_state(self) -> SpreadingState:
        """Each node starts with unknown distance and no diameter information."""
        return SpreadingState()

    def compute(
        self,
        self_state: SpreadingState,
        neighbors: Neighborhood[SpreadingState],
    ) -> SpreadingState:
        """
        Replicates the C++ MAIN() body from spreading_collection.hpp, step by step.

        NOTE: The primitive names below (rectangle_walk, abf_distance, etc.) are
        unbound in Python — they are FCPP DSL calls recognized by the transpiler's
        PythonAstVisitor.visit_Call(). They map 1-to-1 to FCPP C++ function names.
        """
        # ── Step 1: random walk inside the 3D box [0,0,0] → [SIDE,SIDE,HEIGHT] ──
        # C++: rectangle_walk(CALL, make_vec(0,0,0), make_vec(side,side,height), speed, 1);
        rectangle_walk(  # noqa: F821
            (0.0, 0.0, 0.0),
            (SIDE, SIDE, HEIGHT),
            SPEED,
            1,            # movement period
        )

        # ── Step 2: source selection ──────────────────────────────────────────
        # C++ select_source(CALL, 50) checks node.current_time(); we use the state flag.
        is_source = self_state.is_source

        # ── Step 3: Adaptive Bellman-Ford distance from the source ────────────
        # C++: double dist = abf_distance(CALL, is_source);
        dist = abf_distance(is_source)  # noqa: F821

        # ── Step 4: collect the network diameter back toward the source ───────
        # C++: double sdiam = mp_collection(CALL, dist, dist, 0.0,
        #          [](double x, double y){ return max(x, y); },
        #          [](double x, int)     { return x; });
        # Accumulator: take the maximum distance; divider: no normalization.
        sdiam = mp_collection(          # noqa: F821
            dist,                       # gradient (routing field)
            dist,                       # local value to aggregate (own distance)
            0.0,                        # null/identity value for max
            lambda x, y: max(x, y),     # accumulator
            lambda x, n: x,             # divider (identity — no averaging)
        )

        # ── Step 5: broadcast the diameter from source to the whole network ───
        # C++: double diam = broadcast(CALL, dist, sdiam);
        diam = broadcast(dist, sdiam)   # noqa: F821

        return SpreadingState(
            is_source=is_source,
            calc_distance=dist,
            source_diameter=sdiam,
            diameter=diam,
        )


# ---------------------------------------------------------------------------
# Demo simulation — AbstractExample subclass
# ---------------------------------------------------------------------------

class SpreadingCollectionExample(AbstractExample):
    """Pure-Python approximation of the spreading-collection algorithm.

    Implements the same 5 steps as compute() using Python logic so that
    per-node log files can be produced without a C++ compiler.
    The topology is a random spatial deployment with fixed-radius connectivity.

    Nodes are stored as dict[int, SpreadingState]; the initial set is
    range(NUM_NODES) but nodes may join or leave between rounds.
    """

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)

    @property
    def log_prefix(self) -> str:
        return "spreading_collection"

    def initial_positions(self) -> dict:
        return {
            i: (self._rng.uniform(0.0, SIDE), self._rng.uniform(0.0, SIDE))
            for i in range(NUM_NODES)
        }

    def initial_states(self, positions: dict) -> dict:
        return {
            nid: SpreadingState(is_source=(nid == SOURCE_ID))
            for nid in positions
        }

    def round_step(self, round_num: int, positions: dict, states: dict) -> tuple:
        new_positions = {}
        new_states = {}

        for nid, (x, y) in positions.items():
            # ── Step 1: rectangle_walk (move node) ───────────────────────
            new_positions[nid] = (
                max(0.0, min(SIDE, x + self._rng.uniform(-SPEED, SPEED))),
                max(0.0, min(SIDE, y + self._rng.uniform(-SPEED, SPEED))),
            )

        for nid in positions:
            s = states[nid]
            nbr_s = [states[n] for n in neighbors_of(positions, nid, COMM)]

            # ── Step 2: is_source ─────────────────────────────────────────
            is_source = s.is_source

            # ── Step 3: abf_distance ──────────────────────────────────────
            if is_source:
                dist = 0.0
            elif nbr_s:
                dist = min(ns.calc_distance for ns in nbr_s) + COMM * 0.05
            else:
                dist = math.inf

            # ── Step 4: mp_collection (max distance toward source) ────────
            if is_source:
                child_vals = [
                    ns.calc_distance for ns in nbr_s
                    if math.isfinite(ns.calc_distance)
                ]
                sdiam = max(child_vals, default=0.0)
            else:
                parents = [ns for ns in nbr_s if ns.calc_distance < dist]
                sdiam = max((ns.source_diameter for ns in parents), default=0.0)

            # ── Step 5: broadcast (diameter from source to all) ───────────
            if is_source:
                diam = sdiam
            else:
                parent_pairs = [(ns.calc_distance, ns.diameter) for ns in nbr_s
                                if ns.calc_distance < dist]
                if parent_pairs:
                    diam = min(parent_pairs, key=lambda t: t[0])[1]
                else:
                    diam = s.diameter   # retain last known

            new_states[nid] = SpreadingState(
                is_source=is_source,
                calc_distance=dist,
                source_diameter=sdiam,
                diameter=diam,
            )

        return new_positions, new_states

    def log_header(self, node_id: int, state) -> str:
        return (
            f"# SpreadingCollection — node {node_id}\n"
            "# round,is_source,calc_distance,source_diameter,diameter\n"
        )

    def log_line(self, round_num: int, node_id: int, state) -> str:
        return (
            f"{round_num},{int(state.is_source)},"
            f"{state.calc_distance:.4f},{state.source_diameter:.4f},"
            f"{state.diameter:.4f}\n"
        )

    def on_simulation_end(self) -> None:
        print(f"    Wrote {NUM_NODES} log files → {self.log_dir}/")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("\n" + "=" * 70)
    print("FCPP Bridge — Spreading Collection Example")
    print("Ported from: fcpp-sample-project/lib/spreading_collection.hpp")
    print("=" * 70 + "\n")

    print("[1/3] Validating Python DSL...")
    try:
        report_validation(SpreadingCollectionAggregate)
    except Exception as exc:
        print(f"    FAIL: {exc}")
        return

    print("\n[2/3] Transpiling to C++...")
    report_transpilation(SpreadingCollectionAggregate)

    print("\n[3/3] Running demo simulation and writing per-node logs...")
    print(f"    Nodes: {NUM_NODES}  |  Rounds: {NUM_ROUNDS}  |  Source: node {SOURCE_ID}")
    SpreadingCollectionExample().run(NUM_ROUNDS)

    print("\nAlgorithm summary:")
    print("  1. rectangle_walk  — random 3D movement in deployment area")
    print("  2. abf_distance    — Bellman-Ford gradient from source node")
    print("  3. mp_collection   — network diameter collected at source")
    print("  4. broadcast       — diameter propagated from source to all nodes")
    print()
    print("Primitives used:")
    print("  geometry.hpp  : rectangle_walk")
    print("  spreading.hpp : abf_distance, broadcast")
    print("  collection.hpp: mp_collection")
    print()


if __name__ == "__main__":
    main()
