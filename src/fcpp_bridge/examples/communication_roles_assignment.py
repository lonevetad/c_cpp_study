"""
Communication Roles Assignment — fcpp_bridge DSL example.

Demonstrates a distributed algorithm in which a static node swarm negotiates
communication roles (Sender / Repeater / Receiver) based on proximity to
pre-placed "source points" and "sink points".

Demonstrates:
  1. ``bis_distance`` ×2 — gradient from Receivers AND from Senders
  2. ``nbr`` + ``min_hood`` — distributed Sender-election (closest node wins)
  3. ``old`` ×2 — round counter (for periodic message creation) and received-log
  4. ``broadcast`` — propagate each Sender's message outward to all nodes
  5. ``match/case`` (→ C++ ``switch``) — per-role behavioural dispatch
  6. ``self_uid()`` — node's own UID (tie-breaker in election, message tag)

Requires Python 3.10+ (``match/case`` statement).

CommunicationRole values (stored in CommRoleState.role):
    0 = UNASSIGNED   default until role is resolved
    1 = SENDER       nearest node to a source point; injects messages
    2 = REPEATER     middle relay; forwards broadcast messages
    3 = RECEIVER     nearest node to a sink point; consumes messages

Algorithm (per round — all steps run at EVERY node):
  Step 1: bis_distance rooted at Receivers → gradient toward Receivers
  Step 2: bis_distance rooted at Senders   → gradient away from Senders
  Step 3: nbr(dist_to_nearest_source) + min_hood — Sender election
          (node with smallest source-distance wins; self_uid() breaks ties)
  Step 4: old(0, lambda t: t+1) — round counter
  Step 5: broadcast(dist_from_sender, msg_payload)
          propagates each Sender's latest message outward to all nodes
  Step 6: old({}, ...) — accumulate received messages at Receivers
  Step 7: match/case — per-role task + state assembly (no primitives inside cases)

Note on primitive ordering:
    All six primitive calls (steps 1–6) execute at EVERY node each round in
    the same order.  Only local expressions appear inside the match/case block.

Note on self_uid():
    Returns ``node.uid`` in generated C++ (no CALL counter).
    In the Python DSL it returns 0 (placeholder); the demo simulation uses the
    real ``nid`` directly.

Note on role stability:
    Roles are determined once (in _setup_network) and stored as initial state.
    The aggregate compute() reads them from self_state.role — they never change
    because sink/source points are fixed.  The match/case therefore acts as a
    permanent routing configuration, not a dynamic election.

Note on role assignment in toolchain mode:
    The C++ binary uses initial_state() → CommRoleState() (UNASSIGNED) for all
    nodes, since _setup_network() role assignment cannot be passed to the binary
    via the current IPC interface.  Role-specific behaviour will only execute
    correctly once role injection is added to the IPC protocol.

Running:
    CommunicationRolesExample().run(NUM_ROUNDS) invokes the full toolchain:
    validate → transpile → compile → SwarmProcess → per-node logs.
    A C++ compiler and FCPP headers are required.

Log files written to examples/logs/:
    node_<id>_comm_roles.log   — per-node per-round stats
    comm_receiver_messages.log — RECEIVER node received_log_size per round
"""

import logging
import math
import random
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple

from fcpp_bridge.python_dsl import aggregate_function, Neighborhood
from fcpp_bridge.examples._example_utils import (
    neighbors_of,
    SPAWN_STATUS_BORDER,
    SPAWN_STATUS_INTERNAL,
    SPAWN_STATUS_TERMINATED,
    report_validation,
    report_transpilation,
)
from fcpp_bridge.examples.abstract_example import AbstractExample

# ---------------------------------------------------------------------------
# CommunicationRole enum
# ---------------------------------------------------------------------------

class CommunicationRole(IntEnum):
    UNASSIGNED = 0  # default before role convergence
    SENDER     = 1  # nearest node to a source point; injects messages
    REPEATER   = 2  # relay node; forwards messages along the broadcast field
    RECEIVER   = 3  # nearest node to a sink point; consumes messages


# ---------------------------------------------------------------------------
# Simulation constants
# ---------------------------------------------------------------------------

NODES = 15              # total number of nodes in the swarm
SINK_POINTS = 2         # number of sink points (attract Receivers)
SOURCE_POINTS = 3       # number of source points (attract Senders)
COMM = 100.0            # communication radius (units)
SIDE = int(math.isqrt(NODES * 3000)) + 1  # deployment area side ≈ sqrt(nodes*3000)
NUM_ROUNDS = 60         # simulation rounds
MSG_TICKS_INTERVAL = 10  # Sender emits a new message every N rounds

ISOLATION_THRESHOLD = 0.20   # max fraction of isolated nodes allowed
MAX_MIGRATION_ITERS = 50     # max migration passes before accepting the network
MAX_POINT_PLACEMENT_ITERS = 10  # max retries per sink/source point placement

# Spawn status aliases (kept for clarity in DSL code; values from _example_utils)
STATUS_BORDER     = SPAWN_STATUS_BORDER
STATUS_INTERNAL   = SPAWN_STATUS_INTERNAL
STATUS_TERMINATED = SPAWN_STATUS_TERMINATED


# ---------------------------------------------------------------------------
# State dataclass
# ---------------------------------------------------------------------------

@dataclass
class CommRoleState:
    """
    Per-node state for the communication-roles-assignment algorithm.

    role                  — CommunicationRole integer (0–3)
    dist_to_nearest_sink  — pre-computed Euclidean distance to the nearest sink point
    dist_to_nearest_source— pre-computed Euclidean distance to the nearest source point
    dist_to_receiver      — bis_distance gradient toward Receiver nodes (step 1)
    dist_from_sender      — bis_distance gradient from Sender nodes (step 2)
    round_tick            — monotonically increasing round counter via old (step 4)
    msg_payload           — most recent message this node carries (Sender or relayed)
    received_log_size     — distinct messages received (only meaningful at RECEIVER)
    """
    role:                   int   = CommunicationRole.UNASSIGNED.value
    dist_to_nearest_sink:   float = math.inf
    dist_to_nearest_source: float = math.inf
    dist_to_receiver:       float = math.inf
    dist_from_sender:       float = math.inf
    round_tick:             int   = 0
    msg_payload:            object = None
    received_log_size:      int   = 0


# ---------------------------------------------------------------------------
# Aggregate function — Python DSL (transpiles to C++)
# ---------------------------------------------------------------------------

@aggregate_function
class CommunicationRolesAggregate:
    """
    Aggregate program: distributed communication-role assignment + message flow.

    Roles are fixed (set externally from the setup phase and stored in
    self_state.role).  The aggregate algorithm's job is to:
      a) compute routing gradients so Senders can reach Receivers;
      b) propagate messages from Senders through Repeaters to Receivers;
      c) accumulate received messages at Receivers via old.

    Note on Python 3.10+ match/case:
        Case labels use dotted value patterns (``CommunicationRole.X.value``),
        which are always treated as value patterns in Python 3.10+, never as
        capture patterns.

    Note on self_uid():
        Returns ``node.uid`` in generated C++ (no CALL counter increment).
        In the Python DSL layer it returns 0 (placeholder).
    """

    def initial_state(self) -> CommRoleState:
        """Default state: UNASSIGNED role, unknown distances."""
        return CommRoleState()

    def compute(
        self,
        self_state: CommRoleState,
        neighbors: Neighborhood[CommRoleState],
    ) -> CommRoleState:
        """
        Round computation — 7 steps.

        Steps 1–6: shared aggregate primitives; every node calls them in order.
        Step 7:    role-specific local task + state assembly (no primitives inside).
        """
        role = self_state.role
        is_receiver = (role == CommunicationRole.RECEIVER.value)
        is_sender   = (role == CommunicationRole.SENDER.value)

        # ── Step 1: BIS distance gradient toward Receivers ────────────────────
        # C++: double d_recv = bis_distance(CALL, is_receiver, 1, COMM);
        # Gives each node its hop-weighted distance to the nearest Receiver.
        dist_to_receiver = bis_distance(is_receiver, 1, COMM)  # noqa: F821

        # ── Step 2: BIS distance gradient away from Senders ───────────────────
        # C++: double d_send = bis_distance(CALL, is_sender, 1, COMM);
        # Gives each node its hop-weighted distance to the nearest Sender.
        # Used as the routing field for broadcast in step 5.
        dist_from_sender = bis_distance(is_sender, 1, COMM)   # noqa: F821

        # ── Step 3: Sender election via nbr + min_hood ────────────────────────
        # Among nodes near the same source point, the one with the smallest
        # (source-distance, uid) pair wins the Sender election.
        # C++: auto [win_dist, win_uid] = min_hood(CALL,
        #          make_tuple(nbr(CALL, dist_to_nearest_source), node.uid));
        # self_uid() → node.uid in C++ (no CALL counter; safe as tie-breaker)
        nbr_source_dists = nbr(self_state.dist_to_nearest_source)  # noqa: F821
        election_winner = min_hood((nbr_source_dists, self_uid()))  # noqa: F821
        # A node is the election winner if its own (distance, uid) pair is the minimum.
        # (In Python DSL: self_uid() returns 0, so election logic is symbolic here;
        #  the demo simulation uses real node IDs for correctness.)

        # ── Step 4: Round counter ─────────────────────────────────────────────
        # C++: int tick = old(CALL, 0, [](int t){ return t+1; });
        round_tick = old(0, lambda t: t + 1)  # noqa: F821

        # ── Step 5: Broadcast message from each Sender ────────────────────────
        # Senders inject a new message every MSG_TICKS_INTERVAL rounds.
        # broadcast(dist_from_sender, payload) propagates each Sender's payload
        # outward along the sender-gradient to all nodes (including Receivers).
        # Repeaters do not need to relay explicitly — broadcast handles it.
        should_send = is_sender and (round_tick % MSG_TICKS_INTERVAL == 0)
        # Message payload: (sender_uid, tick, dist_to_nearest_source) — dummy data.
        sender_payload = (
            (self_uid(), round_tick, self_state.dist_to_nearest_source)  # noqa: F821
            if should_send
            else self_state.msg_payload
        )
        incoming_msg = broadcast(dist_from_sender, sender_payload)  # noqa: F821

        # ── Step 6: Receiver accumulates messages via old ─────────────────────
        # C++: auto log = old(CALL, {}, [](auto prev){...});
        # The log maps (sender_uid, tick) → message payload for deduplication.
        received_log = old(  # noqa: F821
            {},
            lambda prev: (
                {**prev, (incoming_msg[0], incoming_msg[1]): incoming_msg}
                if (is_receiver and incoming_msg is not None)
                else prev
            ),
        )

        # ── Step 7: per-role task + state assembly (match/case → C++ switch) ──
        # Only local expressions here — no aggregate primitive calls.
        match role:
            case CommunicationRole.SENDER.value:
                # Inject a new message every MSG_TICKS_INTERVAL rounds and track count.
                # [Placeholder] Real: encode actual sensor or data payload.
                return CommRoleState(
                    role=role,
                    dist_to_nearest_sink=self_state.dist_to_nearest_sink,
                    dist_to_nearest_source=self_state.dist_to_nearest_source,
                    dist_to_receiver=dist_to_receiver,
                    dist_from_sender=0.0,
                    round_tick=round_tick,
                    msg_payload=sender_payload,
                    received_log_size=0,
                )
            case CommunicationRole.RECEIVER.value:
                # Consume messages from incoming_msg; log arrival for reporting.
                # [Placeholder] Real: parse payload, acknowledge, forward to storage.
                return CommRoleState(
                    role=role,
                    dist_to_nearest_sink=self_state.dist_to_nearest_sink,
                    dist_to_nearest_source=self_state.dist_to_nearest_source,
                    dist_to_receiver=0.0,
                    dist_from_sender=dist_from_sender,
                    round_tick=round_tick,
                    msg_payload=incoming_msg,
                    received_log_size=len(received_log),
                )
            case CommunicationRole.REPEATER.value:
                # Relay the broadcast message toward Receivers.
                # broadcast() already handles propagation; this case just carries
                # the current payload in state for logging / debugging purposes.
                # [Placeholder] Real: implement store-and-forward or TTL logic.
                return CommRoleState(
                    role=role,
                    dist_to_nearest_sink=self_state.dist_to_nearest_sink,
                    dist_to_nearest_source=self_state.dist_to_nearest_source,
                    dist_to_receiver=dist_to_receiver,
                    dist_from_sender=dist_from_sender,
                    round_tick=round_tick,
                    msg_payload=incoming_msg,
                    received_log_size=0,
                )
            case _:   # CommunicationRole.UNASSIGNED
                # Passive node: maintains gradient info but neither sends nor receives.
                return CommRoleState(
                    role=role,
                    dist_to_nearest_sink=self_state.dist_to_nearest_sink,
                    dist_to_nearest_source=self_state.dist_to_nearest_source,
                    dist_to_receiver=dist_to_receiver,
                    dist_from_sender=dist_from_sender,
                    round_tick=round_tick,
                    msg_payload=None,
                    received_log_size=0,
                )


# ---------------------------------------------------------------------------
# Setup helpers — pure Python (NOT aggregate functions)
# ---------------------------------------------------------------------------

def _count_isolated(positions: Dict[int, Tuple[float, float]], comm: float) -> List[int]:
    """Return list of node IDs with no neighbors within *comm* (equivalent to nbr_count()=1)."""
    return [nid for nid in positions if len(neighbors_of(positions, nid, comm)) == 0]


def _build_and_migrate_network(
    n: int,
    side: float,
    comm: float,
    isolation_threshold: float,
    max_iters: int,
    rng: random.Random,
) -> Dict[int, Tuple[float, float]]:
    """
    Build a random node deployment and migrate isolated nodes until the fraction
    of isolated nodes is below *isolation_threshold*, or *max_iters* is reached.

    Returns the final positions dict {nid: (x, y)}.
    """
    positions = {i: (rng.uniform(0.0, side), rng.uniform(0.0, side)) for i in range(n)}
    isolated = _count_isolated(positions, comm)
    migrations = 0

    while len(isolated) / n > isolation_threshold and migrations < max_iters:
        migrations += 1
        logging.info(
            "  Migration %d: %d/%d nodes isolated (%.0f%% > %.0f%%); relocating...",
            migrations, len(isolated), n,
            100 * len(isolated) / n, 100 * isolation_threshold,
        )
        if migrations > 1:
            for nid in positions:
                x, y = positions[nid]
                iso_flag = " [isolated]" if nid in isolated else ""
                logging.debug("    node %d: (%.1f, %.1f)%s", nid, x, y, iso_flag)
        for nid in isolated:
            positions[nid] = (rng.uniform(0.0, side), rng.uniform(0.0, side))
        isolated = _count_isolated(positions, comm)

    if migrations > 0:
        logging.info(
            "  Migration done after %d pass(es): %d/%d isolated (%.0f%%)",
            migrations, len(isolated), n, 100 * len(isolated) / n,
        )
    return positions


def _place_points(
    count: int,
    is_sink: bool,
    positions: Dict[int, Tuple[float, float]],
    comm: float,
    locked: Dict[int, Tuple[Tuple[float, float], bool]],
    max_placement_iters: int,
    rng: random.Random,
) -> List[Tuple[float, float]]:
    """
    Place *count* sink-or-source points in the network.

    Each point is located within *comm* radius of a randomly chosen anchor node.
    No two points share the same anchor (the anchor is "locked" after use).
    Mutates *locked* in-place; returns list of placed point positions.
    """
    label = "sink" if is_sink else "source"
    all_nids = list(positions.keys())
    placed: List[Tuple[float, float]] = []

    for j in range(count):
        available = [nid for nid in all_nids if nid not in locked]
        if not available:
            logging.warning(
                "  Point %s #%d: no unlocked anchors left; skipping.", label, j + 1)
            continue
        anchor = rng.choice(available)
        ax, ay = positions[anchor]

        point_pos: Optional[Tuple[float, float]] = None
        for attempt in range(max_placement_iters):
            angle = rng.uniform(0.0, 2.0 * math.pi)
            r = rng.uniform(0.0, comm)
            px = ax + r * math.cos(angle)
            py = ay + r * math.sin(angle)

            conflict = any(
                math.dist((px, py), positions[lnid]) < comm
                for lnid in locked
            )
            if not conflict:
                point_pos = (px, py)
                break
            logging.info(
                "  Re-attempt %d for %s point #%d (conflict detected).",
                attempt + 1, label, j + 1,
            )
        else:
            point_pos = (px, py)   # type: ignore[possibly-undefined]
            logging.warning(
                "  %s point #%d: accepted after %d retries (conflict may remain).",
                label, j + 1, max_placement_iters,
            )

        locked[anchor] = (point_pos, is_sink)
        placed.append(point_pos)

    return placed


def _assign_initial_roles(
    positions: Dict[int, Tuple[float, float]],
    sink_point_positions: List[Tuple[float, float]],
    source_point_positions: List[Tuple[float, float]],
    comm: float,
) -> Dict[int, CommRoleState]:
    """
    Compute initial CommRoleState for every node based on spatial proximity.

    Role assignment rules:
      1. A node within COMM of a sink point → RECEIVER.
      2. Among nodes within COMM of a source point, the one closest to it wins
         the SENDER election; ties are broken by smallest node ID.
      3. All other nodes → REPEATER.

    Returns {nid: CommRoleState} with dist_to_nearest_sink/source pre-filled.
    """
    def nearest_dist(nid: int, points: List[Tuple[float, float]]) -> float:
        if not points:
            return math.inf
        return min(math.dist(positions[nid], p) for p in points)

    dist_sink   = {nid: nearest_dist(nid, sink_point_positions)   for nid in positions}
    dist_source = {nid: nearest_dist(nid, source_point_positions) for nid in positions}

    roles: Dict[int, int] = {nid: CommunicationRole.REPEATER.value for nid in positions}

    for sink_pos in sink_point_positions:
        candidates = [
            nid for nid in positions
            if math.dist(positions[nid], sink_pos) < comm
        ]
        if candidates:
            winner = min(candidates, key=lambda n: (math.dist(positions[n], sink_pos), n))
            roles[winner] = CommunicationRole.RECEIVER.value

    for src_pos in source_point_positions:
        candidates = [
            nid for nid in positions
            if math.dist(positions[nid], src_pos) < comm
            and roles[nid] != CommunicationRole.RECEIVER.value
        ]
        if candidates:
            winner = min(candidates, key=lambda n: (math.dist(positions[n], src_pos), n))
            roles[winner] = CommunicationRole.SENDER.value

    return {
        nid: CommRoleState(
            role=roles[nid],
            dist_to_nearest_sink=dist_sink[nid],
            dist_to_nearest_source=dist_source[nid],
        )
        for nid in positions
    }


def _setup_network(
    nodes: int = NODES,
    sink_points: int = SINK_POINTS,
    source_points: int = SOURCE_POINTS,
    comm: float = COMM,
    side: float = SIDE,
    isolation_threshold: float = ISOLATION_THRESHOLD,
    max_migration_iters: int = MAX_MIGRATION_ITERS,
    max_point_placement_iters: int = MAX_POINT_PLACEMENT_ITERS,
    seed: int = 42,
) -> Tuple[
    Dict[int, Tuple[float, float]],
    List[Tuple[float, float]],
    List[Tuple[float, float]],
    Dict[int, CommRoleState],
]:
    """
    Full network setup: deploy + migrate + place sink/source points + assign roles.

    Returns: (positions, sink_positions, source_positions, initial_states)

    Raises:
        ValueError: if sink_points + source_points > nodes.
    """
    if sink_points + source_points > nodes:
        raise ValueError(
            f"Inconsistent configuration: sink_points ({sink_points}) + "
            f"source_points ({source_points}) > nodes ({nodes})."
        )

    rng = random.Random(seed)
    logging.info("Setting up network: %d nodes, %d sinks, %d sources", nodes, sink_points, source_points)

    positions = _build_and_migrate_network(
        nodes, side, comm, isolation_threshold, max_migration_iters, rng)

    locked: Dict[int, Tuple[Tuple[float, float], bool]] = {}
    sink_positions   = _place_points(sink_points,   True,  positions, comm, locked, max_point_placement_iters, rng)
    source_positions = _place_points(source_points, False, positions, comm, locked, max_point_placement_iters, rng)

    logging.info("Placed %d sink point(s) and %d source point(s).", len(sink_positions), len(source_positions))

    initial_states = _assign_initial_roles(positions, sink_positions, source_positions, comm)

    return positions, sink_positions, source_positions, initial_states


# ---------------------------------------------------------------------------
# AbstractExample subclass — toolchain bridge
# ---------------------------------------------------------------------------

class CommunicationRolesExample(AbstractExample):
    """Runs CommunicationRolesAggregate through the full toolchain.

    The constructor runs _setup_network() to determine initial positions.
    Validates, transpiles, compiles (SHA-256 cached), and runs the C++ binary.
    State updates arrive via IPC; per-node log files are written from snapshots.

    An extra per-simulation log (comm_receiver_messages.log) is opened in
    on_simulation_start() and closed in on_simulation_end(). Its content
    (RECEIVER node received_log_size per round) is written in on_round_complete().
    """

    def __init__(self, seed: int = 42):
        positions, sink_pos, source_pos, init_states = _setup_network(seed=seed)
        self._initial_positions = positions
        self._sink_positions = sink_pos
        self._source_positions = source_pos
        self._initial_states_cache = init_states

        self._recv_log = None
        self._last_snapshot = None

    @property
    def aggregate_class(self):
        return CommunicationRolesAggregate

    @property
    def log_prefix(self) -> str:
        return "comm_roles"

    def initial_positions(self) -> dict:
        return dict(self._initial_positions)

    def on_simulation_start(self) -> None:
        recv_log_path = self.log_dir / "comm_receiver_messages.log"
        self._recv_log = open(recv_log_path, "w")  # noqa: SIM115
        self._recv_log.write(
            "# Communication Roles Assignment — receiver message log (toolchain)\n"
            "# round,receiver_nid,received_log_size\n"
        )

    def log_header(self, node_id: int, state_data: Any) -> str:
        d = state_data if isinstance(state_data, dict) else vars(state_data)
        try:
            role_name = CommunicationRole(d.get('role', 0)).name
        except (ValueError, KeyError):
            role_name = "UNKNOWN"
        return (
            f"# CommRoles — node {node_id} ({role_name})\n"
            "# round,role,dist_to_receiver,dist_from_sender,received_log_size\n"
        )

    def log_line(self, round_num: int, node_id: int, state_data: Any) -> str:
        d = state_data if isinstance(state_data, dict) else vars(state_data)
        return (
            f"{round_num},{d.get('role', 0)},"
            f"{d.get('dist_to_receiver', 0.0):.4f},"
            f"{d.get('dist_from_sender', 0.0):.4f},"
            f"{d.get('received_log_size', 0)}\n"
        )

    def on_round_complete(self, round_num: int, snapshot) -> None:
        self._last_snapshot = snapshot
        if snapshot is None or self._recv_log is None:
            return
        for ns in snapshot.nodes:
            d = ns.state_data if isinstance(ns.state_data, dict) else vars(ns.state_data)
            if d.get('role') == CommunicationRole.RECEIVER.value:
                self._recv_log.write(
                    f"{round_num},{ns.node_id},{d.get('received_log_size', 0)}\n"
                )

    def on_simulation_end(self) -> None:
        if self._recv_log:
            self._recv_log.close()
            self._recv_log = None
        snap = self._last_snapshot
        n = len(self._initial_positions)
        receiver_sizes = {}
        if snap and snap.nodes:
            for ns in snap.nodes:
                d = ns.state_data if isinstance(ns.state_data, dict) else vars(ns.state_data)
                if d.get('role') == CommunicationRole.RECEIVER.value:
                    receiver_sizes[ns.node_id] = d.get('received_log_size', 0)
        total_msgs = sum(receiver_sizes.values())
        print(f"    Wrote {n} node logs + comm_receiver_messages.log → {self.log_dir}/")
        print(f"    Total distinct messages received across all Receivers: {total_msgs}")
        for rnid in sorted(receiver_sizes):
            print(f"    RECEIVER node {rnid:2d}: {receiver_sizes[rnid]} messages")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    print("\n" + "=" * 70)
    print("FCPP Bridge — Communication Roles Assignment Example")
    print("Demonstrates: bis_distance ×2, nbr+min_hood election, old ×2,")
    print("              broadcast, match/case — static roles, dynamic messages")
    print("=" * 70 + "\n")

    print("[1/4] Validating Python DSL...")
    try:
        report_validation(CommunicationRolesAggregate)
    except Exception as exc:
        print(f"    FAIL: {exc}")
        return

    print("\n[2/4] Transpiling to C++...")
    report_transpilation(CommunicationRolesAggregate)

    print("\n[3/4] Setting up network...")
    try:
        example = CommunicationRolesExample()
    except ValueError as exc:
        print(f"    FAIL: {exc}")
        return

    role_counts = {r: 0 for r in CommunicationRole}
    for s in example._initial_states_cache.values():
        role_counts[CommunicationRole(s.role)] += 1
    print(f"    Nodes: {NODES}  |  COMM radius: {COMM}  |  Side: {SIDE}")
    print(f"    Sink points: {len(example._sink_positions)}  |  Source points: {len(example._source_positions)}")
    print(
        "    Role distribution: "
        + ", ".join(f"{r.name}×{role_counts[r]}" for r in CommunicationRole)
    )

    print(
        f"\n[4/4] Running demo simulation "
        f"({NODES} nodes, {NUM_ROUNDS} rounds, MSG_TICKS_INTERVAL={MSG_TICKS_INTERVAL})..."
    )
    example.run(NUM_ROUNDS)

    print("\nAlgorithm summary (7 steps — all run at every node per round):")
    print("  1. bis_distance(is_receiver)   — gradient toward Receivers")
    print("  2. bis_distance(is_sender)     — gradient away from Senders")
    print("  3. nbr + min_hood              — Sender election (closest to source wins)")
    print("       tie-breaker: self_uid()   → node.uid in C++ (no CALL counter)")
    print("  4. old(0, t+1)                 — round counter")
    print("  5. broadcast(dist_from_sender, payload)")
    print("       propagate each Sender's message outward to entire network")
    print("  6. old({}, accumulate)         — received-message log at Receivers")
    print("  7. match/case                  — per-role task (no primitives inside)")
    print()
    print("CommunicationRole switch cases:")
    for r in CommunicationRole:
        print(f"  case {r.value}: {r.name}")
    print()
    print("Relationship to worker_role_assignment.py:")
    print("  RoleCommunicationType.ENDPOINT → CommunicationRole.SENDER")
    print("  RoleCommunicationType.RECEIVER → CommunicationRole.RECEIVER")
    print("  RoleCommunicationType.REPEATER → CommunicationRole.REPEATER")
    print("  (plus CommunicationRole.UNASSIGNED — pre-convergence default)")
    print()
    print("Primitives used:")
    print("  spreading.hpp  : bis_distance ×2, broadcast")
    print("  basics.hpp     : nbr, old ×2")
    print("  utils.hpp      : min_hood")
    print("  (node API)     : self_uid() → node.uid  [no CALL]")
    print()
    print("Future exercises (see FUTURE_EXERCISES.md):")
    print("  - Multiple independent communication instances via spawn")
    print("  - Dynamic sink/source points (changing every N ticks)")
    print("  - Mobile nodes wandering to locate sink/source points")
    print("  - Area partition + node scanning assignment")
    print()


if __name__ == "__main__":
    main()
