"""
Message Dispatch example — fcpp_bridge port of message_dispatch.hpp.

Original C++ source:
    fcpp-sample-project/lib/message_dispatch.hpp
    Author: Giorgio Audrito (Copyright © 2022)

Algorithm (same order as C++ MAIN):
    1. rectangle_walk  — nodes move randomly in a 3D deployment area
    2. bis_distance    — compute gradient distance from source device (device 0)
    3. min_hood + nbr  — find spanning-tree parent (nearest neighbor toward source)
    4. sp_collection   — collect routing sets: which node IDs are "below" each node
    5. spawn           — dispatch each message as a per-message aggregate process
    6. old             — persist a map of received messages across rounds

The algorithm routes point-to-point messages from any sender to any receiver
along a spanning tree rooted at device 0, avoiding network flooding.
Each message process runs only on nodes whose subtree contains either the
sender or the receiver ("inpath" condition).

Log files:
    Per-node logs written to examples/logs/node_<id>_message_dispatch.log
    Each line: round, is_source, center_dist, routing_set_size,
                               received_count, active_procs

Running:
    MessageDispatchExample().run(NUM_ROUNDS) invokes the full toolchain:
    validate → transpile → compile → SwarmProcess → per-node logs.
    A C++ compiler and FCPP headers are required.

Differences from original C++:
    - Devices: C++ uses 300; this port uses 30 for manageable log output.
    - Message injection: C++ generates random messages during simulated time [10..50]
      using node.current_time() and node.next_real()/next_int().
      This port uses an old() round counter; non-source nodes inject one message
      every 10 rounds during rounds 10..50 (deterministic approximation).
    - node.nbr_uid(): used in spanning-tree construction; the nbr(ds) field in the
      Python DSL uses 0 as a placeholder UID since node.nbr_uid() is C++ API.
    - status enum: C++ uses status::internal/border/terminated_output (enum class);
      Python uses integer constants STATUS_BORDER/INTERNAL/TERMINATED.
    - routing_set uses placeholder UID 0 in DSL; actual UIDs in demo simulation.
    - sp_collection uses frozenset (Python) instead of std::unordered_set<device_t>.
"""

import math
import random
from dataclasses import dataclass, field
from typing import Any

from fcpp_bridge.python_dsl import aggregate_function, Neighborhood
from fcpp_bridge.examples._example_utils import (
    SPAWN_STATUS_BORDER,
    SPAWN_STATUS_INTERNAL,
    SPAWN_STATUS_TERMINATED,
    report_validation,
    report_transpilation,
)
from fcpp_bridge.examples.abstract_example import AbstractExample

# ---------------------------------------------------------------------------
# Simulation constants
# ---------------------------------------------------------------------------

DEVICES = 30        # C++ original uses 300; reduced here for demo output
COMM = 100          # communication radius
SIDE = int(math.isqrt(DEVICES * 3000)) + 1  # deployment area side ≈ sqrt(devices*3000)
HEIGHT = 100        # deployment area height
SPEED = 10          # movement speed per round
NUM_ROUNDS = 60     # simulation rounds (C++ runs ~100 time units of simulation)
MSG_START = 10      # first round for message injection
MSG_END = 50        # last round for message injection
MSG_INTERVAL = 10   # inject one message per node every MSG_INTERVAL rounds

# Status codes — aliases of the shared SPAWN_STATUS_* constants from _example_utils
STATUS_BORDER = SPAWN_STATUS_BORDER          # node not in routing path
STATUS_INTERNAL = SPAWN_STATUS_INTERNAL      # node is in the routing path
STATUS_TERMINATED = SPAWN_STATUS_TERMINATED  # node is the message destination


# ---------------------------------------------------------------------------
# State dataclass
# ---------------------------------------------------------------------------

@dataclass
class MessageDispatchState:
    """
    Per-node state for the message-dispatch algorithm.

    Mirrors key node storage tags from message_dispatch.hpp:
        is_source     (bool)          — True for device 0 (spanning-tree root)
        center_dist   (float)         — BIS distance from source (defines the tree gradient)
        routing_set   (frozenset[int])— node IDs in this node's subtree ("below" in tree)
        received_count (int)          — distinct messages delivered to this node so far
        active_procs  (int)           — spawn processes active at this node this round
    """
    is_source: bool = False
    center_dist: float = math.inf
    routing_set: frozenset = field(default_factory=frozenset)
    received_count: int = 0
    active_procs: int = 0


# ---------------------------------------------------------------------------
# Aggregate function — Python DSL definition (transpiles to C++)
# ---------------------------------------------------------------------------

@aggregate_function
class MessageDispatchAggregate:
    """
    Aggregate program: spawn-based point-to-point message routing.

    Translated from: fcpp-sample-project/lib/message_dispatch.hpp

    Architecture:
        - A spanning tree rooted at device 0 provides a routing backbone.
        - Each node collects, via sp_collection, the set of UIDs "below" it.
        - A message (from, to, time) spawns one aggregate process; the process
          runs on nodes whose subtree contains 'from' OR 'to' (inpath condition).
        - old() persists the delivery map between rounds.

    Primitive → C++ mapping:
        rectangle_walk(...)   → rectangle_walk(CALL, ...)   [geometry.hpp]
        bis_distance(...)     → bis_distance(CALL, ...)     [spreading.hpp]
        nbr(...)              → nbr(CALL, ...)              [basics.hpp]
        min_hood(...)         → min_hood(CALL, ...)         [basics.hpp]
        old(...)              → old(CALL, ...)              [basics.hpp]
        sp_collection(...)    → sp_collection(CALL, ...)    [collection.hpp]
        spawn(...)            → spawn(CALL, ...)            [utils/aggregates.hpp]
    """

    def initial_state(self) -> MessageDispatchState:
        return MessageDispatchState()

    def compute(
        self,
        self_state: MessageDispatchState,
        neighbors: Neighborhood[MessageDispatchState],
    ) -> MessageDispatchState:
        """
        Replicates C++ MAIN() from message_dispatch.hpp in order:
          1. rectangle_walk  — 3D random walk
          2. bis_distance    — gradient from source (device 0)
          3. min_hood + nbr  — spanning-tree parent (nearest-to-source neighbor)
          4. sp_collection   — subtree routing sets (node UIDs below each node)
          5. old + spawn     — round counter, message injection, process dispatch
          6. old             — persist map of received messages
        """
        # ── Step 1: random walk in 3D box ─────────────────────────────────────
        # C++: rectangle_walk(CALL, make_vec(0,0,0), make_vec(side,side,height), speed, 1);
        rectangle_walk(  # noqa: F821
            (0.0, 0.0, 0.0),
            (float(SIDE), float(SIDE), float(HEIGHT)),
            float(SPEED),
            1,
        )

        # ── Step 2: BIS distance from source ─────────────────────────────────
        # C++: double ds = bis_distance(CALL, is_src, 1, 100);
        is_src = (self_uid() == 0)  # noqa: F821
        ds = bis_distance(is_src, 1, 100)  # noqa: F821

        # ── Step 3: spanning-tree parent ──────────────────────────────────────
        # C++: device_t parent = get<1>(
        #          min_hood(CALL, make_tuple(nbr(CALL, ds), node.nbr_uid())));
        # nbr(ds): field of neighbors' ds values.
        # min_hood picks (min_dist, its_uid) → parent is the uid component.
        # NOTE: 0 is a placeholder for node.nbr_uid() (C++ API not in Python DSL).
        parent = min_hood(  # noqa: F821
            (nbr(ds), 0),   # noqa: F821  — (distance_field, uid_field)
        )

        # ── Step 4: routing sets ──────────────────────────────────────────────
        # C++: set_t below = sp_collection(CALL, ds, set_t{node.uid}, set_t{},
        #          [](set_t x, set_t const& y){ x.insert(y.begin(),y.end()); return x; });
        # Each node contributes its own UID; sp_collection unions sets up toward source.
        below = sp_collection(  # noqa: F821
            ds,
            frozenset({0}),      # local value: {this node's ID} — 0 is placeholder
            frozenset(),         # null value: empty set
            lambda x, y: x | y, # accumulator: set union
        )

        # ── Step 5: round counter + message injection + spawn ─────────────────
        # Round counter tracks simulation ticks for the injection window.
        round_tick = old(0, lambda t: t + 1)  # noqa: F821

        # Non-source nodes inject a new message toward device 0 every MSG_INTERVAL
        # rounds during the injection window [MSG_START, MSG_END].
        new_msg = (  # noqa: F821
            (self_uid(), 0, round_tick)  # (from, to, time) — 0 placeholder for to  # noqa: F821
            if (MSG_START <= round_tick <= MSG_END
                and round_tick % MSG_INTERVAL == 0
                and not is_src)
            else None
        )

        # C++: map_t r = spawn(CALL, [&](message const& m) {
        #         bool inpath = below.count(m.from) + below.count(m.to) > 0;
        #         status s = node.uid == m.to ? status::terminated_output :
        #                    inpath ? status::internal : status::border;
        #         return make_tuple(node.current_time(), s);
        #     }, m);
        r = spawn(  # noqa: F821
            lambda m: (
                0.0,   # delivery timestamp — C++: node.current_time()
                STATUS_TERMINATED if m[1] == 0       # destination check (0 = placeholder)
                else STATUS_INTERNAL if (m[0] in below or m[1] in below)
                else STATUS_BORDER,
            ),
            new_msg,
        )

        # ── Step 6: persist received messages ────────────────────────────────
        # C++: r = old(CALL, map_t{}, [&](map_t prev) {
        #         for (auto& x : r) { /* update delivery stats; persist new entries */ }
        #         return prev_with_new_entries;
        #     });
        received = old(  # noqa: F821
            {},
            lambda prev: {**prev, **r},  # merge newly received into persistent map
        )

        return MessageDispatchState(
            is_source=is_src,
            center_dist=ds,
            routing_set=below,
            received_count=len(received),
            active_procs=len(r),
        )


# ---------------------------------------------------------------------------
# AbstractExample subclass — toolchain bridge
# ---------------------------------------------------------------------------

class MessageDispatchExample(AbstractExample):
    """Runs MessageDispatchAggregate through the full toolchain.

    Validates, transpiles, compiles (SHA-256 cached), and runs the C++ binary.
    State updates arrive via IPC; per-node log files are written from snapshots.
    """

    def __init__(self, seed: int = 13):
        self._rng = random.Random(seed)
        self._last_snapshot = None

    @property
    def aggregate_class(self):
        return MessageDispatchAggregate

    @property
    def log_prefix(self) -> str:
        return "message_dispatch"

    def initial_positions(self) -> dict:
        return {
            i: (self._rng.uniform(0.0, SIDE), self._rng.uniform(0.0, SIDE))
            for i in range(DEVICES)
        }

    def log_header(self, node_id: int, state_data: Any) -> str:
        return (
            f"# MessageDispatch — node {node_id}\n"
            "# round,is_source,center_dist,"
            "routing_set_size,received_count,active_procs\n"
        )

    def log_line(self, round_num: int, node_id: int, state_data: Any) -> str:
        d = state_data if isinstance(state_data, dict) else vars(state_data)
        rs = d.get('routing_set', frozenset())
        rs_size = len(rs) if hasattr(rs, '__len__') else int(d.get('routing_set_size', 0))
        return (
            f"{round_num},{int(d.get('is_source', False))},"
            f"{d.get('center_dist', 0.0):.4f},"
            f"{rs_size},{d.get('received_count', 0)},{d.get('active_procs', 0)}\n"
        )

    def on_round_complete(self, round_num: int, snapshot) -> None:
        self._last_snapshot = snapshot

    def on_simulation_end(self) -> None:
        snap = self._last_snapshot
        total_received = 0
        if snap and snap.nodes:
            total_received = sum(
                (ns.state_data.get('received_count', 0)
                 if isinstance(ns.state_data, dict)
                 else getattr(ns.state_data, 'received_count', 0))
                for ns in snap.nodes
            )
        print(f"    Wrote {DEVICES} log files → {self.log_dir}/")
        print(f"    Total messages received across all nodes (last round): {total_received}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("\n" + "=" * 70)
    print("FCPP Bridge — Message Dispatch Example")
    print("Ported from: fcpp-sample-project/lib/message_dispatch.hpp")
    print("=" * 70 + "\n")

    print("[1/3] Validating Python DSL...")
    try:
        report_validation(MessageDispatchAggregate)
    except Exception as exc:
        print(f"    FAIL: {exc}")
        return

    print("\n[2/3] Transpiling to C++...")
    report_transpilation(MessageDispatchAggregate)

    print("\n[3/3] Running demo simulation and writing per-node logs...")
    print(f"    Nodes: {DEVICES}  |  Rounds: {NUM_ROUNDS}  |  Source: node 0")
    print(f"    Messages injected during rounds {MSG_START}..{MSG_END}, "
          f"every {MSG_INTERVAL} rounds  |  Channel width: {COMM}")
    MessageDispatchExample().run(NUM_ROUNDS)

    print("\nAlgorithm summary:")
    print("  1. rectangle_walk   — random 3D movement")
    print("  2. bis_distance     — smooth gradient from source (device 0)")
    print("  3. min_hood + nbr   — spanning-tree parent (nearest neighbor toward source)")
    print("  4. sp_collection    — routing subtree: node UIDs 'below' each node")
    print("  5. old + spawn      — round counter, message injection, process dispatch")
    print("       new_msg = (self_uid, 0, tick) for rounds 10..50 every 10 rounds")
    print("       status = terminated_output (at dest) | internal | border")
    print("  6. old              — persist received-message map across rounds")
    print()
    print("Primitives used:")
    print("  geometry.hpp       : rectangle_walk")
    print("  spreading.hpp      : bis_distance")
    print("  basics.hpp         : nbr, min_hood, old")
    print("  collection.hpp     : sp_collection")
    print("  utils/aggregates.hpp: spawn")
    print()


if __name__ == "__main__":
    main()
