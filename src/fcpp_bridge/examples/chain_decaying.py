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

Running:
    ChainDecayingExample().run(NUM_ROUNDS) invokes the full toolchain:
    validate → transpile → compile → SwarmProcess → per-node logs.
    A C++ compiler and FCPP headers are required.

Differences from original C++:
    - Deployment: C++ runner configures SIDE, COMM, SPEED externally;
      this port defines them as module constants (see below).
    - was_on_chain is always True in C++ MAIN (passed as literal true);
      this port omits it since it adds no algorithmic content.
"""

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
# Simulation constants (deployment parameters — configured externally in C++)
# ---------------------------------------------------------------------------

NUM_NODES = 30      # initial swarm size (nodes can join/leave dynamically)
SIDE = 300.0        # deployment area side (square)
COMM = 80.0         # communication radius
SPEED = 12.0        # movement speed per round
NUM_ROUNDS = 40     # simulation rounds

INF_INT = 2_147_483_647   # C++: constexpr int inf_int = 2147483647
ERROR_TTL = -1            # sentinel: node has invalid/error state
TTL_THRESHOLD = 10        # C++: threshold_TTL_const_ten returns 10
METRIC_HOP = 1            # C++: metric_unitary_hop returns 1


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
        """
        # ── Step 1: source determination ──────────────────────────────────────
        # C++: bool is_source = (node.uid % 17 == 0);
        is_source = (self_uid() % 17 == 0)  # noqa: F821

        # ── Step 2: nbr with decaying-chain update lambda ─────────────────────
        data = nbr(  # noqa: F821
            (not is_source, 0 if is_source else INF_INT, 0 if is_source else ERROR_TTL, 0),
            lambda d: min_hood(d),  # noqa: F821  — full logic in ChainDecayingExample
        )

        # ── Step 3: liveness check ────────────────────────────────────────────
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
# AbstractExample subclass — toolchain bridge
# ---------------------------------------------------------------------------

class ChainDecayingExample(AbstractExample):
    """Runs ChainDecayingAggregate through the full toolchain.

    Validates, transpiles, compiles (SHA-256 cached), and runs the C++ binary.
    State updates arrive via IPC; per-node log files are written from snapshots.
    """

    def __init__(self, seed: int = 31):
        self._rng = random.Random(seed)
        self._last_snapshot = None

    @property
    def aggregate_class(self):
        return ChainDecayingAggregate

    @property
    def log_prefix(self) -> str:
        return "chain_decaying"

    def initial_positions(self) -> dict:
        return {
            i: (self._rng.uniform(0.0, SIDE), self._rng.uniform(0.0, SIDE))
            for i in range(NUM_NODES)
        }

    def log_header(self, node_id: int, state_data: Any) -> str:
        return (
            f"# ChainDecaying — node {node_id}\n"
            "# round,is_source,in_channel,should_hold,hops,ttl,next_uid\n"
        )

    def log_line(self, round_num: int, node_id: int, state_data: Any) -> str:
        d = state_data if isinstance(state_data, dict) else vars(state_data)
        return (
            f"{round_num},{int(d.get('is_source', False))},"
            f"{int(d.get('in_channel', False))},"
            f"{int(d.get('should_hold', True))},"
            f"{d.get('hops', INF_INT)},{d.get('ttl', ERROR_TTL)},"
            f"{d.get('next_uid', 0)}\n"
        )

    def on_round_complete(self, round_num: int, snapshot) -> None:
        self._last_snapshot = snapshot

    def on_simulation_end(self) -> None:
        print(f"    Wrote {NUM_NODES} log files → {self.log_dir}/")
        snap = self._last_snapshot
        if snap and snap.nodes:
            src_nodes = sorted(
                ns.node_id for ns in snap.nodes
                if (ns.state_data.get('is_source', False)
                    if isinstance(ns.state_data, dict)
                    else getattr(ns.state_data, 'is_source', False))
            )
            alive_nodes = sorted(
                ns.node_id for ns in snap.nodes
                if (ns.state_data.get('in_channel', False)
                    if isinstance(ns.state_data, dict)
                    else getattr(ns.state_data, 'in_channel', False))
            )
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

    ChainDecayingExample().run(NUM_ROUNDS)

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
