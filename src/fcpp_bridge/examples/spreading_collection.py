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
from pathlib import Path

from fcpp_bridge.python_dsl import aggregate_function, Neighborhood
from examples._example_utils import report_validation, report_transpilation

# ---------------------------------------------------------------------------
# Simulation constants (matching spreading_collection.hpp)
# ---------------------------------------------------------------------------

SIDE = 200.0        # deployment area side length (units)
HEIGHT = 100.0      # deployment area height (units)
COMM = 100.0        # communication radius (units)
SPEED = 10.0        # node movement speed (units/round)
NUM_NODES = 15      # swarm size
NUM_ROUNDS = 30     # simulation rounds
SOURCE_ID = 0       # fixed source node (original C++ rotates every 50 seconds)

LOG_DIR = Path(__file__).parent / "logs"


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
# Demo simulation — pure Python approximation for log generation
# ---------------------------------------------------------------------------

def _demo_simulate() -> None:
    """
    Pure-Python approximation of the spreading-collection algorithm.

    Implements the same 5 steps as compute() using Python logic so that
    per-node log files can be produced without a C++ compiler.
    The topology is a random spatial deployment with fixed-radius connectivity.
    """
    random.seed(42)

    # Initial positions (x, y) in [0, SIDE]
    positions = {
        i: (random.uniform(0.0, SIDE), random.uniform(0.0, SIDE))
        for i in range(NUM_NODES)
    }

    # Initial states: node SOURCE_ID is the source
    states = {
        i: SpreadingState(is_source=(i == SOURCE_ID))
        for i in range(NUM_NODES)
    }

    def neighbors_of(nid):
        """Return IDs of nodes within COMM radius (excluding self)."""
        x, y = positions[nid]
        return [
            j for j in range(NUM_NODES)
            if j != nid
            and math.dist((x, y), positions[j]) <= COMM
        ]

    LOG_DIR.mkdir(exist_ok=True)
    log_files = {}

    for round_num in range(NUM_ROUNDS):
        new_states = {}

        for nid in range(NUM_NODES):
            s = states[nid]
            nbrs = neighbors_of(nid)
            nbr_s = [states[n] for n in nbrs]

            # ── Step 1: rectangle_walk (move node) ────────────────────────
            x, y = positions[nid]
            dx = random.uniform(-SPEED, SPEED)
            dy = random.uniform(-SPEED, SPEED)
            positions[nid] = (
                max(0.0, min(SIDE, x + dx)),
                max(0.0, min(SIDE, y + dy)),
            )

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
                # Source accumulates max of all finite distances from "children"
                # (nodes with dist > 0, i.e. further from source)
                child_vals = [
                    ns.calc_distance for ns in nbr_s
                    if math.isfinite(ns.calc_distance)
                ]
                sdiam = max(child_vals, default=0.0)
            else:
                # Non-source nodes propagate upstream what the parent reports
                parents = [ns for ns in nbr_s if ns.calc_distance < dist]
                sdiam = max((ns.source_diameter for ns in parents), default=0.0)

            # ── Step 5: broadcast (diameter from source to all) ───────────
            if is_source:
                diam = sdiam
            else:
                parents = [(ns.calc_distance, ns.diameter) for ns in nbr_s
                           if ns.calc_distance < dist]
                if parents:
                    # take the diameter from the closest node toward the source
                    diam = min(parents, key=lambda t: t[0])[1]
                else:
                    diam = s.diameter   # retain last known

            new_states[nid] = SpreadingState(
                is_source=is_source,
                calc_distance=dist,
                source_diameter=sdiam,
                diameter=diam,
            )

            # ── Write log entry ───────────────────────────────────────────
            if nid not in log_files:
                log_path = LOG_DIR / f"node_{nid}_spreading_collection.log"
                lf = open(log_path, "w")
                lf.write(
                    f"# SpreadingCollection — node {nid}\n"
                    "# round,is_source,calc_distance,source_diameter,diameter\n"
                )
                log_files[nid] = lf
            log_files[nid].write(
                f"{round_num},{int(is_source)},"
                f"{dist:.4f},{sdiam:.4f},{diam:.4f}\n"
            )

        states = new_states

    for lf in log_files.values():
        lf.close()

    print(f"    Wrote {NUM_NODES} log files → {LOG_DIR}/")


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

    # ── Phase 3: Demo simulation + log files ─────────────────────────────
    print("\n[3/3] Running demo simulation and writing per-node logs...")
    print(f"    Nodes: {NUM_NODES}  |  Rounds: {NUM_ROUNDS}  |  Source: node {SOURCE_ID}")
    _demo_simulate()

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
