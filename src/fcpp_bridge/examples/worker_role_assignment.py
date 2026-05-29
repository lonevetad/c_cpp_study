"""
Worker Role Assignment — fcpp_bridge DSL example.

Demonstrates:
  1. Python ``match/case`` (→ C++ ``switch``) for per-role behavioral dispatch
  2. ``spawn`` to route periodic sensor-reading reports from endpoint sensor
     nodes to RECEIVER nodes every MSG_INTERVAL rounds
  3. ``bis_distance`` + ``sp_collection`` for spanning-tree message routing
  4. ``old`` to persist the received-message log across rounds
  5. ``self_uid()`` for the device's own unique identifier (→ ``node.uid``)
  6. ``RoleCommunicationType`` — communication role associated with each
     WorkerRole (endpoint / receiver / repeater)

Requires Python 3.10+ (``match/case`` statement).

WorkerRole integer values (stored in WorkerState.role):
    0 = UNASSIGNED            passive node (repeater type); no assigned task
    1 = RECEIVER              base station; accumulates all endpoint reports
    2 = LIDAR                 endpoint; depth/distance sensor
    3 = INFRARED_SENSOR       endpoint; heat-signature detector
    4 = REPEATER              repeater; signal amplifier and range extender
    5 = TORCHLIGHT_MICROPHONE endpoint; combined audio + illumination sensor
    6 = RUBBLES_REMOVER       endpoint; debris-clearing robot, reports status
    7 = FLYING_OVERSEER       endpoint; aerial survey drone

RoleCommunicationType values:
    0 = ENDPOINT  gathers sensor data from the environment; sends it to RECEIVER
    1 = RECEIVER  accumulates reports received from endpoints
    2 = REPEATER  relays data between nodes that are not in direct contact

Role ↔ RoleCommunicationType mapping:
    UNASSIGNED (0) → REPEATER  (passive relay candidate; no active data gathering)
    RECEIVER   (1) → RECEIVER
    LIDAR      (2) → ENDPOINT
    INFRARED_SENSOR       (3) → ENDPOINT
    REPEATER   (4) → REPEATER  (active signal amplifier and range extender)
    TORCHLIGHT_MICROPHONE (5) → ENDPOINT
    RUBBLES_REMOVER       (6) → ENDPOINT  (reports debris-clearing status)
    FLYING_OVERSEER       (7) → ENDPOINT

Endpoint roles (2, 3, 5, 6, 7): every MSG_INTERVAL rounds inject a sensor-
    reading message toward the nearest RECEIVER via spawn.
    RECEIVER (1) accumulates delivered messages.
Repeater roles (0, 4): relay data between nodes; do not inject sensor data.

Role assignment: ``ROLE_CYCLE[node_id % len(ROLE_CYCLE)]`` — 13-slot cycle,
    DEVICES = 26 (2 full cycles).  Totals: REPEATER-type=14, ENDPOINT-type=10,
    RECEIVER-type=2 (repeaters > endpoints > receivers).

Algorithm per round (all 8 steps execute at EVERY node):
  1. bis_distance    — distance gradient rooted at RECEIVER nodes
  2. nbr + min_hood  — spanning-tree parent toward nearest RECEIVER
  3. count_hood      — local neighbor count (used by LIDAR and REPEATER)
  4. sp_collection   — routing subtree ("below" set) for each node
  5. broadcast       — distribute nearest RECEIVER's UID to all nodes
  6. spawn           — route endpoint messages toward RECEIVER
  7. old             — persist received-message log across rounds
  8. match/case      — role-specific task + state assembly (no primitives inside cases)

Note on FCPP primitive ordering:
    All aggregate primitives (steps 1–7) are called outside the switch so that
    every node increments the internal CALL counter in the same order.  Only
    pure local computations (no nbr/old/spawn calls) appear inside case branches.

Note on self_uid():
    self_uid() returns ``node.uid`` in generated C++ (no CALL counter).
    In the Python DSL layer it returns 0 (placeholder), so the demo simulation
    below uses the real ``nid`` directly rather than calling compute().

Note on role assignment in toolchain mode:
    The C++ binary uses initial_state() → WorkerState(role=0) (UNASSIGNED) for
    all nodes, since the Python-side role assignment (ROLE_CYCLE) cannot be
    passed to the binary via the current IPC interface.  Role-specific behaviour
    will only execute correctly once role injection is added to the IPC protocol.

Log files written to examples/logs/:
    node_<id>_worker_role.log  — per-node per-round stats
    receiver_messages.log      — RECEIVER node received_count per round
"""

import math
import random
from dataclasses import dataclass
from enum import IntEnum
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
# WorkerRole enum
# ---------------------------------------------------------------------------

class WorkerRole(IntEnum):
    UNASSIGNED = 0  # 0 — passive node, no assigned task
    RECEIVER = 1  # 1 — base station, accumulates all endpoint reports
    LIDAR = 2  # 2 — endpoint: depth/distance sensor
    INFRARED_SENSOR = 3  # 3 — endpoint: heat-signature detector
    REPEATER = 4  # 4 — repeater: signal amplifier and range extender
    TORCHLIGHT_MICROPHONE = 5  # 5 — endpoint: combined audio + illumination sensor
    RUBBLES_REMOVER = 6  # 6 — relay: clears physical debris paths
    FLYING_OVERSEER = 7  # 7 — endpoint: aerial survey drone


# ---------------------------------------------------------------------------
# RoleCommunicationType enum + per-role mapping
# ---------------------------------------------------------------------------

class RoleCommunicationType(IntEnum):
    ENDPOINT = 0  # 0 — gathers sensor data from environment; sends it to RECEIVER
    RECEIVER = 1  # 1 — accumulates reports received from endpoints
    REPEATER = 2  # 2 — relays data between nodes that are not in direct contact


ENDPOINT_ROLES = frozenset({  # → 0
    WorkerRole.LIDAR,                 # 2
    WorkerRole.INFRARED_SENSOR,       # 3
    WorkerRole.TORCHLIGHT_MICROPHONE,  # 5
    WorkerRole.RUBBLES_REMOVER,       # 6
    WorkerRole.FLYING_OVERSEER,       # 7
})

REPEATER_ROLES = frozenset({  # → 2
    WorkerRole.UNASSIGNED,  # 0 — passive relay candidate
    WorkerRole.REPEATER,    # 4 — active signal amplifier
})


# Maps each WorkerRole to its RoleCommunicationType.
# Determines the node's role in the data-gathering communication flow.
ROLE_COMM_TYPE: dict = {
    **{r: RoleCommunicationType.ENDPOINT for r in ENDPOINT_ROLES},
    WorkerRole.RECEIVER:              RoleCommunicationType.RECEIVER,   # 1 → 1
    **{r: RoleCommunicationType.REPEATER for r in REPEATER_ROLES},
}


# ---------------------------------------------------------------------------
# Simulation constants
# ---------------------------------------------------------------------------

ADDITIONAL_REPEATERS_EACH_CYCLE = 5

ROLE_CYCLE = (    # total: 13-slots → 5 ENDPOINTs, 1 RECEIVER, 7 REPEATER-type (1 UNASSIGNED + (1+ADDITIONAL_REPEATERS_EACH_CYCLE) REPEATER).
    # 8 standard roles — one of each per cycle
    WorkerRole.UNASSIGNED,        WorkerRole.RECEIVER,
    WorkerRole.LIDAR,             WorkerRole.INFRARED_SENSOR,
    WorkerRole.REPEATER,          WorkerRole.TORCHLIGHT_MICROPHONE,
    WorkerRole.RUBBLES_REMOVER,   WorkerRole.FLYING_OVERSEER,
    # ADDITIONAL_REPEATERS_EACH_CYCLE extra WorkerRole.REPEATER nodes per assignment cycle
    *([WorkerRole.REPEATER] * ADDITIONAL_REPEATERS_EACH_CYCLE)
)

FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS = 2

DEVICES = len(ROLE_CYCLE) * FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS
# With 2 cycles: ENDPOINTS=10, RECEIVERS=2, REPEATER-type=14 (14 > 10 and 2 < 10).

COMM = 100       # communication radius
SIDE = int(math.isqrt(DEVICES * 3000)) + 1
HEIGHT = 80
SPEED = 8
NUM_ROUNDS = 50
MSG_INTERVAL = 10        # endpoints emit a new message every MSG_INTERVAL rounds

# Spawn process status codes — aliases of shared SPAWN_STATUS_* from _example_utils.
# Must match C++ fcpp::status enum values exactly.
STATUS_BORDER = SPAWN_STATUS_BORDER        # 0 — fcpp::status::border
STATUS_INTERNAL = SPAWN_STATUS_INTERNAL    # 1 — fcpp::status::internal
STATUS_TERMINATED = SPAWN_STATUS_TERMINATED  # 2 — fcpp::status::terminated_output


# ---------------------------------------------------------------------------
# State dataclass
# ---------------------------------------------------------------------------

@dataclass
class WorkerState:
    """
    Per-node state for the worker-role-assignment algorithm.

    role              — WorkerRole integer (0–7); see WorkerRole enum above
    dist_to_receiver  — BIS distance from this node to the nearest RECEIVER (role 1)
    routing_set_size  — role-dependent metric:
                          LIDAR (2), REPEATER (4) → count_hood() [coverage]
                          UNASSIGNED (0)          → 0            [passive]
                          all other roles         → len(sp_collection set)
    received_count    — distinct messages received (only meaningful at RECEIVER, role 1)
    active_procs      — spawn processes active at this node this round
    """
    role:              int = 0
    dist_to_receiver:  float = math.inf
    routing_set_size:  int = 0
    received_count:    int = 0
    active_procs:      int = 0


# ---------------------------------------------------------------------------
# Aggregate function — Python DSL (transpiles to C++)
# ---------------------------------------------------------------------------

@aggregate_function
class WorkerRoleAggregate:
    """
    Aggregate program: role-aware sensor swarm with spawn-based message routing.

    Steps 1–6 are shared network-wide operations that run at EVERY node each
    round.  Step 7 (match/case) performs only local, non-aggregate computation:
    it carries out each role's specific task (or a placeholder for it) and then
    assembles the returned state.

    Note on Python 3.10+ match/case:
        Case patterns use dotted-name value patterns — ``case WorkerRole.X.value:``
        chains (``a.b.c``) are always treated as value patterns in Python 3.10+,
        never as capture patterns, so Python evaluates the attribute chain and
        compares it to the subject.  Bare single-identifier names (``case X:``)
        would be capture patterns; that is why they are not used here.

    Note on self_uid():
        self_uid() returns ``node.uid`` in generated C++ (no CALL counter).
        In the Python DSL it returns 0 (placeholder); the demo simulation below
        uses the actual node ID directly via ``nid`` so logs remain correct.
    """

    def initial_state(self) -> WorkerState:
        """Default: UNASSIGNED role (0), distances unknown."""
        return WorkerState()

    def compute(
        self,
        self_state: WorkerState,
        neighbors: Neighborhood[WorkerState],
    ) -> WorkerState:
        """
        Round computation — 8 steps.

        Steps 1–7: shared primitives; every node calls them in the same order.
        Step 8:    role-specific task (local only) + state assembly.
        """
        role = self_state.role

        is_receiver = (role == WorkerRole.RECEIVER.value)
        is_endpoint = (
            role == WorkerRole.LIDAR.value
            or role == WorkerRole.INFRARED_SENSOR.value
            or role == WorkerRole.TORCHLIGHT_MICROPHONE.value
            or role == WorkerRole.RUBBLES_REMOVER.value
            or role == WorkerRole.FLYING_OVERSEER.value
        )

        # ── Step 1: BIS distance gradient rooted at RECEIVER nodes ───────────
        # C++: double d = bis_distance(CALL, is_receiver, 1, 100);
        dist_to_receiver = bis_distance(is_receiver, 1, 100)  # noqa: F821

        # ── Step 2: spanning-tree parent — nearest neighbor toward RECEIVER ──
        # C++: device_t parent = get<1>(
        #          min_hood(CALL, make_tuple(nbr(CALL, dist_to_receiver), node.uid)));
        # self_uid() → node.uid in C++ (no CALL counter; safe as tie-breaking key)
        nbr_dists = nbr(dist_to_receiver)                      # noqa: F821
        parent = min_hood((nbr_dists, self_uid()))          # noqa: F821

        # ── Step 3: local neighbor count ─────────────────────────────────────
        # C++: int nc = count_hood(CALL);
        # Used as "coverage" metric for WorkerRole.LIDAR and WorkerRole.REPEATER in step 7.
        neighbor_count = count_hood()                          # noqa: F821

        # ── Step 4: routing set — subtree of node UIDs "below" this node ─────
        # sp_collection propagates {self_uid()} sets upward toward the RECEIVER root.
        # In C++: self_uid() → node.uid; in Python: 0 (placeholder).
        routing_set = sp_collection(                           # noqa: F821
            dist_to_receiver,
            frozenset({self_uid()}),  # local value: {this device's UID}  # noqa: F821
            frozenset(),              # null value: empty set
            lambda x, y: x | y,      # accumulator: set union
        )

        # ── Step 5: broadcast — distribute nearest RECEIVER's UID ────────────
        # RECEIVER nodes are the roots (is_receiver=True); broadcast propagates
        # their self_uid() outward so every non-root node learns the nearest
        # RECEIVER's UID.  In C++: device_t receiver_uid = broadcast(CALL, is_receiver, node.uid)
        receiver_uid = broadcast(is_receiver, self_uid())      # noqa: F821

        # ── Step 6: spawn — endpoint messages routed toward RECEIVER ─────────
        # Key = (sender_uid, receiver_uid).
        #   sender_uid   → self_uid() (node.uid in C++)
        #   receiver_uid → broadcast result above (nearest RECEIVER's UID)
        # The lambda determines this node's routing status for each message:
        #   TERMINATED (2) — this node IS the RECEIVER (destination reached)
        #   INTERNAL   (1) — this node's subtree contains sender or receiver UID
        #   BORDER     (0) — this node is off-path; process does not run here
        new_msg = (self_uid(), receiver_uid) if is_endpoint else None  # noqa: F821

        active_messages = spawn(                               # noqa: F821
            lambda msg: (
                # payload (placeholder; C++: node.current_time())
                0,
                STATUS_TERMINATED if is_receiver                       # 2
                # 1
                else STATUS_INTERNAL if (msg[0] in routing_set or msg[1] in routing_set)
                else STATUS_BORDER,                                    # 0
            ),
            new_msg,
        )

        # ── Step 7: persist received-message log across rounds ────────────────
        # old() carries the map from the previous round; new entries are merged.
        received_log = old(                                    # noqa: F821
            {},
            lambda prev: {**prev, **active_messages},
        )

        # ── Step 8: role-specific task + state assembly (match/case → C++ switch) ──
        # The match/case in step 8 contains **only local expressions** (no primitive
        # calls) and is therefore safe to use as a per-role customization point.
        #
        # All aggregate values (dist_to_receiver, routing_set, etc.) were already
        # computed in steps 1–7.  Each case performs its role's specific task
        # (or a placeholder comment where the real implementation is not provided)
        # and then assembles the WorkerState to return.
        #
        # routing_set_size is repurposed per role:
        #   LIDAR, REPEATER         → neighbor_count  (coverage metric)
        #   UNASSIGNED              → 0               (passive, no contribution)
        #   all others              → len(routing_set) (subtree size)
        match role:
            case WorkerRole.UNASSIGNED.value:   # UNASSIGNED
                # No task assigned; node passively maintains distance info.
                # [Placeholder] Real implementation: await role assignment via
                # election or external configuration message.
                passive_dist = dist_to_receiver
                return WorkerState(
                    role=role,
                    dist_to_receiver=passive_dist,
                    routing_set_size=0,
                    received_count=0,
                    active_procs=0,
                )
            case WorkerRole.RECEIVER.value:   # RECEIVER
                # Accumulate all delivered endpoint reports into received_log.
                # [Placeholder] Real implementation: parse each message body,
                # tag it with arrival round, and forward to base-station storage.
                messages_received = len(received_log)
                return WorkerState(
                    role=role,
                    dist_to_receiver=0.0,
                    routing_set_size=len(routing_set),
                    received_count=messages_received,
                    active_procs=len(active_messages),
                )
            case WorkerRole.LIDAR.value:   # LIDAR
                # Endpoint: depth/distance sensor.
                # [Placeholder] Real implementation: capture depth-map frame,
                # fuse with neighbor LIDAR data, inject compressed scan into
                # the spawn message stream toward RECEIVER.
                scan_coverage = neighbor_count  # nodes within LiDAR scan range
                return WorkerState(
                    role=role,
                    dist_to_receiver=dist_to_receiver,
                    routing_set_size=scan_coverage,
                    received_count=0,
                    active_procs=len(active_messages),
                )
            case WorkerRole.INFRARED_SENSOR.value:   # INFRARED_SENSOR
                # Endpoint: heat-signature detector.
                # [Placeholder] Real implementation: sample thermal readings,
                # flag anomalies above threshold, and inject alert message into
                # spawn stream tagged with sensor position estimate.
                subtree_size = len(routing_set)  # routing coverage
                return WorkerState(
                    role=role,
                    dist_to_receiver=dist_to_receiver,
                    routing_set_size=subtree_size,
                    received_count=0,
                    active_procs=len(active_messages),
                )
            case WorkerRole.REPEATER.value:   # REPEATER
                # Repeater: signal amplifier and network range extender.
                # Acts as intermediary between endpoints (or other repeaters)
                # that are not in direct communication; may relay data
                # transitively across multiple hops.
                # [Placeholder] Real implementation: forward data frames from
                # neighboring nodes; log relay throughput for health monitoring.
                relay_coverage = neighbor_count  # nodes reachable through this repeater
                return WorkerState(
                    role=role,
                    dist_to_receiver=dist_to_receiver,
                    routing_set_size=relay_coverage,
                    received_count=0,
                    active_procs=len(active_messages),
                )
            case WorkerRole.TORCHLIGHT_MICROPHONE.value:   # TORCHLIGHT_MICROPHONE
                # Endpoint: combined audio + illumination sensor.
                # [Placeholder] Real implementation: capture audio sample and
                # ambient light reading; bundle into a single sensor report and
                # inject into spawn stream toward RECEIVER.
                subtree_size = len(routing_set)  # routing coverage
                return WorkerState(
                    role=role,
                    dist_to_receiver=dist_to_receiver,
                    routing_set_size=subtree_size,
                    received_count=0,
                    active_procs=len(active_messages),
                )
            case WorkerRole.RUBBLES_REMOVER.value:   # RUBBLES_REMOVER
                # Endpoint: physical debris-clearing robot.
                # Gathers environmental sensor data (debris status, path availability)L
                # and injects a clearing-status report into the spawn stream toward
                # RECEIVER.
                # [Placeholder] Real implementation: sample debris sensor; encode
                # clearing status and path availability into the message payload.
                debris_coverage = len(routing_set)
                return WorkerState(
                    role=role,
                    dist_to_receiver=dist_to_receiver,
                    routing_set_size=debris_coverage,
                    received_count=0,
                    active_procs=len(active_messages),
                )
            case WorkerRole.FLYING_OVERSEER.value:   # FLYING_OVERSEER
                # Endpoint: aerial survey drone.
                # [Placeholder] Real implementation: transmit aerial survey
                # frame (top-down image + GPS coordinates) and update the
                # swarm-wide coverage map broadcast by the RECEIVER.
                # nodes visible from aerial position
                survey_footprint = len(routing_set)
                return WorkerState(
                    role=role,
                    dist_to_receiver=dist_to_receiver,
                    routing_set_size=survey_footprint,
                    received_count=0,
                    active_procs=len(active_messages),
                )


# ---------------------------------------------------------------------------
# AbstractExample subclass — toolchain bridge
# ---------------------------------------------------------------------------

class WorkerRoleExample(AbstractExample):
    """Runs WorkerRoleAggregate through the full toolchain.

    Validates, transpiles, compiles (SHA-256 cached), and runs the C++ binary.
    State updates arrive via IPC; per-node log files are written from snapshots.

    An extra per-simulation log (receiver_messages.log) is opened in
    on_simulation_start() and closed in on_simulation_end(). Its content
    (RECEIVER node received_count per round) is written in on_round_complete().
    """

    def __init__(self, seed: int = 17):
        self._rng = random.Random(seed)
        self._recv_log = None
        self._last_snapshot = None

    @property
    def aggregate_class(self):
        return WorkerRoleAggregate

    @property
    def log_prefix(self) -> str:
        return "worker_role"

    def initial_positions(self) -> dict:
        return {
            nid: (self._rng.uniform(0.0, SIDE), self._rng.uniform(0.0, SIDE))
            for nid in range(DEVICES)
        }

    def on_simulation_start(self) -> None:
        recv_log_path = self.log_dir / "receiver_messages.log"
        self._recv_log = open(recv_log_path, "w")  # noqa: SIM115
        self._recv_log.write(
            "# Worker Role Assignment — receiver message log (toolchain)\n"
            "# round,receiver_node,received_count\n"
        )

    def log_header(self, node_id: int, state_data: Any) -> str:
        d = state_data if isinstance(state_data, dict) else vars(state_data)
        try:
            role_name = WorkerRole(d.get('role', 0)).name
        except (ValueError, KeyError):
            role_name = "UNKNOWN"
        return (
            f"# Worker Role Assignment — node {node_id} ({role_name})\n"
            "# round,role,dist_to_receiver,routing_set_size,"
            "received_count,active_procs\n"
        )

    def log_line(self, round_num: int, node_id: int, state_data: Any) -> str:
        d = state_data if isinstance(state_data, dict) else vars(state_data)
        return (
            f"{round_num},{d.get('role', 0)},{d.get('dist_to_receiver', 0.0):.4f},"
            f"{d.get('routing_set_size', 0)},"
            f"{d.get('received_count', 0)},{d.get('active_procs', 0)}\n"
        )

    def on_round_complete(self, round_num: int, snapshot) -> None:
        self._last_snapshot = snapshot
        if snapshot is None or self._recv_log is None:
            return
        for ns in snapshot.nodes:
            d = ns.state_data if isinstance(ns.state_data, dict) else vars(ns.state_data)
            if d.get('role') == WorkerRole.RECEIVER.value:
                self._recv_log.write(
                    f"{round_num},{ns.node_id},{d.get('received_count', 0)}\n"
                )

    def on_simulation_end(self) -> None:
        if self._recv_log:
            self._recv_log.close()
            self._recv_log = None
        snap = self._last_snapshot
        receiver_counts = {}
        if snap and snap.nodes:
            for ns in snap.nodes:
                d = ns.state_data if isinstance(ns.state_data, dict) else vars(ns.state_data)
                if d.get('role') == WorkerRole.RECEIVER.value:
                    receiver_counts[ns.node_id] = d.get('received_count', 0)
        total_msgs = sum(receiver_counts.values())
        print(
            f"    Wrote {DEVICES} node logs + receiver_messages.log → {self.log_dir}/")
        print(f"    Total messages received by RECEIVER nodes: {total_msgs}")
        for recv_nid in sorted(receiver_counts):
            print(
                f"    RECEIVER node {recv_nid:2d}: "
                f"{receiver_counts[recv_nid]} messages received"
            )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("\n" + "=" * 70)
    print("FCPP Bridge — Worker Role Assignment Example")
    print("Demonstrates: match/case (switch) + spawn message routing + self_uid()")
    print("=" * 70 + "\n")

    print("[1/3] Validating Python DSL...")
    try:
        report_validation(WorkerRoleAggregate)
    except Exception as exc:
        print(f"    FAIL: {exc}")
        return

    print("\n[2/3] Transpiling to C++...")
    report_transpilation(WorkerRoleAggregate)

    print(
        f"\n[3/3] Running demo simulation "
        f"({DEVICES} nodes, {NUM_ROUNDS} rounds, MSG_INTERVAL={MSG_INTERVAL})..."
    )
    role_summary = ", ".join(
        f"{WorkerRole(r).name}×{sum(1 for nid in range(DEVICES) if ROLE_CYCLE[nid % len(ROLE_CYCLE)] == r)}"
        for r in range(8)
    )
    print(f"    Role distribution: {role_summary}")
    WorkerRoleExample().run(NUM_ROUNDS)

    print("\nAlgorithm summary (7 steps — all run at every node):")
    print("  1. bis_distance     — gradient distance to nearest RECEIVER (WorkerRole.RECEIVER)")
    print("  2. nbr + min_hood   — spanning-tree parent (self_uid() as tie-breaker)")
    print("  3. count_hood       — local neighbor count (coverage metric)")
    print(
        "  4. sp_collection    — routing subtree: {self_uid()} sets per node")
    print("  5. spawn            — route endpoint sensor-reading messages")
    print("       key = (self_uid(), receiver_uid=0_placeholder)")
    print("       status = TERMINATED (2) | INTERNAL (1) | BORDER (0)")
    print("  6. old              — persist received-message map across rounds")
    print("  7. match/case       — role-specific task + state assembly (no primitives)")
    print()
    print("WorkerRole switch cases:")
    for r in WorkerRole:
        comm_type = ROLE_COMM_TYPE[r]
        tag = f"({comm_type.name.lower()})"
        print(f"  case {r.value}: {r.name:<24s} {tag}")
    print()
    print("RoleCommunicationType — communication role in the data-gathering flow:")
    for ct in RoleCommunicationType:
        roles_with = [r for r in WorkerRole if ROLE_COMM_TYPE[r] == ct]
        role_str = ", ".join(f"{r.name}({r.value})" for r in roles_with)
        print(f"  {ct.name:<10s}({ct.value}): {role_str}")
    print()
    print("New in v1.6 — self_uid() primitive:")
    print("  Python DSL:  self_uid()  → 0 (placeholder)")
    print("  Generated C++: self_uid() → node.uid")
    print("  CALL-counter: NOT incremented (safe inside match/case branches)")
    print()
    print("Primitives used:")
    print("  basics.hpp     : nbr, count_hood, spawn, old")
    print("  utils.hpp      : min_hood")
    print("  spreading.hpp  : bis_distance")
    print("  collection.hpp : sp_collection")
    print("  (node API)     : self_uid() → node.uid  [no CALL]")
    print()


if __name__ == "__main__":
    main()
