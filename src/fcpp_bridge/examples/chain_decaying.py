"""
Chain Decaying example — fcpp_bridge port of chain_decaying.hpp.

Original C++ source:
    fcpp-sample-project/run/chain_decaying.hpp
    (identical copy in fcpp-exercises/run/chain_decaying.hpp)
    Author: Giorgio Audrito

Algorithm (same order as C++ MAIN):
    1. is_source = (node_uid % 17 == 0)      — mark chain extremity nodes
    2. nbr + min_hood                        — propagate decaying-chain state
    3. in_channel = (data.ttl > error_ttl)   — derive liveness from TTL

The core function is_alive_decaying maintains a TTL-based decaying chain:
    - Chain extremity nodes ("sources") continuously refresh the chain with TTL=0.
    - Interior nodes propagate the freshest (lowest) TTL they receive.
    - When a node can no longer receive a fresh value from an extremity, its TTL
      increments each round by the distance metric (1 hop per round here).
    - A node "decays out" (leaves the chain) when TTL >= threshold (10 here).

The 4-tuple state per node:  (should_hold: bool, hops: int, ttl: int, next_uid: int)
    should_hold — True if this node should NOT suppress TTL increments
    hops        — hop distance from the nearest extremity
    ttl         — time-to-live counter; error_ttl=-1 means invalid/error
    next_uid    — UID of the neighbor closest to the nearest extremity

Log files:
    Per-node logs written to examples/logs/node_<id>_chain_decaying.log
    Each line: round, is_source, in_channel, should_hold, hops, ttl, next_uid

Differences from original C++:
    - is_source: C++ uses node.uid (node API); Python port carries is_source in
      state, initialized with (uid % 17 == 0) before the simulation starts.
    - Deployment: C++ runner configures SIDE, COMM, SPEED externally;
      this port defines them as module constants (see below).
    - Python DSL compute(): nbr is called with a simplified lambda showing
      min_hood; the full update logic (am_I_closest, has_to_increment, decay
      check) is faithfully implemented in _demo_simulate().
    - was_on_chain is always True in C++ MAIN (passed as literal true);
      this port omits it since it adds no algorithmic content.
"""

import math
import random
from dataclasses import dataclass, field
from pathlib import Path

from fcpp_bridge.python_dsl import aggregate_function, Neighborhood
from examples._example_utils import report_validation, report_transpilation

# ---------------------------------------------------------------------------
# Simulation constants (deployment parameters — configured externally in C++)
# ---------------------------------------------------------------------------

NUM_NODES = 30      # swarm size
SIDE = 300.0        # deployment area side (square)
COMM = 80.0         # communication radius
SPEED = 12.0        # movement speed per round
NUM_ROUNDS = 40     # simulation rounds

INF_INT = 2_147_483_647   # C++: constexpr int inf_int = 2147483647
ERROR_TTL = -1            # sentinel: node has invalid/error state
TTL_THRESHOLD = 10        # C++: threshold_TTL_const_ten returns 10
METRIC_HOP = 1            # C++: metric_unitary_hop returns 1

LOG_DIR = Path(__file__).parent / "logs"


# ---------------------------------------------------------------------------
# State dataclass
# ---------------------------------------------------------------------------

@dataclass
class ChainDecayingState:
    """
    Per-node state for the chain-decaying algorithm.

    Mirrors the C++ decaying_node_data<int> tuple and node storage tags:
        is_source   (bool) — True if this node is a chain extremity (uid % 17 == 0)
        in_channel  (bool) — True if node is alive in the decaying chain (ttl > -1)
        should_hold (bool) — get<0>: False = do NOT increment TTL (extremity or near one)
        hops        (int)  — get<1>: hop distance from the nearest extremity
        ttl         (int)  — get<2>: TTL counter; error_ttl=-1 = invalid/decayed
        next_uid    (int)  — get<3>: UID of the nearest-to-extremity neighbor
    """
    is_source: bool = False
    in_channel: bool = False
    should_hold: bool = True
    hops: int = INF_INT
    ttl: int = ERROR_TTL
    next_uid: int = 0


# ---------------------------------------------------------------------------
# Aggregate function — Python DSL definition (transpiles to C++)
# ---------------------------------------------------------------------------

@aggregate_function
class ChainDecayingAggregate:
    """
    Aggregate program: TTL-based decaying chain using nbr + min_hood.

    Translated from: fcpp-sample-project/run/chain_decaying.hpp

    The C++ MAIN() calls is_alive_decaying(CALL, is_source, true, inf_int,
    metric_unitary_hop, threshold_TTL_const_ten).  The function body is a
    single nbr call with a complex multi-branch update lambda; this Python
    port inlines that logic.

    Key insight of the algorithm:
        - nbr shares and receives the 4-tuple (should_hold, hops, ttl, next_uid).
        - min_hood picks the neighbor tuple with the lowest lexicographic value —
          which corresponds to the node closest to a chain extremity (source).
        - Extremity nodes always return (False, 0, 0, uid) — refreshing TTL to 0.
        - Non-extremity nodes increment their TTL when isolated (am_I_closest) or
          when their best neighbor says to increment (should_hold=True).
        - Nodes decay (TTL >= threshold) when they lose all paths to extremities.

    Primitive → C++ mapping:
        nbr(...)      → nbr(CALL, ...)      [basics.hpp]
        min_hood(...) → min_hood(CALL, ...) [basics.hpp]
    """

    def initial_state(self) -> ChainDecayingState:
        return ChainDecayingState()

    def compute(
        self,
        self_state: ChainDecayingState,
        neighbors: Neighborhood[ChainDecayingState],
    ) -> ChainDecayingState:
        """
        Replicates C++ MAIN() from chain_decaying.hpp in order:
          1. is_source = (node_uid % 17 == 0)
          2. nbr(initial_tuple, update_lambda)  — propagate chain state via min_hood
          3. in_channel = data.ttl > error_ttl

        C++ MAIN():
            is_source = is_source_node(node.uid);  // uid % 17 == 0
            in_chan = is_alive_decaying(CALL,
                is_source, /*was_on_chain=*/true, inf_int,
                [](node_t&, device_t) -> int { return 1; },      // metric: 1 hop
                [](node_t&, decaying_node_data<int>) -> int { return 10; }  // TTL threshold
            );

        C++ is_alive_decaying body (inlined here):
            data = nbr(CALL,
                (! is_source, is_source?0:inf_int, is_source?0:-1, node.uid),
                [&](field<decaying_node_data<int>> d) {
                    myself = self(d, node.uid);
                    n      = min_hood(CALL, d);
                    // ... compute has_to_increment, increment ttl, decay check
                    return n;
                });
            return get<2>(data) > error_ttl;
        """
        # ── Step 1: source determination ──────────────────────────────────────
        # C++: is_source = is_source_node(node.uid);  // node.uid % 17 == 0
        # Python: is_source flag is set in state during initialization.
        is_source = self_state.is_source

        # ── Step 2: nbr with decaying-chain update lambda ─────────────────────
        # Initial tuple per node:
        #   extremity (is_source): (False, 0, 0, self_uid)  — TTL=0, no increment
        #   interior  (not source): (True, INF_INT, -1, self_uid) — high hops, invalid TTL
        #
        # The update lambda (inlined from is_alive_decaying):
        #   n = min_hood(d)  — pick the neighbor with the best (lowest) chain state
        #   if extremity: return fresh (False, 0, 0, uid)
        #   if isolated (n == myself): increment TTL (decay path)
        #   if has_to_increment: TTL += metric (1 hop)
        #   if TTL >= threshold (10): return decayed state
        #   return n with should_hold updated
        #
        # NOTE: min_hood is called inside the nbr lambda — both are FCPP primitives
        # recognized by the transpiler. The Python lambda below is a simplified
        # representation; the full multi-branch logic lives in _demo_simulate().
        data = nbr(  # noqa: F821
            (not is_source, 0 if is_source else INF_INT, 0 if is_source else ERROR_TTL, 0),
            lambda d: min_hood(d),  # noqa: F821  — full logic: see _demo_simulate
        )

        # ── Step 3: liveness check ────────────────────────────────────────────
        # C++: return get<2>(data) > error_ttl;
        in_channel = data[2] > ERROR_TTL

        return ChainDecayingState(
            is_source=is_source,
            in_channel=in_channel,
            should_hold=data[0],
            hops=data[1],
            ttl=data[2],
            next_uid=data[3],
        )


# ---------------------------------------------------------------------------
# Demo simulation
# ---------------------------------------------------------------------------

def _demo_simulate() -> None:
    """
    Pure-Python faithful implementation of chain_decaying.hpp.

    Implements the full is_alive_decaying logic including:
        - min_hood over the 4-tuple field to find the best path to an extremity
        - am_I_closest detection (isolated node)
        - has_to_increment flag propagation
        - TTL increment with unitary-hop metric
        - Decay detection (TTL >= threshold)
        - should_hold propagation (only hold if hops > 0)
    """
    random.seed(31)

    positions = {
        i: (random.uniform(0.0, SIDE), random.uniform(0.0, SIDE))
        for i in range(NUM_NODES)
    }

    def is_source_node(uid: int) -> bool:
        return uid % 17 == 0

    # Each node's 4-tuple: (should_hold, hops, ttl, next_uid)
    # Initialize all nodes with their starting values.
    node_data: dict[int, tuple] = {}
    for i in range(NUM_NODES):
        src = is_source_node(i)
        node_data[i] = (not src, 0 if src else INF_INT, 0 if src else ERROR_TTL, i)

    def neighbors_of(nid: int) -> list[int]:
        x, y = positions[nid]
        return [
            j for j in range(NUM_NODES)
            if j != nid
            and math.dist((x, y), positions[j]) <= COMM
        ]

    def _chain_update(
        nid: int,
        is_src: bool,
        nbrs: list[int],
        node_data: dict[int, tuple],
    ) -> tuple:
        """
        Applies the is_alive_decaying update lambda for one node.

        Mirrors the C++ lambda passed to nbr:
            myself = self(d, node.uid)
            n      = min_hood(d)           — minimum tuple across self + neighbors
            if extremity: return (False, 0, 0, uid)
            am_I_closest = (n == myself)
            has_to_increment = am_I_closest OR get<0>(n)
            if has_to_increment: increment hops (if not am_I_closest), increment TTL
            if TTL >= threshold: return decayed
            get<0>(n) = (get<1>(n) > 0) AND get<0>(n)
            return n
        """
        if is_src:
            # Extremity always refreshes the chain
            return (False, 0, 0, nid)

        myself = node_data[nid]

        # Field d = self + current neighbors (FCPP nbr field includes self)
        field_values = [myself] + [node_data[n] for n in nbrs]
        n = list(min(field_values))   # min uses lexicographic tuple comparison

        am_I_closest = (tuple(n) == myself)
        has_to_increment = am_I_closest or n[0]   # isolated OR neighbor says increment

        if has_to_increment:
            if not am_I_closest:
                n[1] += 1   # increment hops count (we're using a neighbor's data)
            n[2] += METRIC_HOP  # increment TTL by 1 (unitary hop metric)

        if n[2] >= TTL_THRESHOLD:
            # Decayed: node leaves the chain
            return (False, INF_INT, ERROR_TTL, nid)

        # Propagate should_hold: suppress increment if close enough to extremity (hops=0)
        n[0] = (n[1] > 0) and n[0]

        return tuple(n)

    LOG_DIR.mkdir(exist_ok=True)
    log_files = {}

    for round_num in range(NUM_ROUNDS):
        new_data = {}

        for nid in range(NUM_NODES):
            # Step 1: rectangle_walk
            x, y = positions[nid]
            positions[nid] = (
                max(0.0, min(SIDE, x + random.uniform(-SPEED, SPEED))),
                max(0.0, min(SIDE, y + random.uniform(-SPEED, SPEED))),
            )

            # Step 2: nbr + min_hood (is_alive_decaying core)
            nbrs = neighbors_of(nid)
            is_src = is_source_node(nid)
            new_data[nid] = _chain_update(nid, is_src, nbrs, node_data)

        node_data = new_data

        # Step 3: derive in_channel and write log
        for nid in range(NUM_NODES):
            d = node_data[nid]
            is_src = is_source_node(nid)
            in_chan = d[2] > ERROR_TTL

            if nid not in log_files:
                log_path = LOG_DIR / f"node_{nid}_chain_decaying.log"
                lf = open(log_path, "w")
                lf.write(
                    f"# ChainDecaying — node {nid}  (is_source={is_src})\n"
                    "# round,is_source,in_channel,should_hold,hops,ttl,next_uid\n"
                )
                log_files[nid] = lf

            log_files[nid].write(
                f"{round_num},{int(is_src)},{int(in_chan)},"
                f"{int(d[0])},{d[1]},{d[2]},{d[3]}\n"
            )

    for lf in log_files.values():
        lf.close()

    src_nodes = [i for i in range(NUM_NODES) if is_source_node(i)]
    alive_nodes = [i for i in range(NUM_NODES) if node_data[i][2] > ERROR_TTL]
    print(f"    Wrote {NUM_NODES} log files → {LOG_DIR}/")
    print(f"    Source (extremity) nodes: {src_nodes}")
    print(f"    Nodes in chain after {NUM_ROUNDS} rounds: "
          f"{len(alive_nodes)}/{NUM_NODES} → {alive_nodes}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("\n" + "=" * 70)
    print("FCPP Bridge — Chain Decaying Example")
    print("Ported from: fcpp-sample-project/run/chain_decaying.hpp")
    print("=" * 70 + "\n")

    print("[1/3] Validating Python DSL...")
    try:
        report_validation(ChainDecayingAggregate)
    except Exception as exc:
        print(f"    FAIL: {exc}")
        return

    print("\n[2/3] Transpiling to C++...")
    report_transpilation(ChainDecayingAggregate)

    print("\n[3/3] Running demo simulation and writing per-node logs...")
    print(f"    Nodes: {NUM_NODES}  |  Rounds: {NUM_ROUNDS}  |  COMM: {COMM}")
    print(f"    Source criterion: uid % 17 == 0  |  TTL threshold: {TTL_THRESHOLD}")
    _demo_simulate()

    print("\nAlgorithm summary:")
    print("  Chain extremity nodes: uid % 17 == 0 — continuously refresh TTL to 0.")
    print("  Interior nodes: propagate the minimum (freshest) chain state via nbr.")
    print("    4-tuple: (should_hold, hops, ttl, next_uid)")
    print("    min_hood picks the tuple closest to an extremity (lowest lex. order).")
    print("    If isolated (am_I_closest): TTL increments by 1 each round.")
    print("    If TTL >= 10: node decays — leaves the chain.")
    print("    should_hold=(hops>0 AND should_hold): suppresses increment near source.")
    print()
    print("Primitives used:")
    print("  basics.hpp: nbr, min_hood")
    print()


if __name__ == "__main__":
    main()
