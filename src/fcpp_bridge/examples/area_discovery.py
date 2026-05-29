"""
Area Discovery — fcpp_bridge DSL exercise (FE-10).

Concept
-------
A rectangular area is divided into a regular grid of square tiles.  Each node
claims its "personal tile" (the one whose centre is closest to its position).
Nodes share only their personal tile centre via ``nbr`` — they never broadcast
the whole map.

Tile shapes (polygon corners) are stored in a ``scattered_database`` with the
tile centre as key.  A node queries the database for a *neighbour's* tile shape,
extending Exercise FE-9.

Constraint (simplest version): ``n ≥ num_tiles``, so every tile has at least
one node.  With the default constants (16 nodes, 4×4 grid = 16 tiles) and
random positions inside the area, most tiles end up with exactly one owner.

Key learning goals
------------------
- ``nbr`` shares a per-node scalar/tuple; it does **not** share entire dicts.
- Tile shapes are stored as ``scattered_database`` values keyed on tile centre.
  No single node holds the full map, yet the full map is collectively available.
- ``fold_hood`` with a set-union lambda is the correct idiom for collecting a
  neighbourhood set without ``broadcast``.

FCPP primitive ordering note
-----------------------------
All aggregate primitives (``bis_distance``, ``sp_collection``, ``old``,
``spawn``, ``nbr``, ``fold_hood``) are called **unconditionally** before any
branching — same rule as in FE-9 and all existing examples.

Log files written to examples/logs/:
    node_<id>_area_discovery.log — per-node per-round stats
"""

import math
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, FrozenSet, Optional, Tuple

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
    grid_tile_centers,
    nearest_tile_center,
    compute_tile_shapes,
    TileCenter,
)
from fcpp_bridge.examples.abstract_example import AbstractExample

log = logging.getLogger(__name__)

# Spawn status aliases
STATUS_BORDER     = SPAWN_STATUS_BORDER
STATUS_INTERNAL   = SPAWN_STATUS_INTERNAL
STATUS_TERMINATED = SPAWN_STATUS_TERMINATED

# ---------------------------------------------------------------------------
# Simulation constants
# ---------------------------------------------------------------------------

N          = 16
AREA       = (0.0, 0.0, 400.0, 400.0)
CELL_SIZE  = 100.0     # tile side (divides area evenly → 4×4 = 16 tiles)
COMM       = 150.0
DIAMETER_ESTIMATE         = 12     # conservative hop-count estimate of network diameter
QUERY_TIMEOUT_TOLERANCE_FRAC = 0.125  # 1/8 of diameter added as extra tolerance (configurable)
QUERY_TIMEOUT_TOLERANCE   = max(1, round(DIAMETER_ESTIMATE * QUERY_TIMEOUT_TOLERANCE_FRAC))
QUERY_TIMEOUT  = 30 + QUERY_TIMEOUT_TOLERANCE
SPAWN_THRESHOLD = 1e-3
NUM_ROUNDS = 60


# ---------------------------------------------------------------------------
# State dataclass
# ---------------------------------------------------------------------------

@dataclass
class AreaDiscoveryState:
    """Per-node state for the area-discovery algorithm.

    Extends FE-9 ``ScatteredDBState`` with tile-specific fields.

    local_db               — shard: {TileCenter → tile_polygon}
                             (starts with this node's own tile shape)
    query_target           — tile centre currently being queried (None = idle)
    query_age              — rounds since current query was sent
    answer_ready           — True when a response has arrived this round
    answer_value           — the received polygon (None until answered)
    my_tile_center         — this node's personal tile (constant after round 1)
    neighbors_tile_centers — frozenset of 1-hop neighbours' tile centres
    tile_shape_known       — True once this node has its tile's shape in local_db
    """
    local_db:                Dict[Any, Any]                  = None   # type: ignore[assignment]
    query_target:            Optional[TileCenter]            = None
    query_age:               int                             = 0
    answer_ready:            bool                            = False
    answer_value:            Any                             = None
    my_tile_center:          Optional[TileCenter]            = None
    neighbors_tile_centers:  FrozenSet[TileCenter]           = field(default_factory=frozenset)
    tile_shape_known:        bool                            = False

    def __post_init__(self) -> None:
        if self.local_db is None:
            self.local_db = {}


# ---------------------------------------------------------------------------
# Aggregate function — Python DSL (transpiles to C++)
# ---------------------------------------------------------------------------

@aggregate_function
class AreaDiscoveryAggregate:
    """Aggregate program: tile claim + scattered-database shape query.

    Algorithm (6 steps — all primitives unconditional):
      1. bis_distance   — routing gradient from node 0
      2. sp_collection  — routing subtree
      3. old            — query age counter
      4. spawn          — shape query (same pattern as FE-9, but keyed on TileCenter)
      5. nbr            — share personal tile centre with 1-hop neighbours
      6. fold_hood      — collect set of all 1-hop neighbours' tile centres

    Note on my_tile_center
    ----------------------
    In a full FCPP deployment ``my_tile_center`` is computed once on the Python
    side and injected via ``set_initial_storage``.  In the Python DSL compute()
    it is read from ``self_state`` (carried from the initial state).  In C++, the
    initial state is provided by ``initial_state()``; the Python-side override
    fills ``my_tile_center`` before the simulation starts.

    Note on fold_hood vs min_hood
    ------------------------------
    ``min_hood`` on tuples compares lexicographically, which is not a set union.
    The correct idiom for collecting a neighbourhood SET is:
        ``fold_hood(lambda a, b: a | {b}, nbr_field, frozenset())``
    This is demonstrated in step 6 below.
    """

    def initial_state(self) -> AreaDiscoveryState:
        return AreaDiscoveryState()

    def compute(
        self,
        self_state: AreaDiscoveryState,
        neighbors: Neighborhood[AreaDiscoveryState],
    ) -> AreaDiscoveryState:
        """Round computation — 6 aggregate primitives then state assembly."""

        # ── Step 1: BIS-distance gradient rooted at node 0 ───────────────────
        dist_from_root = bis_distance(self_uid() == 0, 1.0, COMM)  # noqa: F821

        # ── Step 2: routing subtree ───────────────────────────────────────────
        routing_set = sp_collection(                                # noqa: F821
            dist_from_root,
            frozenset({self_uid()}),                               # noqa: F821
            frozenset(),
            lambda a, b: a | b,
        )

        # ── Step 3: query age (idle when no query is active) ──────────────────
        is_querying = (self_state.query_target is not None and not self_state.answer_ready)
        query_age = old(                                           # noqa: F821
            0,
            lambda prev: (prev + 1) if is_querying else 0,
        )

        # ── Step 4: spawn — shape query keyed on (uid, TileCenter) ───────────
        # Same routing logic as FE-9, but target key is a TileCenter tuple.
        # The holder (node whose shard contains this TileCenter) terminates
        # the spawn and provides the polygon as payload.
        new_query_key = (
            (self_uid(), self_state.query_target)                  # noqa: F821
            if is_querying else None
        )
        active_spawns = spawn(                                     # noqa: F821
            lambda key: (
                self_state.local_db.get(key[1]),   # payload: polygon if held
                STATUS_TERMINATED if key[1] in self_state.local_db
                else STATUS_INTERNAL if (
                    key[0] in routing_set or key[1] in routing_set
                )
                else STATUS_BORDER,
            ),
            new_query_key,
        )

        # ── Step 5: share personal tile centre with 1-hop neighbours ──────────
        # nbr shares one tuple per node; never the entire local_db.
        # C++: auto nbr_centers = nbr(CALL, self_state.my_tile_center);
        nbr_centers = nbr(self_state.my_tile_center)               # noqa: F821

        # ── Step 6: collect neighbours' tile centres as a set ─────────────────
        # fold_hood with set-union is the correct way to accumulate a neighbourhood
        # set.  min_hood would compare tuples lexicographically (wrong for sets).
        # C++: auto tc_set = fold_hood(CALL, [](auto a, auto b){ return a | {b}; },
        #                              nbr_centers, frozenset());
        neighbor_centers_set = fold_hood(                          # noqa: F821
            lambda acc, center: acc | {center},
            nbr_centers,
            frozenset(),
        )

        # ── Step 7: state assembly (pure Python — no more primitives) ─────────
        local_db     = dict(self_state.local_db)
        query_target = self_state.query_target
        age_out      = query_age
        answer_ready = self_state.answer_ready
        answer_value = self_state.answer_value
        tile_shape_known = self_state.tile_shape_known

        # Detect answer arrival (spawn terminated at holder → polygon propagated back)
        if is_querying and not answer_ready:
            for (req, tgt), val in active_spawns.items():
                if tgt == self_state.query_target and val is not None:
                    answer_ready = True
                    answer_value = val
                    break

        # Incorporate received tile shape into local_db
        if answer_ready and answer_value is not None:
            local_db[self_state.query_target] = answer_value
            if self_state.query_target == self_state.my_tile_center:
                tile_shape_known = True
            query_target = None
            age_out      = 0
            answer_ready = False
            answer_value = None

        # Timeout: abandon and retry
        elif is_querying and query_age > QUERY_TIMEOUT:
            query_target = None
            age_out      = 0

        # Start query for a neighbour tile shape not yet in local_db
        if query_target is None:
            for tc in neighbor_centers_set:
                if tc not in local_db:
                    query_target = tc
                    age_out = 0
                    break

        return AreaDiscoveryState(
            local_db               = local_db,
            query_target           = query_target,
            query_age              = age_out,
            answer_ready           = answer_ready,
            answer_value           = answer_value,
            my_tile_center         = self_state.my_tile_center,  # constant
            neighbors_tile_centers = frozenset(neighbor_centers_set),
            tile_shape_known       = tile_shape_known,
        )


# ---------------------------------------------------------------------------
# AbstractExample subclass — toolchain bridge
# ---------------------------------------------------------------------------

class AreaDiscoveryExample(AbstractExample):
    """Runs AreaDiscoveryAggregate through the full toolchain.

    Python-side setup (``on_simulation_start``):
    1. Generates random node positions.
    2. Builds the tile grid and tile shapes.
    3. Assigns each node its personal tile (nearest tile centre).
    4. Seeds ``local_db`` with the node's own tile shape (shard = one tile).

    The shard is stored in ``self._initial_storage`` for the demo in ``main()``.
    ``swarm.set_initial_storage`` (future IPC) would push this to C++.
    """

    @property
    def aggregate_class(self):
        return AreaDiscoveryAggregate

    @property
    def log_prefix(self) -> str:
        return "area_discovery"

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
        positions    = self.initial_positions()
        tile_centers = grid_tile_centers(AREA, CELL_SIZE)          # {tid: (cx, cy)}
        tile_shapes  = compute_tile_shapes(tile_centers, AREA, CELL_SIZE)

        storage: NodeStorage = {i: {} for i in range(N)}
        tile_owner: Dict[TileCenter, int] = {}

        for nid in range(N):
            tc = nearest_tile_center(positions[nid], tile_centers)
            storage[nid]['my_tile_center']   = tc
            storage[nid]['local_db']         = {tc: tile_shapes[tc]}
            storage[nid]['tile_shape_known'] = True
            tile_owner[tc] = nid  # last writer wins (collision accepted for learning)

        self._initial_storage = storage
        self._tile_centers    = tile_centers
        self._tile_owner      = tile_owner
        # Future: swarm.set_initial_storage(storage)

        claimed = len(tile_owner)
        total   = len(tile_centers)
        log.info(
            "AreaDiscovery: %d nodes, %d/%d tiles claimed",
            N, claimed, total,
        )
        if claimed < total:
            unclaimed = [tc for tc in tile_shapes if tc not in tile_owner]
            log.warning("Unclaimed tiles: %s", unclaimed)

    def log_header(self, node_id: int, state_data: Any) -> str:
        return (
            f"# AreaDiscovery — node {node_id}\n"
            "# round,my_tile_x,my_tile_y,nbr_tiles,db_size,shape_known,query_target_x,query_target_y\n"
        )

    def log_line(self, round_num: int, node_id: int, state_data: Any) -> str:
        d  = state_data if isinstance(state_data, dict) else vars(state_data)
        tc = d.get('my_tile_center') or (0.0, 0.0)
        qt = d.get('query_target')
        return (
            f"{round_num},"
            f"{tc[0]:.1f},{tc[1]:.1f},"
            f"{len(d.get('neighbors_tile_centers') or [])},"
            f"{len(d.get('local_db') or {})},"
            f"{int(d.get('tile_shape_known', False))},"
            f"{qt[0]:.1f if qt else 0.0},{qt[1]:.1f if qt else 0.0}\n"
        )

    def on_round_complete(self, round_num: int, snapshot) -> None:
        if snapshot is None:
            return
        if round_num % 10 == 0:
            full_nodes = sum(
                1 for ns in snapshot.nodes
                if len(
                    (ns.state_data if isinstance(ns.state_data, dict)
                     else vars(ns.state_data)).get('local_db', {})
                ) > 1
            )
            log.info(
                "Round %d: %d/%d nodes have queried at least one neighbour shape",
                round_num, full_nodes, N,
            )

    def on_simulation_end(self) -> None:
        print(f"    Wrote {N} node logs → {self.log_dir}/")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("\n" + "=" * 70)
    print("FCPP Bridge — Area Discovery Exercise (FE-10)")
    print("Demonstrates: nbr + fold_hood (set-union) + scattered_database query")
    print("=" * 70 + "\n")

    positions    = rnd_in_area(N, AREA, seed=42)
    tile_centers = grid_tile_centers(AREA, CELL_SIZE)

    print(f"Setup: {N} nodes, {len(tile_centers)} tiles ({CELL_SIZE:.0f}×{CELL_SIZE:.0f} each)")
    for nid in sorted(positions):
        tc = nearest_tile_center(positions[nid], tile_centers)
        print(f"  node {nid:2d} at {positions[nid]} → tile centre {tc}")

    print("\n[1/3] Validating Python DSL...")
    try:
        report_validation(AreaDiscoveryAggregate)
    except Exception as exc:
        print(f"    FAIL: {exc}")
        return

    print("\n[2/3] Transpiling to C++...")
    report_transpilation(AreaDiscoveryAggregate)

    print(f"\n[3/3] Toolchain run ({N} nodes, {NUM_ROUNDS} rounds)...")
    AreaDiscoveryExample().run(NUM_ROUNDS)

    print("\nAlgorithm summary (6 steps — all primitives run at every node):")
    print("  1. bis_distance  — routing gradient from node 0")
    print("  2. sp_collection — spanning-tree subtree (UIDs below this node)")
    print("  3. old           — query age counter")
    print("  4. spawn         — shape query (TileCenter key, polygon payload)")
    print("  5. nbr           — share my_tile_center with 1-hop neighbours")
    print("  6. fold_hood     — collect frozenset of neighbour tile centres")
    print()
    print("Key learning points:")
    print("  • nbr shares one tuple per node — never the entire local_db.")
    print("  • fold_hood(lambda a,b: a|{b}, field, frozenset()) collects a set.")
    print("  • min_hood on tuples gives lexicographic minimum (not set union).")
    print()
    print("Primitives used:")
    print("  spreading.hpp  : bis_distance")
    print("  collection.hpp : sp_collection")
    print("  basics.hpp     : spawn, old, nbr, fold_hood")
    print("  (node API)     : self_uid() → node.uid  [no CALL]")
    print()


if __name__ == "__main__":
    main()
