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

Differences from original C++:
    - Devices: C++ uses 300; this port uses 30 for manageable log output.
    - Message injection: C++ generates random messages during simulated time [10..50]
      using node.current_time() and node.next_real()/next_int().
      Python demo uses round numbers 10..50 directly (1 round ≈ 1 time unit).
    - node.nbr_uid(): used in spanning-tree construction; the nbr(ds) field in the
      Python DSL uses 0 as a placeholder UID since node.nbr_uid() is C++ API.
    - status enum: C++ uses status::internal/border/terminated_output (enum class);
      Python uses integer constants STATUS_BORDER/INTERNAL/TERMINATED.
    - routing_set uses placeholder UID 0 in DSL; actual UIDs in _demo_simulate().
    - sp_collection uses frozenset (Python) instead of std::unordered_set<device_t>.
"""

import math
import random
from dataclasses import dataclass, field
from pathlib import Path

from fcpp_bridge.python_dsl import aggregate_function, Neighborhood
from examples._example_utils import report_validation, report_transpilation

# ---------------------------------------------------------------------------
# Simulation constants
# ---------------------------------------------------------------------------

DEVICES = 30        # C++ original uses 300; reduced here for demo output
COMM = 100          # communication radius
SIDE = int(math.isqrt(DEVICES * 3000)) + 1  # deployment area side ≈ sqrt(devices*3000)
HEIGHT = 100        # deployment area height
SPEED = 10          # movement speed per round
NUM_ROUNDS = 60     # simulation rounds (C++ runs ~100 time units of simulation)

LOG_DIR = Path(__file__).parent / "logs"

# Status codes mapping to C++ enum class status
STATUS_BORDER = 0        # node not in routing path
STATUS_INTERNAL = 1      # node is in the routing path
STATUS_TERMINATED = 2    # node is the message destination (terminated with output)


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
        sp_collection(...)    → sp_collection(CALL, ...)    [collection.hpp]
        spawn(...)            → spawn(CALL, ...)            [utils/aggregates.hpp]
        old(...)              → old(CALL, ...)              [basics.hpp]
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
          5. spawn           — one aggregate process per in-flight message
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
        is_src = self_state.is_source
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

        # ── Step 5: dispatch messages via spawn ───────────────────────────────
        # C++: map_t r = spawn(CALL, [&](message const& m) {
        #         bool inpath = below.count(m.from) + below.count(m.to) > 0;
        #         status s = node.uid == m.to ? status::terminated_output :
        #                    inpath ? status::internal : status::border;
        #         return make_tuple(node.current_time(), s);
        #     }, m);
        # The lambda is evaluated per active message process at each node.
        r = spawn(  # noqa: F821
            lambda m: (
                0.0,   # delivery timestamp — C++: node.current_time()
                STATUS_TERMINATED if m[1] == 0       # destination check (0 = placeholder)
                else STATUS_INTERNAL if (m[0] in below or m[1] in below)
                else STATUS_BORDER,
            ),
            None,   # optional new message to inject (C++: common::option<message> m)
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
# Demo simulation
# ---------------------------------------------------------------------------

def _demo_simulate() -> None:
    """
    Pure-Python approximation of the message-dispatch algorithm.

    Implements the same 6 steps as compute() for log generation without a
    C++ compiler.  Messages are routed via a spanning tree rooted at device 0.
    """
    random.seed(13)

    positions = {
        i: (random.uniform(0.0, SIDE), random.uniform(0.0, SIDE))
        for i in range(DEVICES)
    }

    states = {
        i: MessageDispatchState(is_source=(i == 0))
        for i in range(DEVICES)
    }

    # Persistent per-node delivery tracking
    total_received = {i: 0 for i in range(DEVICES)}
    # in_flight: message (from, to, creation_round) -> set of current node IDs hosting it
    in_flight: dict = {}

    def neighbors_of(nid):
        x, y = positions[nid]
        return [
            j for j in range(DEVICES)
            if j != nid
            and math.dist((x, y), positions[j]) <= COMM
        ]

    def _bis_distance(is_endpoint, nbr_dists):
        if is_endpoint:
            return 0.0
        if not nbr_dists:
            return math.inf
        return min(nbr_dists) + COMM * 0.1

    LOG_DIR.mkdir(exist_ok=True)
    log_files = {}

    for round_num in range(NUM_ROUNDS):
        new_states = {}
        distances = {}
        routing_sets = {}

        # ── Step 1 + 2: move nodes and compute BIS distances ─────────────────
        for nid in range(DEVICES):
            x, y = positions[nid]
            positions[nid] = (
                max(0.0, min(SIDE, x + random.uniform(-SPEED, SPEED))),
                max(0.0, min(SIDE, y + random.uniform(-SPEED, SPEED))),
            )

            nbrs = neighbors_of(nid)
            nbr_s = [states[n] for n in nbrs]
            distances[nid] = _bis_distance(
                nid == 0,
                [ns.center_dist for ns in nbr_s if math.isfinite(ns.center_dist)],
            )

        # ── Step 3: spanning-tree parents (min-distance neighbor) ─────────────
        parents = {}
        for nid in range(DEVICES):
            nbrs = neighbors_of(nid)
            if not nbrs or nid == 0:
                parents[nid] = -1
                continue
            best_nbr = min(nbrs, key=lambda n: distances[n])
            parents[nid] = best_nbr if distances[best_nbr] < distances[nid] else -1

        # ── Step 4: routing sets via sp_collection ────────────────────────────
        # Iterative convergence: each node's routing_set = {self} ∪ children's sets
        routing_sets = {nid: frozenset({nid}) for nid in range(DEVICES)}
        for _ in range(8):  # enough iterations for convergence
            new_rs = {}
            for nid in range(DEVICES):
                # Children: neighbors whose parent is nid
                children = [n for n in neighbors_of(nid) if parents.get(n) == nid]
                child_sets = [routing_sets[c] for c in children]
                new_rs[nid] = frozenset({nid}).union(*child_sets) if child_sets \
                    else frozenset({nid})
            routing_sets = new_rs

        # ── Step 5: generate new messages (1% probability, rounds 10..50) ─────
        if 10 <= round_num <= 50:
            for nid in range(DEVICES):
                if random.random() < 0.01:
                    to_id = random.randint(0, DEVICES - 2)
                    if to_id >= nid:
                        to_id += 1
                    m = (nid, to_id, round_num)
                    if m not in in_flight:
                        in_flight[m] = True  # newly spawned

        # Route messages: process stays alive at node if inpath
        delivered_this_round = set()
        active_procs = {nid: 0 for nid in range(DEVICES)}
        for m in list(in_flight.keys()):
            from_id, to_id, _ = m
            reached_dest = False
            for nid in range(DEVICES):
                rs = routing_sets[nid]
                inpath = (from_id in rs) or (to_id in rs)
                if inpath:
                    active_procs[nid] += 1
                    if nid == to_id:
                        reached_dest = True
            if reached_dest:
                delivered_this_round.add(m)
                total_received[to_id] += 1

        for m in delivered_this_round:
            del in_flight[m]

        # ── Build new states and write logs ───────────────────────────────────
        for nid in range(DEVICES):
            is_src = (nid == 0)
            ds = distances[nid]

            new_states[nid] = MessageDispatchState(
                is_source=is_src,
                center_dist=ds,
                routing_set=routing_sets[nid],
                received_count=total_received[nid],
                active_procs=active_procs[nid],
            )

            if nid not in log_files:
                log_path = LOG_DIR / f"node_{nid}_message_dispatch.log"
                lf = open(log_path, "w")
                lf.write(
                    f"# MessageDispatch — node {nid}\n"
                    "# round,is_source,center_dist,"
                    "routing_set_size,received_count,active_procs\n"
                )
                log_files[nid] = lf

            d = new_states[nid]
            log_files[nid].write(
                f"{round_num},{int(is_src)},{ds:.4f},"
                f"{len(d.routing_set)},{d.received_count},{d.active_procs}\n"
            )

        states = new_states

    for lf in log_files.values():
        lf.close()

    total_msgs_delivered = sum(total_received.values())
    print(f"    Wrote {DEVICES} log files → {LOG_DIR}/")
    print(f"    Total messages delivered across all nodes: {total_msgs_delivered}")
    print(f"    Messages still in flight: {len(in_flight)}")


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
    print(f"    Messages generated during rounds 10..50  |  Channel width: {COMM}")
    _demo_simulate()

    print("\nAlgorithm summary:")
    print("  1. rectangle_walk   — random 3D movement")
    print("  2. bis_distance     — smooth gradient from source (device 0)")
    print("  3. min_hood + nbr   — spanning-tree parent (nearest neighbor toward source)")
    print("  4. sp_collection    — routing subtree: node UIDs 'below' each node")
    print("  5. spawn            — one aggregate process per in-flight message")
    print("       inpath = from ∈ below OR to ∈ below")
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
