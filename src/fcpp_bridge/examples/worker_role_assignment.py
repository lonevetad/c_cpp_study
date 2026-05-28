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

Role assignment: ``node_id % 8`` — with DEVICES = 24, each role appears 3 times.

Algorithm per round (all 7 steps execute at EVERY node):
  1. bis_distance    — distance gradient rooted at RECEIVER nodes
  2. nbr + min_hood  — spanning-tree parent toward nearest RECEIVER
  3. count_hood      — local neighbor count (used by LIDAR and REPEATER)
  4. sp_collection   — routing subtree ("below" set) for each node
  5. spawn           — route endpoint messages toward RECEIVER
  6. old             — persist received-message log across rounds
  7. match/case      — role-specific task + state assembly (no primitives inside cases)

Note on FCPP primitive ordering:
    All aggregate primitives (steps 1–6) are called outside the switch so that
    every node increments the internal CALL counter in the same order.  Only
    pure local computations (no nbr/old/spawn calls) appear inside case branches.

Note on self_uid():
    self_uid() returns ``node.uid`` in generated C++ (no CALL counter).
    In the Python DSL layer it returns 0 (placeholder), so the demo simulation
    below uses the real ``nid`` directly rather than calling compute().

Log files written to examples/logs/:
    node_<id>_worker_role.log  — per-node per-round stats
    receiver_messages.log      — messages delivered to any RECEIVER node
"""

import math
import random
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

from fcpp_bridge.python_dsl import aggregate_function, Neighborhood
from examples._example_utils import report_validation, report_transpilation


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
    **ENDPOINT_ROLES,
    WorkerRole.RECEIVER:              RoleCommunicationType.RECEIVER,   # 1 → 1
    **REPEATER_ROLES
}


# ---------------------------------------------------------------------------
# Simulation constants
# ---------------------------------------------------------------------------

DEVICES = 24        # 3 full repetitions of all 8 roles
COMM = 100       # communication radius
SIDE = int(math.isqrt(DEVICES * 3000)) + 1
HEIGHT = 80
SPEED = 8
NUM_ROUNDS = 50
MSG_INTERVAL = 10        # endpoints emit a new message every MSG_INTERVAL rounds

LOG_DIR = Path(__file__).parent / "logs"

# Spawn process status codes — same convention as message_dispatch.py
# Must match C++ fcpp::status enum values exactly:
STATUS_BORDER = 0   # 0 — fcpp::status::border     (node is off routing path)
STATUS_INTERNAL = 1   # 1 — fcpp::status::internal   (node is actively routing)
# 2 — fcpp::status::terminated_output (message reached destination)
STATUS_TERMINATED = 2


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
        Case patterns must be integer literals (``case 0:``, ``case 1:``, …)
        so that Python correctly treats them as value patterns, not capture
        patterns.  Bare module-level names (e.g. ``case RECEIVER:``) would
        create a new binding regardless of the existing variable's value.

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
        Round computation — 7 steps.

        Steps 1–6: shared primitives; every node calls them in the same order.
        Step 7:    role-specific task (local only) + state assembly.
        """
        role = self_state.role

        is_receiver = (role == 1)   # WorkerRole.RECEIVER = 1
        is_endpoint = (
            role == 2               # WorkerRole.LIDAR = 2
            or role == 3            # WorkerRole.INFRARED_SENSOR = 3
            or role == 5            # WorkerRole.TORCHLIGHT_MICROPHONE = 5
            or role == 6            # WorkerRole.RUBBLES_REMOVER = 6
            or role == 7            # WorkerRole.FLYING_OVERSEER = 7
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
        # Used as "coverage" metric for LIDAR (2) and REPEATER (4) in step 7.
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

        # ── Step 5: spawn — endpoint messages routed toward RECEIVER ─────────
        # Key = (sender_uid, receiver_uid).  sender_uid: self_uid() → node.uid.
        # receiver_uid is still 0 (placeholder; requires broadcast from RECEIVER).
        # The lambda determines this node's routing status for each message:
        #   TERMINATED (2) — this node IS the RECEIVER (destination reached)
        #   INTERNAL   (1) — this node's subtree contains sender or receiver UID
        #   BORDER     (0) — this node is off-path; process does not run here
        new_msg = (self_uid(), 0) if is_endpoint else None     # noqa: F821

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

        # ── Step 6: persist received-message log across rounds ────────────────
        # old() carries the map from the previous round; new entries are merged.
        received_log = old(                                    # noqa: F821
            {},
            lambda prev: {**prev, **active_messages},
        )

        # ── Step 7: role-specific task + state assembly (match/case → C++ switch) ──
        # The match/case in step 7 contains **only local expressions** (no primitive
        # calls) and is therefore safe to use as a per-role customization point.
        #
        # All aggregate values (dist_to_receiver, routing_set, etc.) were already
        # computed in steps 1–6.  Each case performs its role's specific task
        # (or a placeholder comment where the real implementation is not provided)
        # and then assembles the WorkerState to return.
        #
        # routing_set_size is repurposed per role:
        #   LIDAR (2), REPEATER (4) → neighbor_count  (coverage metric)
        #   UNASSIGNED (0)          → 0               (passive, no contribution)
        #   all others              → len(routing_set) (subtree size)
        match role:
            case 0:   # UNASSIGNED (WorkerRole.UNASSIGNED = 0)
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
            case 1:   # RECEIVER (WorkerRole.RECEIVER = 1)
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
            case 2:   # LIDAR (WorkerRole.LIDAR = 2)
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
            case 3:   # INFRARED_SENSOR (WorkerRole.INFRARED_SENSOR = 3)
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
            case 4:   # REPEATER (WorkerRole.REPEATER = 4)
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
            # TORCHLIGHT_MICROPHONE (WorkerRole.TORCHLIGHT_MICROPHONE = 5)
            case 5:
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
            case 6:   # RUBBLES_REMOVER (WorkerRole.RUBBLES_REMOVER = 6)
                # Endpoint: physical debris-clearing robot.
                # Gathers environmental sensor data (debris status, path availability)
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
            case _:   # 7 — FLYING_OVERSEER (WorkerRole.FLYING_OVERSEER = 7)
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
# Pure-Python demo simulation
# ---------------------------------------------------------------------------

def _demo_simulate() -> None:
    """
    Pure-Python approximation of the worker-role-assignment algorithm.

    Implements the same 7 steps as compute() for log generation without a
    C++ compiler.  Messages are routed along a spanning tree toward the
    nearest RECEIVER node.

    Message delivery model:
        A message injected at round R by endpoint E takes
        ``ceil(distances[E] / COMM) + 1`` rounds to travel to a RECEIVER.
        While in-flight the message contributes to active_procs for every
        node whose routing subtree contains either the sender or a receiver.

    Note: the demo uses the real ``nid`` as node UID (self_uid() placeholder
    is 0 in the DSL layer, but the demo simulation has direct access to nid).
    """
    random.seed(17)

    roles = {nid: nid % 8 for nid in range(DEVICES)}
    positions = {
        nid: (random.uniform(0.0, SIDE), random.uniform(0.0, SIDE))
        for nid in range(DEVICES)
    }
    distances = {nid: math.inf for nid in range(DEVICES)}
    routing_sets = {nid: frozenset({nid}) for nid in range(DEVICES)}

    receiver_ids = frozenset(
        nid for nid, r in roles.items() if r == WorkerRole.RECEIVER)
    endpoint_ids = frozenset(
        nid for nid, r in roles.items() if r in ENDPOINT_ROLES)

    # in_flight: (sender_nid, interval_index) → (msg_body, rounds_remaining)
    in_flight: dict = {}
    total_delivered = {nid: 0 for nid in range(DEVICES)}
    log_files: dict = {}

    def neighbors_of(nid: int) -> list:
        x, y = positions[nid]
        return [
            j for j in range(DEVICES)
            if j != nid and math.dist((x, y), positions[j]) <= COMM
        ]

    def _bis_distance(is_endpoint: bool, nbr_dists: list) -> float:
        if is_endpoint:
            return 0.0
        if not nbr_dists:
            return math.inf
        return min(nbr_dists) + COMM * 0.1   # simplified unit cost per hop

    LOG_DIR.mkdir(exist_ok=True)
    recv_log_path = LOG_DIR / "receiver_messages.log"
    recv_log = open(recv_log_path, "w")  # noqa: SIM115 — closed below
    recv_log.write(
        "# Worker Role Assignment — receiver message log\n"
        "# round,receiver_node,sender_node,sender_role,rounds_in_flight,message_body\n"
    )

    for round_num in range(NUM_ROUNDS):
        # ── Move nodes ───────────────────────────────────────────────────────
        for nid in range(DEVICES):
            x, y = positions[nid]
            positions[nid] = (
                max(0.0, min(SIDE, x + random.uniform(-SPEED, SPEED))),
                max(0.0, min(SIDE, y + random.uniform(-SPEED, SPEED))),
            )

        # ── Step 1: BIS distances toward RECEIVER ────────────────────────────
        new_distances = {}
        for nid in range(DEVICES):
            is_recv = (roles[nid] == WorkerRole.RECEIVER)  # role 1
            nbrs = neighbors_of(nid)
            nbr_dists = [
                distances[n] for n in nbrs if math.isfinite(distances[n])
            ]
            new_distances[nid] = _bis_distance(is_recv, nbr_dists)
        distances = new_distances

        # ── Step 2: spanning-tree parents (uses real nid as UID) ─────────────
        parents: dict = {}
        for nid in range(DEVICES):
            if roles[nid] == WorkerRole.RECEIVER:  # role 1
                parents[nid] = -1
                continue
            nbrs = neighbors_of(nid)
            if not nbrs:
                parents[nid] = -1
                continue
            # nid as tie-breaker
            best = min(nbrs, key=lambda n: (distances[n], n))
            parents[nid] = best if distances[best] < distances[nid] else -1

        # ── Step 3: neighbor counts ───────────────────────────────────────────
        neighbor_counts = {nid: len(neighbors_of(nid))
                           for nid in range(DEVICES)}

        # ── Step 4: routing sets (iterative convergence; uses real nid as UID) ─
        routing_sets = {nid: frozenset({nid}) for nid in range(DEVICES)}
        for _ in range(8):
            new_rs: dict = {}
            for nid in range(DEVICES):
                children = [
                    n for n in neighbors_of(nid) if parents.get(n) == nid
                ]
                new_rs[nid] = (
                    frozenset({nid}).union(
                        *(routing_sets[c] for c in children))
                    if children
                    else frozenset({nid})
                )
            routing_sets = new_rs

        # ── Step 5: inject new messages from endpoints every MSG_INTERVAL ────
        if round_num > 0 and round_num % MSG_INTERVAL == 0:
            interval_idx = round_num // MSG_INTERVAL
            for nid in endpoint_ids:
                msg_key = (nid, interval_idx)  # (sender_uid, interval_index)
                if msg_key not in in_flight and math.isfinite(distances[nid]):
                    role_name = WorkerRole(roles[nid]).name
                    sensor_reading = round(random.uniform(0.0, 100.0), 2)
                    msg_body = (
                        f"[node {nid} / {role_name}]"
                        f" sensor_reading={sensor_reading}"
                    )
                    hops_est = max(1, math.ceil(distances[nid] / COMM) + 1)
                    in_flight[msg_key] = (msg_body, hops_est)

        # ── Step 5 (cont.): advance in-flight messages; deliver on expiry ────
        delivered_this_round: list = []
        for msg_key, (msg_body, rounds_left) in list(in_flight.items()):
            sender_nid = msg_key[0]
            if rounds_left <= 1:
                # Deliver to all reachable receivers
                for recv_nid in sorted(receiver_ids):
                    if math.isfinite(distances[sender_nid]):
                        total_delivered[recv_nid] += 1
                        original_hops = max(1, math.ceil(
                            distances[sender_nid] / COMM) + 1)
                        recv_log.write(
                            f"{round_num},{recv_nid},{sender_nid},"
                            f"{WorkerRole(roles[sender_nid]).name},"
                            f"{original_hops},{msg_body}\n"
                        )
                delivered_this_round.append(msg_key)
            else:
                in_flight[msg_key] = (msg_body, rounds_left - 1)
        for mk in delivered_this_round:
            del in_flight[mk]

        # ── Active process count per node (messages currently in-flight) ──────
        active_procs = {nid: 0 for nid in range(DEVICES)}
        for (sender_nid, _), _ in in_flight.items():
            for nid in range(DEVICES):
                rs = routing_sets[nid]
                if sender_nid in rs or any(r in rs for r in receiver_ids):
                    active_procs[nid] += 1

        # ── Write per-node log entries ────────────────────────────────────────
        for nid in range(DEVICES):
            role = roles[nid]
            role_name = WorkerRole(role).name
            dist = distances[nid]

            # routing_set_size: role-dependent metric (mirrors match/case step 7)
            if role in (WorkerRole.LIDAR, WorkerRole.REPEATER):  # roles 2 and 4
                rs_size = neighbor_counts[nid]
            elif role == WorkerRole.UNASSIGNED:  # role 0
                rs_size = 0
            else:
                rs_size = len(routing_sets[nid])

            recv_count = (
                # role 1
                total_delivered[nid] if role == WorkerRole.RECEIVER else 0
            )

            if nid not in log_files:
                log_path = LOG_DIR / f"node_{nid}_worker_role.log"
                lf = open(log_path, "w")  # noqa: SIM115 — closed below
                lf.write(
                    f"# Worker Role Assignment — node {nid} ({role_name})\n"
                    "# round,dist_to_receiver,routing_set_size,"
                    "received_count,active_procs\n"
                )
                log_files[nid] = lf

            log_files[nid].write(
                f"{round_num},{dist:.4f},{rs_size},"
                f"{recv_count},{active_procs[nid]}\n"
            )

    for lf in log_files.values():
        lf.close()
    recv_log.close()

    total_msgs = sum(total_delivered.values())
    print(
        f"    Wrote {DEVICES} node logs + receiver_messages.log → {LOG_DIR}/")
    print(f"    Messages still in flight at end:  {len(in_flight)}")
    print(f"    Total messages delivered to receiver(s): {total_msgs}")
    for recv_nid in sorted(receiver_ids):
        print(
            f"    RECEIVER node {recv_nid:2d}: "
            f"{total_delivered[recv_nid]} messages received"
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
        f"{WorkerRole(r).name}×{sum(1 for nid in range(DEVICES) if nid % 8 == r)}"
        for r in range(8)
    )
    print(f"    Role distribution: {role_summary}")
    _demo_simulate()

    print("\nAlgorithm summary (7 steps — all run at every node):")
    print("  1. bis_distance     — gradient distance to nearest RECEIVER (role 1)")
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
        print(f"  case {int(r):d}: {r.name:<24s} {tag}")
    print()
    print("RoleCommunicationType — communication role in the data-gathering flow:")
    for ct in RoleCommunicationType:
        roles_with = [r for r in WorkerRole if ROLE_COMM_TYPE[r] == ct]
        role_str = ", ".join(f"{r.name}({int(r)})" for r in roles_with)
        print(f"  {ct.name:<10s}({int(ct)}): {role_str}")
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
