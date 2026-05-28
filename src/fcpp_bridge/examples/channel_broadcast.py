"""
Channel Broadcast example — fcpp_bridge port of channel_broadcast.hpp.

Original C++ source:
    fcpp-sample-project/lib/channel_broadcast.hpp
    Author: Giorgio Audrito (Copyright © 2021)

Algorithm (same order as C++ MAIN + channel helper):
    1. rectangle_walk    — nodes move randomly in a 3D deployment area
    2. bis_distance(src) — BIS distance from the source node (device 0)
    3. bis_distance(dst) — BIS distance from the destination node (device 1)
    4. broadcast(ds, dd) — broadcast ds (distance-to-source) so every node
                           can compute the straight-line source→destination span
    5. in_channel check  — node is "in channel" iff ds + dd < span + width

The elliptical channel selects all nodes whose combined distance to both
endpoints is within `width` of the straight source-destination path length.

Log files:
    Per-node logs written to examples/logs/node_<id>_channel_broadcast.log
    Each line: round, is_source, is_dest, source_dist, dest_dist, in_channel

Differences from original C++:
    - Source (device 0) and destination (device 1) are static by device ID.
      The Python port carries is_source / is_dest in the state (set externally).
    - Demo simulation uses a simplified spatial topology.
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
# Simulation constants (matching channel_broadcast.hpp)
# ---------------------------------------------------------------------------

DEVICES = 30        # number of nodes
COMM = 100          # communication radius
# deployment area side ≈ sqrt(devices*3000)
SIDE = int(math.isqrt(DEVICES * 3000)) + 1
HEIGHT = 100        # deployment area height
CHANNEL_WIDTH = 20  # ellipse half-width
SPEED = 10          # movement speed per round
NUM_ROUNDS = 25     # simulation rounds


# ---------------------------------------------------------------------------
# State dataclass
# ---------------------------------------------------------------------------

@dataclass
class ChannelState:
    """
    Per-node state for the channel-broadcast algorithm.

    Mirrors the node storage tags declared in channel_broadcast.hpp:
        is_source   (bool)   — true for device 0 (the source endpoint)
        is_dest     (bool)   — true for device 1 (the destination endpoint)
        source_dist (float)  — BIS distance to the source
        dest_dist   (float)  — BIS distance to the destination
        in_channel  (bool)   — whether this node lies within the elliptical channel
    """
    is_source: bool = False
    is_dest: bool = False
    source_dist: float = math.inf
    dest_dist: float = math.inf
    in_channel: bool = False


# ---------------------------------------------------------------------------
# Aggregate function — Python DSL definition (transpiles to C++)
# ---------------------------------------------------------------------------

@aggregate_function
class ChannelBroadcastAggregate:
    """
    Aggregate program: elliptical channel selection between two endpoint nodes.

    Translated from: fcpp-sample-project/lib/channel_broadcast.hpp

    The channel() helper function in C++ calls bis_distance twice (once for the
    source, once for the destination) and uses broadcast to propagate the
    source-to-destination span.  All those calls appear in compute() below in
    the same order as in the C++ code.

    Primitive → C++ mapping:
        rectangle_walk(...)     → rectangle_walk(CALL, ...)   [geometry.hpp]
        bis_distance(...)       → bis_distance(CALL, ...)     [spreading.hpp]
        broadcast(...)          → broadcast(CALL, ...)        [spreading.hpp]
    """

    def initial_state(self) -> ChannelState:
        """Start with unknown distances; source and dest flags set externally."""
        return ChannelState()

    def compute(
        self,
        self_state: ChannelState,
        neighbors: Neighborhood[ChannelState],
    ) -> ChannelState:
        """
        Replicates the C++ MAIN() + channel() bodies in order.

        C++ MAIN():
            rectangle_walk(CALL, {0,0,0}, {side,side,height}, 10, 1);
            channel(CALL, is_src, is_dst, 20);

        C++ channel():
            double ds = bis_distance(CALL, source, 1, 100);
            double dd = bis_distance(CALL, dest,   1, 100);
            bool c = ds + dd < broadcast(CALL, ds, dd) + width;
            c = c or source or dest;
        """
        # ── Step 1: random walk in 3D box [0,0,0] → [SIDE,SIDE,HEIGHT] ───────
        # C++: rectangle_walk(CALL, make_vec(0,0,0), make_vec(side,side,height), 10, 1);
        rectangle_walk(  # noqa: F821
            (0.0, 0.0, 0.0),
            (float(SIDE), float(SIDE), float(HEIGHT)),
            float(SPEED),
            1,
        )

        # ── Step 2: BIS distance from the source endpoint (device 0) ─────────
        # C++ channel(): double ds = bis_distance(CALL, source, 1, 100);
        # Parameters: is_source flag, precision=1, speed=100
        ds = bis_distance(self_state.is_source, 1, 100)  # noqa: F821

        # ── Step 3: BIS distance from the destination endpoint (device 1) ────
        # C++ channel(): double dd = bis_distance(CALL, dest, 1, 100);
        dd = bis_distance(self_state.is_dest, 1, 100)    # noqa: F821

        # ── Step 4: broadcast ds (source distance) from source to whole network
        # This propagates the direct source→destination path length to all nodes.
        # C++ channel(): bool c = ds + dd < broadcast(CALL, ds, dd) + width;
        # broadcast(dist_field, value): routes `value` from the source of the gradient.
        # Here we broadcast `dd` (destination distance) along the `ds` gradient,
        # so each node gets the distance from source to the nearest point on the
        # path to the destination — i.e., the source-to-destination span.
        span = broadcast(ds, dd)  # noqa: F821

        # ── Step 5: channel membership check ─────────────────────────────────
        # The elliptical channel: node is inside iff its total path length
        # (via both endpoints) is close to the direct span.
        in_channel = (
            (ds + dd < span + CHANNEL_WIDTH)
            or self_state.is_source
            or self_state.is_dest
        )

        return ChannelState(
            is_source=self_state.is_source,
            is_dest=self_state.is_dest,
            source_dist=ds,
            dest_dist=dd,
            in_channel=in_channel,
        )


# ---------------------------------------------------------------------------
# Demo simulation — AbstractExample subclass
# ---------------------------------------------------------------------------

def _bis_distance(is_endpoint: bool, nbr_dists: list) -> float:
    """Approximate BIS distance: like ABF but with smoother convergence."""
    if is_endpoint:
        return 0.0
    if not nbr_dists:
        return math.inf
    return min(nbr_dists) + COMM * 0.1


class ChannelBroadcastExample(AbstractExample):
    """Pure-Python faithful implementation of channel_broadcast.hpp.

    Implements the same 5 steps as compute() using Python logic so that
    per-node log files can be produced without a C++ compiler.

    Nodes are stored as dict[int, ChannelState]; the initial set is
    range(DEVICES) but nodes may join or leave between rounds.
    """

    def __init__(self, seed: int = 7):
        self._rng = random.Random(seed)
        self._final_states: dict = {}

    @property
    def log_prefix(self) -> str:
        return "channel_broadcast"

    def initial_positions(self) -> dict:
        return {
            i: (self._rng.uniform(0.0, SIDE), self._rng.uniform(0.0, SIDE))
            for i in range(DEVICES)
        }

    def initial_states(self, positions: dict) -> dict:
        return {
            nid: ChannelState(is_source=(nid == 0), is_dest=(nid == 1))
            for nid in positions
        }

    def round_step(self, round_num: int, positions: dict, states: dict) -> tuple:
        new_positions = {}
        new_states = {}

        for nid, (x, y) in positions.items():
            new_positions[nid] = (
                max(0.0, min(SIDE, x + self._rng.uniform(-SPEED, SPEED))),
                max(0.0, min(SIDE, y + self._rng.uniform(-SPEED, SPEED))),
            )

        for nid in positions:
            s = states[nid]
            nbrs = neighbors_of(positions, nid, COMM)
            nbr_s = [states[n] for n in nbrs]

            # Step 2: BIS distance to source
            ds = _bis_distance(
                s.is_source,
                [ns.source_dist for ns in nbr_s if math.isfinite(ns.source_dist)],
            )

            # Step 3: BIS distance to destination
            dd = _bis_distance(
                s.is_dest,
                [ns.dest_dist for ns in nbr_s if math.isfinite(ns.dest_dist)],
            )

            # Step 4: broadcast — propagate dd from source along ds gradient
            if s.is_source:
                span = dd
            else:
                parents = [
                    (ns.source_dist, ns.dest_dist)
                    for ns in nbr_s
                    if ns.source_dist < ds and math.isfinite(ns.source_dist)
                ]
                if parents:
                    span = min(parents, key=lambda t: t[0])[1]
                else:
                    span = s.source_dist + s.dest_dist

            # Step 5: channel check
            in_channel = (
                (ds + dd < span + CHANNEL_WIDTH)
                or s.is_source
                or s.is_dest
            )

            new_states[nid] = ChannelState(
                is_source=s.is_source,
                is_dest=s.is_dest,
                source_dist=ds,
                dest_dist=dd,
                in_channel=in_channel,
            )

        return new_positions, new_states

    def log_header(self, node_id: int, state) -> str:
        return (
            f"# ChannelBroadcast — node {node_id}\n"
            "# round,is_source,is_dest,source_dist,dest_dist,in_channel\n"
        )

    def log_line(self, round_num: int, node_id: int, state) -> str:
        return (
            f"{round_num},{int(state.is_source)},{int(state.is_dest)},"
            f"{state.source_dist:.4f},{state.dest_dist:.4f},{int(state.in_channel)}\n"
        )

    def on_round_complete(self, round_num: int, positions: dict, states: dict) -> None:
        self._final_states = states

    def on_simulation_end(self) -> None:
        states = self._final_states
        in_channel_count = sum(1 for s in states.values() if s.in_channel)
        print(f"    Wrote {DEVICES} log files → {self.log_dir}/")
        print(f"    Last round: {in_channel_count}/{DEVICES} nodes inside the channel")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("\n" + "=" * 70)
    print("FCPP Bridge — Channel Broadcast Example")
    print("Ported from: fcpp-sample-project/lib/channel_broadcast.hpp")
    print("=" * 70 + "\n")

    print("[1/3] Validating Python DSL...")
    try:
        report_validation(ChannelBroadcastAggregate)
    except Exception as exc:
        print(f"    FAIL: {exc}")
        return

    print("\n[2/3] Transpiling to C++...")
    report_transpilation(ChannelBroadcastAggregate)

    print("\n[3/3] Running demo simulation and writing per-node logs...")
    print(f"    Nodes: {DEVICES}  |  Rounds: {NUM_ROUNDS}")
    print(
        f"    Source: node 0  |  Destination: node 1  |  Channel width: {CHANNEL_WIDTH}")
    ChannelBroadcastExample().run(NUM_ROUNDS)

    print("\nAlgorithm summary:")
    print("  1. rectangle_walk  — random 3D movement")
    print("  2. bis_distance(source)      — smooth distance to source endpoint")
    print("  3. bis_distance(destination) — smooth distance to destination endpoint")
    print("  4. broadcast(ds, dd)         — propagate destination distance from source")
    print("  5. in_channel = ds+dd < span + width  — elliptical membership test")
    print()
    print("Primitives used:")
    print("  geometry.hpp  : rectangle_walk")
    print("  spreading.hpp : bis_distance, broadcast")
    print()


if __name__ == "__main__":
    main()
