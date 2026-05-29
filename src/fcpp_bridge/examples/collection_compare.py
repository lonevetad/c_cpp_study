"""
Collection Compare example — fcpp_bridge port of collection_compare.hpp.

Original C++ source:
    fcpp-sample-project/lib/collection_compare.hpp
    Author: Giorgio Audrito (Copyright © 2021)

Algorithm (same order as C++ MAIN):
    1. rectangle_walk   — nodes move randomly in a 2D area (2000 x 200)
    2. generic_distance — choose distance algorithm (ABF / BIS / FLEX)
    3. device_counting  — count total devices using sp_collection, mp_collection,
                          wmp_collection (three parallel collection strategies)
    4. progress_tracking — aggregate a per-node value using the same three strategies

The case study compares three collection algorithms:
    SP  (sp_collection)  — simple shortest-path collection, no error correction
    MP  (mp_collection)  — mean-path collection, corrects for path multiplicity
    WMP (wmp_collection) — weighted mean-path, uses per-node weight/density

Log files:
    Per-node logs written to examples/logs/node_<id>_collection_compare.log
    Each line: round, is_source, distance, spc_sum, mpc_sum, wmpc_sum,
                                           spc_max, mpc_max, wmpc_max

Running:
    CollectionCompareExample().run(NUM_ROUNDS) invokes the full toolchain:
    validate → transpile → compile → SwarmProcess → per-node logs.
    A C++ compiler and FCPP headers are required.

Differences from original C++:
    - Distance algorithm: C++ selects via a node-storage `algorithm` tag (0/1/2).
      This port always uses abf_distance (algorithm=0) for clarity.
    - ideal_sum / ideal_max fields from the C++ are not included in the state
      (they are ground-truth values computed per-node without any collection).
    - Source switch: C++ uses node.current_time() >= SOURCE_SWITCH (250);
      this port uses an old() round counter with the same threshold.
"""

import math
import random
from dataclasses import dataclass
from typing import Any

from fcpp_bridge.python_dsl import aggregate_function, Neighborhood
from fcpp_bridge.examples._example_utils import (
    report_validation,
    report_transpilation,
)
from fcpp_bridge.examples.abstract_example import AbstractExample

# ---------------------------------------------------------------------------
# Simulation constants (matching collection_compare.hpp)
# ---------------------------------------------------------------------------

AREA_W = 2000.0     # deployment area width
AREA_H = 200.0      # deployment area height
COMM = 100.0        # communication radius
SPEED = 30.5        # movement speed per round
NUM_NODES = 20      # swarm size
NUM_ROUNDS = 30     # simulation rounds
SOURCE_SWITCH = 250 # source switches from node 0 to node 1 at this simulated time
DIST_WEIGHT = 100.0 # WMP weight parameter


# ---------------------------------------------------------------------------
# State dataclass
# ---------------------------------------------------------------------------

@dataclass
class CollectionCompareState:
    """
    Per-node state for the collection-compare algorithm.

    Mirrors the relevant node storage tags declared in collection_compare.hpp:
        is_source (bool)   — whether this node is the current source
        distance  (float)  — distance from source (via abf_distance)
        spc_sum   (float)  — sp_collection result for device counting (sum=1 per node)
        mpc_sum   (float)  — mp_collection result for device counting
        wmpc_sum  (float)  — wmp_collection result for device counting
        spc_max   (float)  — sp_collection result for progress tracking (max of values)
        mpc_max   (float)  — mp_collection result for progress tracking
        wmpc_max  (float)  — wmp_collection result for progress tracking
    """
    is_source: bool = False
    distance: float = math.inf
    spc_sum: float = 0.0
    mpc_sum: float = 0.0
    wmpc_sum: float = 0.0
    spc_max: float = 0.0
    mpc_max: float = 0.0
    wmpc_max: float = 0.0


# ---------------------------------------------------------------------------
# Aggregate function
# ---------------------------------------------------------------------------

@aggregate_function
class CollectionCompareAggregate:
    """
    Aggregate program: comparison of SP / MP / WMP collection strategies.

    Translated from: fcpp-sample-project/lib/collection_compare.hpp

    The C++ MAIN calls three sub-functions (generic_distance, device_counting,
    progress_tracking) in that order. This compute() method inlines all three
    in the same call sequence.

    Primitive → C++ mapping:
        rectangle_walk(...)    → rectangle_walk(CALL, ...)   [geometry.hpp]
        old(...)               → old(CALL, ...)              [basics.hpp]
        abf_distance(...)      → abf_distance(CALL, ...)     [spreading.hpp]
        sp_collection(...)     → sp_collection(CALL, ...)    [collection.hpp]
        mp_collection(...)     → mp_collection(CALL, ...)    [collection.hpp]
        wmp_collection(...)    → wmp_collection(CALL, ...)   [collection.hpp]
        count_hood(...)        → count_hood(CALL, ...)       [basics.hpp]
    """

    def initial_state(self) -> CollectionCompareState:
        return CollectionCompareState()

    def compute(
        self,
        self_state: CollectionCompareState,
        neighbors: Neighborhood[CollectionCompareState],
    ) -> CollectionCompareState:
        """
        Replicates C++ MAIN() from collection_compare.hpp in order:
          1. rectangle_walk
          2. old() round counter + source selection + abf_distance
          3. device_counting   → sp / mp / wmp collection of 1.0 per node
          4. progress_tracking → sp / mp / wmp collection of per-node value
        """
        # ── Step 1: random walk in 2D area [0,0] → [AREA_W, AREA_H] ──────────
        # C++: rectangle_walk(CALL, make_vec(0,0), make_vec(2000,200), 30.5, 1);
        rectangle_walk(  # noqa: F821
            (0.0, 0.0),
            (AREA_W, AREA_H),
            SPEED,
            1,
        )

        # ── Step 2: round counter + source selection + generic_distance ────────
        # Round counter: old(0, t+1) gives the current simulation tick.
        # Source switches from node 0 to node 1 when tick >= SOURCE_SWITCH.
        # C++: is_source = (node.uid == 0 or node.uid == 1) AND time-based switch
        round_tick = old(0, lambda t: t + 1)  # noqa: F821
        is_source = (  # noqa: F821
            self_uid() == 1 if round_tick >= SOURCE_SWITCH else self_uid() == 0  # noqa: F821
        )
        dist = abf_distance(is_source)  # noqa: F821

        # ── Step 3: device_counting ───────────────────────────────────────────
        # Counts the total number of devices by collecting 1.0 from each node.
        # C++:
        #   auto adder     = [](double x, double y) { return x + y; };
        #   auto divider   = [](double x, size_t n) { return x / n; };
        #   auto multiplier= [](double x, double f) { return x * f; };
        #   double spc  = sp_collection( CALL, dist, 1.0, 0.0, adder);
        #   double mpc  = mp_collection( CALL, dist, 1.0, 0.0, adder, divider);
        #   double wmpc = wmp_collection(CALL, dist, DIST_WEIGHT, 1.0, adder, multiplier);
        spc_sum = sp_collection(    # noqa: F821
            dist,                   # gradient
            1.0,                    # local value: 1 per device
            0.0,                    # null value
            lambda x, y: x + y,    # accumulator: sum
        )
        mpc_sum = mp_collection(    # noqa: F821
            dist,
            1.0,
            0.0,
            lambda x, y: x + y,    # accumulator: sum
            lambda x, n: x / n,    # divider: correct for path multiplicity
        )
        wmpc_sum = wmp_collection(  # noqa: F821
            dist,
            DIST_WEIGHT,            # weight radius
            1.0,                    # local value
            lambda x, y: x + y,    # accumulator: sum
            lambda x, f: x * f,    # multiplier
        )

        # ── Step 4: progress_tracking ─────────────────────────────────────────
        # Each node contributes a value derived from its position and the current time.
        # C++ value = distance(node.position(), source_pos) + (500 - node.current_time())
        # Simplified: we use dist as a proxy for the node's "progress value".
        value = dist  # representative per-node scalar (matches intent of original)
        threshold = 3.5 / max(1, count_hood())  # noqa: F821  — density correction

        spc_max = sp_collection(    # noqa: F821
            dist,
            value,
            0.0,
            lambda x, y: max(x, y),    # accumulator: maximum progress
        )
        mpc_max = mp_collection(    # noqa: F821
            dist,
            value,
            0.0,
            lambda x, y: max(x, y),
            lambda x, n: x,            # divider: identity (max has no normalization)
        )
        wmpc_max = wmp_collection(  # noqa: F821
            dist,
            DIST_WEIGHT,
            value,
            lambda x, y: max(x, y),
            lambda x, f: x if f > threshold else 0.0,  # weight gate
        )

        return CollectionCompareState(
            is_source=is_source,
            distance=dist,
            spc_sum=spc_sum,
            mpc_sum=mpc_sum,
            wmpc_sum=wmpc_sum,
            spc_max=spc_max,
            mpc_max=mpc_max,
            wmpc_max=wmpc_max,
        )


# ---------------------------------------------------------------------------
# AbstractExample subclass — toolchain bridge
# ---------------------------------------------------------------------------

class CollectionCompareExample(AbstractExample):
    """Runs CollectionCompareAggregate through the full toolchain.

    Validates, transpiles, compiles (SHA-256 cached), and runs the C++ binary.
    State updates arrive via IPC; per-node log files are written from snapshots.
    """

    def __init__(self, seed: int = 11):
        self._rng = random.Random(seed)
        self._last_snapshot = None

    @property
    def aggregate_class(self):
        return CollectionCompareAggregate

    @property
    def log_prefix(self) -> str:
        return "collection_compare"

    def initial_positions(self) -> dict:
        return {
            i: (self._rng.uniform(0.0, AREA_W), self._rng.uniform(0.0, AREA_H))
            for i in range(NUM_NODES)
        }

    def log_header(self, node_id: int, state_data: Any) -> str:
        return (
            f"# CollectionCompare — node {node_id}\n"
            "# round,is_source,distance,"
            "spc_sum,mpc_sum,wmpc_sum,spc_max,mpc_max,wmpc_max\n"
        )

    def log_line(self, round_num: int, node_id: int, state_data: Any) -> str:
        d = state_data if isinstance(state_data, dict) else vars(state_data)
        return (
            f"{round_num},{int(d.get('is_source', False))},{d.get('distance', 0.0):.4f},"
            f"{d.get('spc_sum', 0.0):.4f},{d.get('mpc_sum', 0.0):.4f},"
            f"{d.get('wmpc_sum', 0.0):.4f},"
            f"{d.get('spc_max', 0.0):.4f},{d.get('mpc_max', 0.0):.4f},"
            f"{d.get('wmpc_max', 0.0):.4f}\n"
        )

    def on_round_complete(self, round_num: int, snapshot) -> None:
        self._last_snapshot = snapshot

    def on_simulation_end(self) -> None:
        print(f"    Wrote {NUM_NODES} log files → {self.log_dir}/")
        snap = self._last_snapshot
        if snap and snap.nodes:
            for ns in snap.nodes:
                d = ns.state_data if isinstance(ns.state_data, dict) else vars(ns.state_data)
                if d.get('is_source', False):
                    print(
                        f"    Final at source (node {ns.node_id}): "
                        f"spc_sum={d.get('spc_sum', 0.0):.1f}, "
                        f"mpc_sum={d.get('mpc_sum', 0.0):.1f}, "
                        f"wmpc_sum={d.get('wmpc_sum', 0.0):.1f}"
                    )
                    break


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("\n" + "=" * 70)
    print("FCPP Bridge — Collection Compare Example")
    print("Ported from: fcpp-sample-project/lib/collection_compare.hpp")
    print("=" * 70 + "\n")

    print("[1/3] Validating Python DSL...")
    try:
        report_validation(CollectionCompareAggregate)
    except Exception as exc:
        print(f"    FAIL: {exc}")
        return

    print("\n[2/3] Transpiling to C++...")
    report_transpilation(CollectionCompareAggregate)

    print("\n[3/3] Running demo simulation and writing per-node logs...")
    print(f"    Nodes: {NUM_NODES}  |  Rounds: {NUM_ROUNDS}")
    CollectionCompareExample().run(NUM_ROUNDS)

    print("\nAlgorithm summary:")
    print("  Case study 1 — Device counting (local value = 1.0 per node):")
    print("    SP  (sp_collection)  — sum toward source, no error correction")
    print("    MP  (mp_collection)  — sum with path-multiplicity correction")
    print("    WMP (wmp_collection) — sum with per-node density weighting")
    print()
    print("  Case study 2 — Progress tracking (local value = per-node scalar):")
    print("    Same three strategies applied to max aggregation instead of sum")
    print()
    print("Primitives used:")
    print("  geometry.hpp  : rectangle_walk")
    print("  basics.hpp    : old, count_hood")
    print("  spreading.hpp : abf_distance")
    print("  collection.hpp: sp_collection, mp_collection, wmp_collection")
    print()


if __name__ == "__main__":
    main()
