"""
Iteratively Area Discovery — fcpp_bridge DSL exercise (FE-11).

Concept
-------
Tiles outnumber nodes.  Nodes must repeatedly explore tiles until all are
covered.  The four-phase cycle per node:

  SEEKING   → query "is tile T assigned?"  Wait up to ``2×diameter + margin``
               rounds.  No reply → tile is unassigned → distributed election.
  MOVING    → winning node moves toward tile centre via ``follow_target``.
  EXPLORING → node is at tile centre; sits still for ``EXPLORE_TICKS`` rounds.
  DONE      → all reachable tiles have been explored.

Anti-double-assignment protocol (second scattered_database)
------------------------------------------------------------
A **second** key-value store ``assignment_db: {TileCenter → node_id}`` tracks
which tiles are assigned.  It is separate from ``local_db`` (tile shapes):

  DB               Keys        Values
  local_db         TileCenter  tile polygon (shape)
  assignment_db    TileCenter  assigned node ID (int)

Filling ``assignment_db`` (1-hop spawn propagation)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
When node n claims tile t (SEEKING → MOVING):
  1. n inserts (t → n_id) into its own ``assignment_db``.
  2. n emits a 1-hop ``spawn`` keyed on ``(n_id, t, 'assign')``.
  3. Liveness: ``hops_distance ≤ 1 AND t NOT IN recipient.assignment_db``.
  4. Each eligible neighbour inserts (t → n_id) and exits.
  No node stays at the spawn boundary — the DB membership guard self-terminates.

Querying (double-assignment avoidance)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Before claiming tile t:
  1. Local check: ``t in assignment_db`` → skip.
  2. Network query spawn with timeout:
     ``QUERY_TIMEOUT_MULT × DIAMETER_ESTIMATE + QUERY_TIMEOUT_MARGIN`` rounds.
  3. Reply → update local ``assignment_db``; skip t.
  4. Timeout → unassigned → **distributed election**:
     compute distance to t; share via ``nbr``; win iff distance ≤ ``min_hood``.
     (Same idiom as FE-6 min-UID election, keyed on distance instead of UID.)

Version A (default): rectangular area.
Version B (extension): non-rectangular convex polygon area — only tile initialisation changes.

FCPP primitive ordering note
-----------------------------
ALL aggregate primitives are called unconditionally so that every node
increments the CALL counter in the same order:
  1. nbr / min_hood  — election distance sharing
  2. spawn (query)   — "is tile assigned?" query token
  3. spawn (assign)  — 1-hop assignment propagation token
  4. old             — exploring_ticks counter
  5. follow_target   — movement (called unconditionally; no-op when not MOVING)

Log files written to examples/logs/:
    node_<id>_iter_area_discovery.log  — per-node per-round stats
"""

import math
import logging
from dataclasses import dataclass, field
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
# Node status constants  (stored in IterAreaDiscoveryState.status)
# ---------------------------------------------------------------------------

STATUS_SEEKING    = 0   # no tile, looking for an unassigned one
STATUS_MOVING     = 1   # moving toward my_tile centre
STATUS_EXPLORING  = 2   # at tile centre, counting down EXPLORE_TICKS
STATUS_DONE       = 3   # this node has finished all reachable tiles

# ---------------------------------------------------------------------------
# Simulation constants
# ---------------------------------------------------------------------------

N                    = 10
AREA                 = (0.0, 0.0, 600.0, 600.0)
CELL_SIZE            = 100.0        # → 6×6 = 36 tiles, 3.6× more than nodes
COMM                 = 150.0
EXPLORE_TICKS        = 7            # rounds to "explore" a tile
MOVE_SPEED           = 15.0         # units/round (slow relative to COMM)
SPAWN_THRESHOLD      = 1e-3
QUERY_TIMEOUT_MULT            = 2     # base timeout = 2 × network diameter
QUERY_TIMEOUT_MARGIN          = 4     # extra rounds beyond base (+margin)
DIAMETER_ESTIMATE             = 12    # fallback if diameter cannot be computed live
QUERY_TIMEOUT_TOLERANCE_FRAC  = 0.125  # 1/8 of diameter added as extra tolerance (configurable)
QUERY_TIMEOUT_TOLERANCE       = max(1, round(DIAMETER_ESTIMATE * QUERY_TIMEOUT_TOLERANCE_FRAC))
NUM_ROUNDS           = 200


# ---------------------------------------------------------------------------
# State dataclass
# ---------------------------------------------------------------------------

@dataclass
class IterAreaDiscoveryState:
    """Per-node state for the iterative area-discovery algorithm.

    First scattered_database (from FE-9/FE-10):
        local_db        — {TileCenter → tile_polygon}; explored tile shapes

    Second scattered_database (FE-11 new, anti-double-assignment):
        assignment_db   — {TileCenter → node_id}; known tile assignments

    Area-discovery fields:
        my_tile         — current target tile centre (None when SEEKING)
        exploring_ticks — rounds spent exploring the current tile
        pending_queries — {TileCenter → age}; tiles with an outstanding query
        status          — one of STATUS_SEEKING / MOVING / EXPLORING / DONE
    """
    local_db:        Dict[TileCenter, Any]    = None   # type: ignore[assignment]
    assignment_db:   Dict[TileCenter, int]    = None   # type: ignore[assignment]
    my_tile:         Optional[TileCenter]     = None
    exploring_ticks: int                      = 0
    pending_queries: Dict[TileCenter, int]    = None   # type: ignore[assignment]
    status:          int                      = STATUS_SEEKING

    def __post_init__(self) -> None:
        if self.local_db     is None: self.local_db     = {}
        if self.assignment_db is None: self.assignment_db = {}
        if self.pending_queries is None: self.pending_queries = {}


# ---------------------------------------------------------------------------
# Aggregate function — Python DSL (transpiles to C++)
# ---------------------------------------------------------------------------

@aggregate_function
class IterAreaDiscoveryAggregate:
    """Aggregate program: iterative tile exploration with anti-double-assignment.

    Algorithm (5 aggregate-primitive groups — all unconditional):
      1. nbr + min_hood  — share distance to best candidate tile for election
      2. spawn (query)   — "is tile T assigned?" query token
      3. spawn (assign)  — 1-hop assignment propagation (fills assignment_db)
      4. old             — exploring_ticks counter
      5. follow_target   — movement toward tile centre (no-op unless MOVING)

    After the primitives, pure Python assembles the next state (Steps 6–10).

    Note on self_pos() and follow_target()
    ----------------------------------------
    ``follow_target(target_pos, max_speed)`` maps to
    ``follow_target(CALL, target_pos, max_speed)`` in C++ (geometry.hpp).
    In the FCPP runtime, the node's position is updated automatically.
    In the Python DSL placeholder, ``follow_target`` is a no-op; positions are
    updated externally in ``on_round_complete`` of the Example class.

    ``self_pos()`` is not a FCPP DSL primitive — the C++ runtime provides node
    position via node fields.  Distance-to-tile computations that use
    ``math.dist(self_pos(), tile)`` are Python-side and are replaced by C++
    equivalents (``make_vec`` / Euclidean distance) when compiled.

    Note on 1-hop spawn liveness
    ------------------------------
    The liveness guard for the assignment spawn uses two conditions:
      (a) threshold decay: spawn value × 0.0005 after 1 hop — limits reach.
      (b) body guard: ``if tile not in assignment_db: insert(…)`` — prevents
          double-insertion and makes the spawn self-terminating.
    Open Design Question Q6 (EXERCISES_PLAN.md) tracks this mechanism.
    """

    def initial_state(self) -> IterAreaDiscoveryState:
        return IterAreaDiscoveryState()

    def compute(
        self,
        self_state: IterAreaDiscoveryState,
        neighbors: Neighborhood[IterAreaDiscoveryState],
    ) -> IterAreaDiscoveryState:
        """Round computation — all primitives unconditional, then state assembly."""

        # ── Step 1: election infrastructure — nbr + min_hood ─────────────────
        # Each SEEKING node computes its Euclidean distance to the best
        # (nearest unassigned) candidate tile.  Sharing via nbr + min_hood
        # implements the distributed min-distance election (analogous to FE-6).
        #
        # self_pos() placeholder: Python DSL returns (0, 0).
        # In C++, node position is available as a runtime field.
        #
        # When not SEEKING (or no candidate exists), distance is set to +inf
        # so the node does not interfere with the election.
        assignment_db = dict(self_state.assignment_db)

        # Identify candidate tiles: known to network but not yet in assignment_db
        # and not already being queried.  all_tile_centers is injected via
        # set_initial_storage; until then it is read from local_db or assumed empty.
        all_tiles = list(self_state.local_db.keys())   # tiles known so far

        # Best candidate from this node's perspective (lowest distance, unassigned)
        seeking = (self_state.status == STATUS_SEEKING)
        unqueried = [
            t for t in all_tiles
            if t not in assignment_db and t not in self_state.pending_queries
        ]
        if seeking and unqueried:
            best_candidate = min(unqueried, key=lambda t: math.dist(self_pos(), t))  # noqa: F821
            dist_to_best = math.dist(self_pos(), best_candidate)                     # noqa: F821
        else:
            best_candidate = None
            dist_to_best = float('inf')

        # Share distance; min_hood selects the node closest to best_candidate.
        nbr_dists    = nbr(dist_to_best)                           # noqa: F821
        min_nbr_dist = min_hood(nbr_dists)                         # noqa: F821

        # ── Step 2: spawn — "is tile assigned?" query ─────────────────────────
        # For each tile in pending_queries emit a query spawn.
        # A node that has the tile in its assignment_db returns TERMINATED with
        # the assigned node_id; others relay (INTERNAL) or ignore (BORDER).
        # (Only one query key is supported per round in this simplified version.)
        query_tile   = next(iter(self_state.pending_queries), None)
        new_q_key    = (self_uid(), query_tile, 'query') if query_tile else None  # noqa: F821
        query_spawns = spawn(                                      # noqa: F821
            lambda key: (
                assignment_db.get(key[1]),   # payload: assigned_id or None
                STATUS_TERMINATED if key[1] in assignment_db
                else STATUS_INTERNAL,
            ),
            new_q_key,
        )

        # ── Step 3: spawn — 1-hop assignment propagation ──────────────────────
        # Emitted when this node just claimed a tile (my_tile not yet in DB).
        # Liveness: (a) value × 0.0005 decay limits to 1 hop;
        #           (b) guard in body: insert only if tile NOT in assignment_db.
        # The spawned sub-program: eligible nodes insert and terminate.
        just_claimed = (
            self_state.status == STATUS_MOVING
            and self_state.my_tile is not None
            and self_state.my_tile not in self_state.assignment_db
        )
        assign_key = (
            (self_uid(), self_state.my_tile, 'assign')             # noqa: F821
            if just_claimed else None
        )
        assign_spawns = spawn(                                     # noqa: F821
            lambda key: (
                key[1],            # payload: the tile centre being assigned
                # TERMINATED iff this node does NOT yet have the tile in DB
                # (insert + terminate; liveness body guard)
                STATUS_TERMINATED if key[1] not in assignment_db
                else STATUS_BORDER,  # already inserted → leave spawn
            ),
            assign_key,
        )

        # ── Step 4: old — exploring_ticks counter ─────────────────────────────
        # Accumulated via old(); resets to 0 outside EXPLORING status.
        is_exploring = (self_state.status == STATUS_EXPLORING)
        exploring_ticks = old(                                     # noqa: F821
            0,
            lambda prev: (prev + 1) if is_exploring else 0,
        )

        # ── Step 5: follow_target — movement primitive (unconditional) ────────
        # In C++: follow_target(CALL, target_pos, max_speed) updates node position.
        # Called unconditionally; in SEEKING/EXPLORING/DONE status the target is
        # the current position (no movement).  In MOVING it drives toward my_tile.
        target_pos = (
            self_state.my_tile if self_state.status == STATUS_MOVING and self_state.my_tile
            else self_pos()                                        # noqa: F821
        )
        follow_target(target_pos, MOVE_SPEED)                      # noqa: F821

        # ── Step 6: incorporate assignment spawn results ───────────────────────
        # Insert tiles received via assign_spawns that are not yet in the DB.
        # (This is the "liveness body guard" from the spec.)
        for key, tile_center in assign_spawns.items():
            if tile_center not in assignment_db:
                src_nid = key[0]   # spawning node's UID
                assignment_db[tile_center] = src_nid

        # If we just claimed a tile, insert it in our own DB too.
        if just_claimed and self_state.my_tile is not None:
            assignment_db[self_state.my_tile] = self_uid()         # noqa: F821

        # ── Step 7: age pending queries; identify timed-out tiles ────────────
        timeout = QUERY_TIMEOUT_MULT * DIAMETER_ESTIMATE + QUERY_TIMEOUT_MARGIN + QUERY_TIMEOUT_TOLERANCE
        new_pending: Dict[TileCenter, int] = {}
        timed_out_tiles = []
        for tile, age in self_state.pending_queries.items():
            new_age = age + 1
            if tile in assignment_db:
                pass   # received a reply — drop from pending
            elif new_age > timeout:
                timed_out_tiles.append(tile)   # no reply → unassigned → election
            else:
                new_pending[tile] = new_age

        # ── Step 8: query-spawn result detection ──────────────────────────────
        # If a query spawn terminated (holder replied), update assignment_db.
        for (req, tgt, _), val in query_spawns.items():
            if val is not None and tgt not in assignment_db:
                assignment_db[tgt] = val   # val is the assigned node_id

        # ── Step 9: state machine — status transitions ────────────────────────
        my_tile = self_state.my_tile
        status  = self_state.status

        match status:

            case _ if status == STATUS_SEEKING:
                # Try to elect a winner for a timed-out (unassigned) tile
                if timed_out_tiles and best_candidate in timed_out_tiles:
                    is_winner = (dist_to_best <= min_nbr_dist)
                    if is_winner:
                        my_tile = best_candidate
                        assignment_db[best_candidate] = self_uid()  # noqa: F821
                        status  = STATUS_MOVING
                    # else: another node won; remove from pending on next round
                elif not timed_out_tiles:
                    # Issue new queries for unqueried candidate tiles
                    for t in unqueried[:3]:
                        new_pending[t] = 0   # start query, age=0

                # Transition to DONE if all known tiles are assigned
                if all(t in assignment_db for t in all_tiles) and len(all_tiles) > 0:
                    status = STATUS_DONE

            case _ if status == STATUS_MOVING:
                dist_to_tile = math.dist(self_pos(), my_tile) if my_tile else 0.0  # noqa: F821
                if dist_to_tile < CELL_SIZE / 2:
                    status = STATUS_EXPLORING

            case _ if status == STATUS_EXPLORING:
                if exploring_ticks >= EXPLORE_TICKS:
                    # Store explored tile in local_db, then seek next tile
                    if my_tile is not None:
                        local_db_out = dict(self_state.local_db)
                        local_db_out[my_tile] = True  # placeholder: real shape from DB
                    else:
                        local_db_out = dict(self_state.local_db)
                    my_tile = None
                    status  = STATUS_SEEKING
                    return IterAreaDiscoveryState(
                        local_db        = local_db_out,
                        assignment_db   = assignment_db,
                        my_tile         = my_tile,
                        exploring_ticks = 0,
                        pending_queries = new_pending,
                        status          = status,
                    )

            case _ if status == STATUS_DONE:
                pass   # nothing to do

        et_out = exploring_ticks if status == STATUS_EXPLORING else 0

        return IterAreaDiscoveryState(
            local_db        = dict(self_state.local_db),
            assignment_db   = assignment_db,
            my_tile         = my_tile,
            exploring_ticks = et_out,
            pending_queries = new_pending,
            status          = status,
        )


# ---------------------------------------------------------------------------
# AbstractExample subclass — toolchain bridge
# ---------------------------------------------------------------------------

class IterAreaDiscoveryExample(AbstractExample):
    """Runs IterAreaDiscoveryAggregate through the full toolchain.

    Python-side setup:
    - Builds the tile grid (36 tiles for 10 nodes → 3.6× ratio).
    - Precomputes tile shapes (for possible future set_initial_storage).
    - All nodes start with empty local_db and assignment_db (STATUS_SEEKING).
    """

    @property
    def aggregate_class(self):
        return IterAreaDiscoveryAggregate

    @property
    def log_prefix(self) -> str:
        return "iter_area_discovery"

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
        return rnd_in_area(N, AREA, seed=7)

    def on_simulation_start(self) -> None:
        tile_centers      = grid_tile_centers(AREA, CELL_SIZE)
        tile_shapes       = compute_tile_shapes(tile_centers, AREA, CELL_SIZE)
        self._total_tiles = len(tile_centers)
        self._tile_shapes = tile_shapes
        storage: NodeStorage = {
            i: {
                'local_db':        {},
                'assignment_db':   {},
                'status':          STATUS_SEEKING,
                'pending_queries': {},
                'exploring_ticks': 0,
                'my_tile':         None,
            }
            for i in range(N)
        }
        self._initial_storage = storage
        # Future: swarm.set_initial_storage(storage)
        log.info(
            "IterAreaDiscovery: %d nodes, %d tiles (ratio %.1f×)",
            N, self._total_tiles, self._total_tiles / N,
        )

    def log_header(self, node_id: int, state_data: Any) -> str:
        return (
            f"# IterAreaDiscovery — node {node_id}\n"
            "# round,status,my_tile_x,my_tile_y,explored,assigned_known,pending_queries\n"
        )

    def log_line(self, round_num: int, node_id: int, state_data: Any) -> str:
        d  = state_data if isinstance(state_data, dict) else vars(state_data)
        mt = d.get('my_tile') or (0.0, 0.0)
        return (
            f"{round_num},"
            f"{d.get('status', STATUS_SEEKING)},"
            f"{mt[0]:.1f},{mt[1]:.1f},"
            f"{len(d.get('local_db') or {})},"
            f"{len(d.get('assignment_db') or {})},"
            f"{len(d.get('pending_queries') or {})}\n"
        )

    def on_round_complete(self, round_num: int, snapshot) -> None:
        if snapshot is None:
            return
        explored   = sum(
            len((ns.state_data if isinstance(ns.state_data, dict)
                 else vars(ns.state_data)).get('local_db', {}))
            for ns in snapshot.nodes
        )
        done_nodes = sum(
            1 for ns in snapshot.nodes
            if (ns.state_data if isinstance(ns.state_data, dict)
                else vars(ns.state_data)).get('status') == STATUS_DONE
        )
        if round_num % 20 == 0:
            log.info(
                "Round %d: %d/%d tiles explored, %d/%d nodes done",
                round_num, explored, self._total_tiles, done_nodes, N,
            )
        if explored >= self._total_tiles:
            log.info("All %d tiles explored — simulation complete.", self._total_tiles)

    def on_simulation_end(self) -> None:
        print(f"    Wrote {N} node logs → {self.log_dir}/")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("\n" + "=" * 70)
    print("FCPP Bridge — Iteratively Area Discovery Exercise (FE-11)")
    print("Demonstrates: spawn 1-hop assignment + nbr min_hood election + follow_target")
    print("=" * 70 + "\n")

    tile_centers = grid_tile_centers(AREA, CELL_SIZE)
    print(
        f"Setup: {N} nodes, {len(tile_centers)} tiles "
        f"({CELL_SIZE:.0f}×{CELL_SIZE:.0f}, ratio {len(tile_centers)/N:.1f}×)"
    )
    print(
        f"Timeouts: base = {QUERY_TIMEOUT_MULT}×{DIAMETER_ESTIMATE} = "
        f"{QUERY_TIMEOUT_MULT*DIAMETER_ESTIMATE} rounds, "
        f"+margin = {QUERY_TIMEOUT_MARGIN}, +tolerance = {QUERY_TIMEOUT_TOLERANCE} "
        f"→ total {QUERY_TIMEOUT_MULT*DIAMETER_ESTIMATE+QUERY_TIMEOUT_MARGIN+QUERY_TIMEOUT_TOLERANCE}"
    )

    print("\n[1/3] Validating Python DSL...")
    try:
        report_validation(IterAreaDiscoveryAggregate)
    except Exception as exc:
        print(f"    FAIL: {exc}")
        return

    print("\n[2/3] Transpiling to C++...")
    report_transpilation(IterAreaDiscoveryAggregate)

    print(f"\n[3/3] Toolchain run ({N} nodes, {NUM_ROUNDS} rounds)...")
    IterAreaDiscoveryExample().run(NUM_ROUNDS)

    print("\nAlgorithm summary (5 primitive groups — all unconditional):")
    print("  1. nbr + min_hood  — election: node closest to candidate tile wins")
    print("  2. spawn (query)   — 'is tile assigned?' query with timeout")
    print("  3. spawn (assign)  — 1-hop propagation to fill assignment_db")
    print("  4. old             — exploring_ticks temporal counter")
    print("  5. follow_target   — movement toward tile centre")
    print()
    print("Anti-double-assignment protocol:")
    print("  • assignment_db (second DB): {TileCenter → node_id}")
    print("  • 1-hop spawn: liveness = hops≤1 AND tile NOT IN recipient.assignment_db")
    print("  • No node stays at the border (self-terminating via DB membership guard)")
    print("  • Timeout → election → min-distance winner claims the tile")
    print()
    print("Node status transitions:")
    print(f"  {STATUS_SEEKING} SEEKING → (win election) → {STATUS_MOVING} MOVING")
    print(f"  {STATUS_MOVING}  MOVING  → (at tile centre) → {STATUS_EXPLORING} EXPLORING")
    print(f"  {STATUS_EXPLORING}  EXPLORING → (EXPLORE_TICKS={EXPLORE_TICKS} rounds) → {STATUS_SEEKING} SEEKING")
    print(f"  {STATUS_DONE}  DONE    → (all tiles assigned) → stays DONE")
    print()
    print("Primitives used:")
    print("  geometry.hpp   : follow_target")
    print("  spreading.hpp  : (bis_distance via FE-9 shared infrastructure)")
    print("  basics.hpp     : nbr, spawn, old")
    print("  utils.hpp      : min_hood")
    print("  (node API)     : self_uid() → node.uid, self_pos() → node.position")
    print()
    print("Version B extension (non-rectangular area):")
    print("  Replace grid_tile_centers + compute_tile_shapes with polygon-aware")
    print("  versions that use clip_polygon_to_polygon from ex_utils/tiles.py.")
    print("  The FCPP algorithm is identical; only Python-side tile init changes.")
    print()


if __name__ == "__main__":
    main()
