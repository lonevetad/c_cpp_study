"""
Scattered Database — fcpp_bridge DSL exercise (FE-9).

Concept
-------
Emulates a sharded, distributed, replicated key-value store.  Each node
holds a local *shard* of the global database initialised by
``spread_data_coprime_ID_pos``: ``{coprime_neighbour_id: that_neighbour's_position}``.

When a node needs an entry it does not hold, it requests it from the network.
The node that holds the target key routes the value back to the requester.

Routing strategy — Option A (reverse spawn, recommended)
---------------------------------------------------------
1. Requester emits a query spawn keyed on ``(self_uid(), target_id)``.
   The spawn propagates until it reaches the holder (TERMINATED) via the
   spanning tree built by ``bis_distance`` + ``sp_collection``.
2. The holder's TERMINATED value (the data payload) propagates back toward
   the spawn origin (the requester) via FCPP's spawn-termination mechanism.
3. When the terminated value reaches the requester, ``answer_ready = True``.

Option B (``bis_distance`` + ``channel_broadcast``) is simpler to implement
but requires the holder to know the requester's gradient direction in advance.
It is noted as a variant in the comments below.

FCPP primitive ordering note
-----------------------------
All aggregate primitives (``bis_distance``, ``sp_collection``, ``spawn``,
``old``) are called **unconditionally** so every node increments the internal
CALL counter in the same order.  State assembly (branching, arithmetic) comes
after all primitive calls.

Log files written to examples/logs/:
    node_<id>_scattered_db.log  — per-node per-round stats
"""

import math
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from fcpp_bridge.python_dsl import aggregate_function, Neighborhood
from fcpp_bridge.examples._example_utils import (
    SPAWN_STATUS_BORDER,
    SPAWN_STATUS_INTERNAL,
    SPAWN_STATUS_TERMINATED,
    report_validation,
    report_transpilation,
)
from fcpp_bridge.examples.ex_utils import (
    rnd_in_area,
    NodeStorage,
    spread_data_coprime_ID_pos,
)
from fcpp_bridge.examples.abstract_example import AbstractExample

log = logging.getLogger(__name__)

# Spawn process status codes
STATUS_BORDER     = SPAWN_STATUS_BORDER       # 0 — off routing path
STATUS_INTERNAL   = SPAWN_STATUS_INTERNAL     # 1 — actively routing
STATUS_TERMINATED = SPAWN_STATUS_TERMINATED   # 2 — answer reached requester

# ---------------------------------------------------------------------------
# Simulation constants
# ---------------------------------------------------------------------------

N              = 15
AREA           = (0.0, 0.0, 500.0, 500.0)
COMM           = 150.0
DIAMETER_ESTIMATE         = 12     # conservative hop-count estimate of network diameter
QUERY_TIMEOUT_TOLERANCE_FRAC = 0.125  # 1/8 of diameter added as extra tolerance (configurable)
QUERY_TIMEOUT_TOLERANCE   = max(1, round(DIAMETER_ESTIMATE * QUERY_TIMEOUT_TOLERANCE_FRAC))
QUERY_TIMEOUT  = 30 + QUERY_TIMEOUT_TOLERANCE   # rounds before abandoning a query
SPAWN_THRESHOLD = 1e-3        # spawn liveness threshold
NUM_ROUNDS     = 60


# ---------------------------------------------------------------------------
# State dataclass
# ---------------------------------------------------------------------------

@dataclass
class ScatteredDBState:
    """Per-node state for the scattered-database algorithm.

    local_db      — this node's shard: {id → position} (grows as answers arrive)
    query_target  — ID currently being queried (-1 = idle)
    query_age     — rounds elapsed since current query was sent
    answer_ready  — True when a response has been received this round
    answer_value  — the received value (None until answered)
    """
    local_db:     Dict[int, Tuple[float, float]] = None   # type: ignore[assignment]
    query_target: int                           = -1
    query_age:    int                           = 0
    answer_ready: bool                          = False
    answer_value: Optional[Tuple[float, float]] = None

    def __post_init__(self) -> None:
        if self.local_db is None:
            self.local_db = {}


# ---------------------------------------------------------------------------
# Aggregate function — Python DSL (transpiles to C++)
# ---------------------------------------------------------------------------

@aggregate_function
class ScatteredDBAggregate:
    """Aggregate program: distributed shard query via reverse spawn.

    Algorithm (7 steps — all primitives unconditional):
      1. bis_distance — routing gradient from node 0 (fixed root)
      2. sp_collection — routing subtree (UIDs "below" this node)
      3. old           — persist and age the current query
      4. spawn         — query token: propagates toward holder; TERMINATES there
                         with the data payload, which flows back to requester
      5. State assembly — update local_db / start new query / detect timeout

    Note on self_uid():
        Returns ``node.uid`` in C++; returns 0 (placeholder) in Python DSL.
        The demo simulation below passes ``nid`` directly to work around this.

    Note on initial_state():
        All nodes start with an empty ``local_db``.  In a full deployment the
        shard from ``spread_data_coprime_ID_pos`` would be injected via
        ``swarm.set_initial_storage(storage)`` before round 1.
        That IPC command is planned for a future version; until then the
        C++ binary begins with empty shards and the Python demo pre-populates
        storage manually in ``ScatteredDBExample.on_simulation_start``.
    """

    def initial_state(self) -> ScatteredDBState:
        return ScatteredDBState()

    def compute(
        self,
        self_state: ScatteredDBState,
        neighbors: Neighborhood[ScatteredDBState],
    ) -> ScatteredDBState:
        """Round computation — 4 aggregate primitives then state assembly."""

        # ── Step 1: BIS-distance gradient rooted at the fixed root (node 0) ──
        # Every node uses this gradient for spawn routing.
        # In a production deployment each requester would build its own gradient,
        # but using a shared root keeps the exercise concise.
        # C++: double d = bis_distance(CALL, self_uid() == 0, 1.0, COMM);
        dist_from_root = bis_distance(self_uid() == 0, 1.0, COMM)  # noqa: F821

        # ── Step 2: routing subtree ───────────────────────────────────────────
        # Collects the set of UIDs in this node's spanning-tree subtree toward
        # the root.  Used to determine INTERNAL routing status for the spawn.
        # C++: auto rs = sp_collection(CALL, d, {node.uid}, {}, [](auto a, auto b){ return a | b; });
        routing_set = sp_collection(                                # noqa: F821
            dist_from_root,
            frozenset({self_uid()}),                               # noqa: F821
            frozenset(),
            lambda a, b: a | b,
        )

        # ── Step 3: query age — incremented each round while querying ─────────
        # old(initial, update) accumulates temporally; resets to 0 when idle.
        # C++: int age = old(CALL, 0, [&](int p){ return querying ? p+1 : 0; });
        is_querying = (self_state.query_target != -1 and not self_state.answer_ready)
        query_age = old(                                           # noqa: F821
            0,
            lambda prev: (prev + 1) if is_querying else 0,
        )

        # ── Step 4: spawn — query token with reverse-spawn response ───────────
        # Key:    (requester_uid, target_id)
        # Status: TERMINATED → this node holds the data (it becomes the answer)
        #         INTERNAL   → on the routing path (uid in spanning subtree)
        #         BORDER     → off path; does not relay
        # Payload: the data value when TERMINATED, else None.
        #
        # FCPP semantics: when a spawn terminates, the terminal value propagates
        # back toward the spawn's origin.  The requester collects it from the
        # returned active_spawns map.
        #
        # Option B alternative (simpler, noted here for reference):
        #   is_source = (self_uid() == requester_uid)
        #   reply_gradient = bis_distance(CALL, is_source, 1.0, COMM)
        #   answer = channel_broadcast(CALL, is_source, local_data, reply_gradient)
        new_query_key = (
            (self_uid(), self_state.query_target)                  # noqa: F821
            if is_querying else None
        )
        active_spawns = spawn(                                     # noqa: F821
            lambda key: (
                self_state.local_db.get(key[1]),   # payload: data if held, else None
                STATUS_TERMINATED if key[1] in self_state.local_db
                else STATUS_INTERNAL if (
                    key[0] in routing_set or key[1] in routing_set
                )
                else STATUS_BORDER,
            ),
            new_query_key,
        )

        # ── Step 5: state assembly (pure Python — no more primitives) ─────────
        local_db     = dict(self_state.local_db)
        query_target = self_state.query_target
        age_out      = query_age
        answer_ready = self_state.answer_ready
        answer_value = self_state.answer_value

        # Detect answer: spawn terminated at holder → payload arrived at requester
        if is_querying and not answer_ready:
            for (req, tgt), val in active_spawns.items():
                if tgt == self_state.query_target and val is not None:
                    answer_ready = True
                    answer_value = val
                    break

        # Incorporate received answer
        if answer_ready and answer_value is not None:
            local_db[self_state.query_target] = answer_value
            query_target = -1
            age_out      = 0
            answer_ready = False
            answer_value = None

        # Timeout: abandon stale query and retry next round
        elif is_querying and query_age > QUERY_TIMEOUT:
            query_target = -1
            age_out      = 0

        # Start a new query if idle and shard is incomplete
        if query_target == -1:
            known = set(local_db.keys()) | {self_uid()}           # noqa: F821
            candidates = [i for i in range(N) if i not in known]
            if candidates:
                query_target = candidates[0]
                age_out      = 0

        return ScatteredDBState(
            local_db=local_db,
            query_target=query_target,
            query_age=age_out,
            answer_ready=answer_ready,
            answer_value=answer_value,
        )


# ---------------------------------------------------------------------------
# AbstractExample subclass — toolchain bridge
# ---------------------------------------------------------------------------

class ScatteredDBExample(AbstractExample):
    """Runs ScatteredDBAggregate through the full toolchain.

    Pre-populates each node's ``local_db`` shard with the coprime-neighbour
    position map via ``spread_data_coprime_ID_pos``.

    Note: ``on_simulation_start`` stores the shard in ``self._initial_storage``
    so the Python demo in ``main()`` can use it.  The IPC call
    ``swarm.set_initial_storage(storage)`` required to push initial state to
    the C++ binary is planned for a future release.
    """

    @property
    def aggregate_class(self):
        return ScatteredDBAggregate

    @property
    def log_prefix(self) -> str:
        return "scattered_db"

    @property
    def log_dir(self) -> Path:
        return Path(__file__).parent / "logs"

    @property
    def build_dir(self) -> Path:
        return Path(__file__).parent / ".fcpp_build"

    @property
    def cpp_dir(self) -> Path:
        return Path(__file__).parent / ".fcpp_cpp"

    def initial_positions(self) -> Dict[int, Tuple[float, ...]]:
        return rnd_in_area(N, AREA, seed=42)

    def on_simulation_start(self) -> None:
        positions = self.initial_positions()
        storage: NodeStorage = {i: {} for i in range(N)}
        spread_data_coprime_ID_pos(storage, positions, COMM, field='local_db')
        self._initial_storage = storage
        # Future: swarm.set_initial_storage(storage)
        # Until that IPC command is available, the C++ binary starts with empty
        # shards and the algorithm converges more slowly (nodes have no initial data).
        log.info(
            "ScatteredDB: %d nodes, shard sizes: %s",
            N,
            {nid: len(s['local_db']) for nid, s in storage.items()},
        )

    def log_header(self, node_id: int, state_data: Any) -> str:
        return (
            f"# ScatteredDatabase — node {node_id}\n"
            "# round,query_target,query_age,db_size,answer_ready\n"
        )

    def log_line(self, round_num: int, node_id: int, state_data: Any) -> str:
        d = state_data if isinstance(state_data, dict) else vars(state_data)
        return (
            f"{round_num},"
            f"{d.get('query_target', -1)},"
            f"{d.get('query_age', 0)},"
            f"{len(d.get('local_db', {}))},"
            f"{int(d.get('answer_ready', False))}\n"
        )

    def on_round_complete(self, round_num: int, snapshot) -> None:
        if snapshot is None:
            return
        answered = sum(
            1 for ns in snapshot.nodes
            if (ns.state_data if isinstance(ns.state_data, dict)
                else vars(ns.state_data)).get('answer_ready', False)
        )
        if answered:
            log.info("Round %d: %d node(s) received a query answer", round_num, answered)

    def on_simulation_end(self) -> None:
        print(f"    Wrote {N} node logs → {self.log_dir}/")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("\n" + "=" * 70)
    print("FCPP Bridge — Scattered Database Exercise (FE-9)")
    print("Demonstrates: spawn query routing + old + bis_distance + sp_collection")
    print("=" * 70 + "\n")

    print("[1/3] Validating Python DSL...")
    try:
        report_validation(ScatteredDBAggregate)
    except Exception as exc:
        print(f"    FAIL: {exc}")
        return

    print("\n[2/3] Transpiling to C++...")
    report_transpilation(ScatteredDBAggregate)

    print(f"\n[3/3] Toolchain run ({N} nodes, {NUM_ROUNDS} rounds)...")
    print("    Note: C++ binary starts with empty shards (set_initial_storage pending).")
    print("    Convergence will require more rounds than with pre-populated shards.")
    ScatteredDBExample().run(NUM_ROUNDS)

    print("\nAlgorithm summary (4 steps — all primitives run at every node):")
    print("  1. bis_distance    — routing gradient from root node (uid == 0)")
    print("  2. sp_collection   — spanning-tree subtree (UIDs below this node)")
    print("  3. old             — query age counter (reset to 0 when idle)")
    print("  4. spawn           — query token: TERMINATED at holder → payload flows back")
    print()
    print("State fields:")
    print("  local_db      — this node's shard {id: position}")
    print("  query_target  — ID currently being queried (-1 = idle)")
    print("  query_age     — rounds elapsed since query started")
    print("  answer_ready  — True when a response arrived this round")
    print("  answer_value  — the received value (None until answered)")
    print()
    print("Primitives used:")
    print("  spreading.hpp  : bis_distance")
    print("  collection.hpp : sp_collection")
    print("  basics.hpp     : spawn, old")
    print("  (node API)     : self_uid() → node.uid  [no CALL]")
    print()


if __name__ == "__main__":
    main()
