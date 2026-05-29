# fcpp_bridge — Examples Implementation Plan

Three exercises that build incrementally on `ex_utils` and on each other:

```
ex_utils/position.py  ──┐
ex_utils/storage.py   ──┤── ex_utils/tiles.py (new)
                        │
                 scattered_database.py      (Exercise 1)
                        │
                 area_discovery.py          (Exercise 2)
                        │
                 iteratively_area_discovery.py  (Exercise 3)
```

All three live in `src/fcpp_bridge/examples/`.

---

## 0. Shared prerequisite: `examples/ex_utils/tiles.py` (new utility)

Both area exercises need tile-geometry helpers that do not belong in `position.py` or
`storage.py`. Create `examples/ex_utils/tiles.py` and re-export from `ex_utils/__init__.py`.

### API

```python
TileCenter = Tuple[float, float]
Polygon    = List[Tuple[float, float]]   # ordered corners (CCW)
TileMap    = Dict[TileCenter, Polygon]   # center → polygon corners

def grid_tile_centers(area: Tuple[float,...], cell_size: float) -> Dict[int, TileCenter]:
    """Return {tile_id: (cx, cy)} for all tiles whose centres lie inside *area*."""

def nearest_tile_center(pos: Tuple[float,...],
                        tile_centers: Dict[int, TileCenter]) -> TileCenter:
    """Return the TileCenter from *tile_centers* closest to *pos*."""

def compute_tile_shapes(tile_centers: Dict[int, TileCenter],
                        area: Tuple[float, float, float, float],
                        cell_size: float) -> TileMap:
    """Return {(cx, cy): polygon_corners} for every tile in *tile_centers*.

    Interior tiles: axis-aligned square (cx ± cell/2, cy ± cell/2).
    Border/corner tiles: above square clipped to *area* bounds.
    """

def clip_rect_to_rect(inner: Polygon, outer_area: Tuple[float,float,float,float]) -> Polygon:
    """Sutherland-Hodgman: clip *inner* polygon against a rectangular *outer_area*.

    Returns the (possibly empty) clipped polygon.
    """

def clip_polygon_to_polygon(subject: Polygon, clip: Polygon) -> Polygon:
    """Full Sutherland-Hodgman for arbitrary convex *clip* polygon.

    Used by iteratively_area_discovery when the area is a non-rectangular polygon.
    Returns the clipped polygon (empty list if no intersection).
    """
```

### Implementation notes

- `grid_tile_centers`: iterate `x` in `range(xmin + cell/2, xmax, cell)` and similarly
  for `y`, yield `(x, y)` only when the point is strictly inside or on the boundary of `area`.
- `clip_rect_to_rect` → special-case `clip_polygon_to_polygon` with 4-vertex clip polygon.
- Both clipping functions use the standard Sutherland-Hodgman inside/intersection logic;
  convexity of the clip shape is required (rectangle and convex polygon area both qualify).

---

## Exercise 1: `scattered_database`

### Concept

Emulates a sharded, distributed, replicated key-value store. Each node holds a local
subset of the global database ("shard"). Initial shards come from
`spread_data_coprime_ID_pos`: `{coprime_neighbor_id: that_neighbor's_position}`. After
initialisation the store is immutable at the node level — a node cannot see any entry
it was not given at start.

When a node needs an entry it does not have (a specific `target_id` absent from its
`local_db`, different from its own ID), it requests it from the network. The node that
holds `target_id` in its shard routes the value back to the requester.

### State

```python
@dataclass
class ScatteredDBState:
    local_db:       Dict[int, Tuple[float, ...]]    # shard: id → position (or other data)
    query_target:   int                             # ID being sought (-1 = no active query)
    query_age:      int                             # rounds since current query was sent
    answer_ready:   bool                            # True when a response has been received
    answer_value:   Optional[Tuple[float, ...]]     # the received value (None until answered)
```

### Constants

```python
N              = 15
AREA           = (0.0, 0.0, 500.0, 500.0)
COMM           = 150.0
DIAMETER_ESTIMATE         = 12    # conservative hop-count estimate of network diameter
QUERY_TIMEOUT_TOLERANCE_FRAC = 0.125  # 1/8 of diameter added as extra tolerance
QUERY_TIMEOUT_TOLERANCE   = max(1, round(DIAMETER_ESTIMATE * QUERY_TIMEOUT_TOLERANCE_FRAC))
QUERY_TIMEOUT  = 30 + QUERY_TIMEOUT_TOLERANCE   # rounds before abandoning a query
SPAWN_THRESHOLD = 1e-3       # spawn liveness threshold
```

### Python-side setup (`on_simulation_start`)

```python
from fcpp_bridge.examples.ex_utils import rnd_in_area, NodeStorage, spread_data_coprime_ID_pos

positions = rnd_in_area(N, AREA, seed=42)
storage: NodeStorage = {i: {} for i in range(N)}
spread_data_coprime_ID_pos(storage, positions, COMM, field='local_db')
# Push storage + positions as initial state to the swarm via IPC before round 1.
```

### Query and response routing

Two design options; the exercise should demonstrate **Option A** and mention **Option B**
as a variant:

**Option A — Reverse `spawn` (recommended)**

1. Requester sends a `spawn` keyed on `(requesting_nid, target_id)` with a small
   initial threshold. The spawn token propagates outward each round.
2. Each node that receives the spawn token checks whether `target_id` is in its
   `local_db`. If yes, it spawns a *response* token keyed on `(target_id, requesting_nid)`
   whose payload contains the data value.
3. The response token propagates back toward the requester. When it reaches the requester,
   `answer_ready = True` and `answer_value` is set.

Spawn key collision avoidance: include round number or a request sequence counter in
the key to allow the same node to re-query the same target across multiple rounds.

**Option B — `bis_distance` + `channel_broadcast`**

1. Requester treats itself as the `is_source` root; computes `bis_distance` gradient.
2. Responds via `channel_broadcast(is_source=True, value=data)` from the responder,
   which routes the data along the gradient toward the requester.
3. Simpler to implement but requires the responder to "know" the requester gradient,
   which in FCPP terms means the responder must be within the `bis_distance` spanning
   tree — guaranteed in a connected topology.

### `compute()` outline

```python
def compute(self, self_state, neighbors):
    # 1. Decide whether to start a new query this round.
    if self_state.query_target == -1 and not_all_known(self_state.local_db):
        target = pick_unknown_id(self_state.local_db, self_uid())  # noqa: F821
        return ScatteredDBState(
            ..., query_target=target, query_age=0, answer_ready=False, answer_value=None
        )

    # 2. Propagate / detect timeout.
    age = old(self_state.query_age) + 1                             # noqa: F821
    if age > QUERY_TIMEOUT:
        # abandon and start over next round
        return ScatteredDBState(..., query_target=-1, query_age=0)

    # 3. Spawn query token.
    query_token = spawn(                                             # noqa: F821
        key=(self_uid(), self_state.query_target),                  # noqa: F821
        threshold=SPAWN_THRESHOLD,
        value={'requester': self_uid(), 'target': self_state.query_target},  # noqa: F821
    )

    # 4. Check if we hold the queried data for any *incoming* request.
    # (Handled in the spawn sub-program: if local_db has the key, emit response.)

    # 5. Receive response (if any).
    answer_ready  = self_state.answer_ready   # updated by response spawn
    answer_value  = self_state.answer_value

    if answer_ready:
        new_db = dict(self_state.local_db)
        new_db[self_state.query_target] = answer_value
        return ScatteredDBState(..., local_db=new_db, query_target=-1, answer_ready=False)

    return ScatteredDBState(..., query_age=age)
```

### `AbstractExample` subclass

```python
class ScatteredDBExample(AbstractExample):
    @property
    def aggregate_class(self): return ScatteredDBAggregate

    def initial_positions(self): return rnd_in_area(N, AREA, seed=42)

    def on_simulation_start(self, swarm):
        positions = self.initial_positions()
        storage = {i: {} for i in range(N)}
        spread_data_coprime_ID_pos(storage, positions, COMM, field='local_db')
        swarm.set_initial_storage(storage)   # IPC command to pre-populate node state

    def on_round_complete(self, snapshot):
        completed = [n for n in snapshot.nodes
                     if n.state_data.get('answer_ready')]
        log.info("Round %d: %d nodes received a query answer",
                 snapshot.round_number, len(completed))
```

### Success criterion

After a configurable number of rounds, every node's `local_db` should contain at least
one entry it did not start with (demonstrating successful data exchange).

---

## Exercise 2: `area_discovery`

### Concept

A rectangular area is divided into a regular grid of square tiles. Each node claims its
"personal tile" (the tile whose centre is closest to the node's position). Nodes share
only their personal tile centre via `nbr` — they never broadcast the whole map.

Tile shapes (polygon corners) are stored inside `scattered_database` with the tile centre
as key. A node queries the database to learn its tile's shape, extending Exercise 1.

Constraint (simplest version): `n ≥ number_of_tiles`, so every tile has at least one node.

### New utility: `examples/ex_utils/tiles.py`

See §0. Also add `nearest_tile_center` call to the Python-side setup.

### State

```python
@dataclass
class AreaDiscoveryState(ScatteredDBState):
    # inherited: local_db, query_target, query_age, answer_ready, answer_value
    my_tile_center:        Optional[Tuple[float, float]]  # closest tile centre (constant after round 1)
    neighbors_tile_centers: FrozenSet[Tuple[float, float]] # tile centres from nbr (1-hop)
    tile_shape_known:       bool                           # True after DB answered the shape query
```

### Constants

```python
N          = 16
AREA       = (0.0, 0.0, 400.0, 400.0)
CELL_SIZE  = 100.0     # tile side length (must divide area evenly for simplest version)
COMM       = 150.0
```

### Python-side setup

```python
from fcpp_bridge.examples.ex_utils import (
    rnd_in_area, NodeStorage,
    grid_tile_centers, nearest_tile_center, compute_tile_shapes,
)

positions    = rnd_in_area(N, AREA, seed=42)
tile_centers = grid_tile_centers(AREA, CELL_SIZE)      # {tid: (cx, cy)}
tile_shapes  = compute_tile_shapes(tile_centers, AREA, CELL_SIZE)  # {(cx,cy): polygon}

storage: NodeStorage = {i: {} for i in range(N)}
for nid in storage:
    tc = nearest_tile_center(positions[nid], tile_centers)
    storage[nid]['local_db'] = {tc: tile_shapes[tc]}   # shard = just this node's tile shape
    storage[nid]['my_tile_center'] = tc
    storage[nid]['tile_shape_known'] = True             # already known from setup
```

Because every node starts with its own tile's shape in `local_db`, the `scattered_database`
query mechanism is needed only when a node wants a *neighbour's* tile shape — which
demonstrates the mechanism without requiring it for the primary function.

### `compute()` outline

```python
def compute(self, self_state, neighbors):
    # 1. Share personal tile centre with 1-hop neighbours.
    nbr_centers_field = nbr(self_state.my_tile_center)        # noqa: F821

    # 2. Collect received centres (1-hop only — no full-map broadcast).
    neighbors_centers = min_hood(nbr_centers_field)            # noqa: F821
    # Note: min_hood on tuples compares lexicographically; use fold_hood for a union.
    # For the exercise, collecting the set of received centres requires a custom fold:
    #   fold_hood(lambda a, b: a | {b}, nbr_centers_field, frozenset())
    # This translates to a C++ fold_hood with a lambda — valid DSL.

    # 3. ScatteredDB query for a neighbour's tile shape (extends Exercise 1).
    #    (Same logic as Exercise 1 but target key is a TileCenter tuple, not an int.)

    return AreaDiscoveryState(
        ...,
        my_tile_center        = self_state.my_tile_center,     # constant
        neighbors_tile_centers = frozenset(neighbors_centers),
        tile_shape_known      = self_state.tile_shape_known,
    )
```

### `on_round_complete` logging

Log the tile-coverage map: for each tile centre, how many nodes claim it. For a valid
placement (n ≥ num_tiles, positions spread reasonably), every tile should have exactly
one owner. If two nodes claim the same tile, the exercise surfaces a placement collision —
acceptable for learning purposes.

### Key learning goals

- `nbr` shares per-node scalar/tuple values; it does **not** share entire dicts.
- Tile-shape storage via `scattered_database` shows why a distributed key-value store
  is needed: no node holds the full map, yet the full map is collectively available.
- `fold_hood` with a set-union lambda is the correct idiom for collecting a neighbourhood
  set without `broadcast`.

---

## Exercise 3: `iteratively_area_discovery`

### Concept

Tiles outnumber nodes. Nodes must repeatedly explore tiles until all are covered:

1. A node with no tile: emit a query ("is this tile assigned?") toward the nearest
   unscanned tile. Wait up to `2 × diameter` rounds for a confirmation reply.
2. No reply → tile is unassigned → node claims it, moves toward its centre, sits still
   for `EXPLORE_TICKS` rounds (= "explores" it), then moves on.
3. Reply → tile already assigned → skip, try next candidate.
4. All nodes scatter their `first_ever_tile` (the first tile they ever started exploring)
   via `nbr`. This 1-hop sharing propagates knowledge of claimed tiles through the
   network, preventing duplicate assignments.

### Area variants

- **Version A** (simpler): rectangular area, `num_tiles` set so that 2–4× more tiles
  than nodes exist.
- **Version B** (advanced): area may be a non-self-intersecting polygon. Tile clipping
  uses `clip_polygon_to_polygon` from `tiles.py`.

### State

> ⚠️ **CORRECTION (higher-priority spec)**: The original plan included `first_ever_tile`
> and `known_assigned` fields. Both are **removed** and replaced by `assignment_db`
> (a second `scattered_database`). See the Anti-double-assignment protocol section below.

```python
@dataclass
class IterAreaDiscoveryState:
    # First scattered_database (from FE-9/FE-10): tile polygon shapes
    local_db:        Dict[TileCenter, Any]           # tile_center → tile_shape (explored tiles)
    # Second scattered_database (FE-11 new): assignment tracking
    assignment_db:   Dict[TileCenter, int]           # tile_center → assigned node ID
    # Area-discovery fields:
    my_tile:         Optional[TileCenter]            # current target tile centre (None = seeking)
    exploring_ticks: int                             # rounds spent on current tile (via old)
    pending_queries: Dict[TileCenter, int]           # tile_center → age; awaiting "is tile assigned?" reply
    status:          int                             # see STATUS_* constants below
```

```python
STATUS_SEEKING    = 0   # no tile, looking for an unassigned one
STATUS_MOVING     = 1   # moving toward my_tile centre
STATUS_EXPLORING  = 2   # at tile centre, counting down EXPLORE_TICKS
STATUS_DONE       = 3   # this node has finished all reachable tiles
```

### Constants

```python
N               = 10
AREA            = (0.0, 0.0, 600.0, 600.0)
CELL_SIZE       = 100.0
COMM            = 150.0
EXPLORE_TICKS   = 7      # rounds to "explore" a tile
MOVE_SPEED      = 15.0   # units/round (must be slow relative to COMM)
QUERY_TIMEOUT_MULT           = 2     # base timeout multiplier (2 × network_diameter)
QUERY_TIMEOUT_MARGIN         = 4     # extra rounds beyond base (+margin)
DIAMETER_ESTIMATE            = 12    # fallback constant if diameter cannot be computed live
QUERY_TIMEOUT_TOLERANCE_FRAC = 0.125  # 1/8 of diameter added as extra tolerance
QUERY_TIMEOUT_TOLERANCE      = max(1, round(DIAMETER_ESTIMATE * QUERY_TIMEOUT_TOLERANCE_FRAC))
```

### Network diameter

Diameter can be computed live (premium approach) or set as a constant (simpler):

```python
# Live (FCPP): root at an arbitrary source (node 0)
hop_dist = bis_distance(self_uid() == 0, 1.0, COMM)    # noqa: F821
diameter = broadcast(self_uid() == 0, max_hood(hop_dist))  # noqa: F821
timeout  = QUERY_TIMEOUT_MULT * int(diameter)
```

```python
# Constant fallback:
timeout = QUERY_TIMEOUT_MULT * DIAMETER_ESTIMATE
```

The exercise should implement the constant version first and note the live alternative.

### `compute()` outline — revised steps

> ⚠️ **CORRECTION (higher-priority spec)**: Step 1 (`nbr(first_ever_tile)` + `fold_hood`)
> is replaced. The anti-double-assignment mechanism now uses a second `scattered_database`
> (`assignment_db`) propagated via a 1-hop `spawn`. All `new_first` / `known_assigned`
> assignments are removed from every branch; the return no longer carries those fields.

```python
def compute(self, self_state, neighbors):

    # ── Step 1a: Receive incoming assignment spawns → update assignment_db ───
    # When a neighbour claims a tile, it emits a 1-hop spawn. The spawn liveness
    # function checks: hops_distance(spawner) ≤ 1 AND tile NOT IN assignment_db.
    # Each recipient inserts exactly once, then fails re-entry → no node at border.
    assignment_db = dict(self_state.assignment_db)
    # (Received spawn payloads {tile, node_id} are merged here by the framework.)

    # ── Step 1b: Emit 1-hop assignment spawn on new tile claim ───────────────
    if (self_state.status == STATUS_MOVING
            and self_state.my_tile is not None
            and self_state.my_tile not in assignment_db):
        assignment_db[self_state.my_tile] = self_uid()                  # noqa: F821
        spawn(                                                           # noqa: F821
            key=(self_uid(), self_state.my_tile, 'assign'),             # noqa: F821
            value={'tile': self_state.my_tile, 'node_id': self_uid()},  # noqa: F821
            threshold=SPAWN_THRESHOLD,
            # liveness: hops ≤ 1 AND tile NOT in recipient.assignment_db
        )

    # ── Step 2: Age pending "is tile assigned?" queries ──────────────────────
    timeout = QUERY_TIMEOUT_MULT * DIAMETER_ESTIMATE + QUERY_TIMEOUT_MARGIN + QUERY_TIMEOUT_TOLERANCE
    new_pending = {}
    unassigned_candidates = []
    for tile, age in self_state.pending_queries.items():
        new_age = age + 1
        if new_age > timeout:
            unassigned_candidates.append(tile)   # no reply → unassigned → election
        else:
            new_pending[tile] = new_age

    # ── Step 3: STATUS_SEEKING → query or claim via election ─────────────────
    if self_state.status == STATUS_SEEKING:
        if unassigned_candidates:
            # Election: distributed min-distance (analogous to FE-6 min-UID election).
            # Each candidate shares its distance to the best tile via nbr; wins iff
            # its distance ≤ min_hood(nbr distances).
            best_tile = min(unassigned_candidates,
                            key=lambda t: math.dist(self_pos(), t))     # noqa: F821
            dist_to_best = math.dist(self_pos(), best_tile)             # noqa: F821
            nbr_dists = nbr(dist_to_best)                               # noqa: F821
            is_winner = (dist_to_best <= min_hood(nbr_dists))           # noqa: F821
            if is_winner:
                my_tile = best_tile
                assignment_db[best_tile] = self_uid()                   # noqa: F821
                status  = STATUS_MOVING
            else:
                my_tile = self_state.my_tile
                status  = STATUS_SEEKING
        else:
            # Issue new "is tile assigned?" queries for unknown tile centres
            all_tile_centers = ...   # Python-side constant passed via state or storage
            unknowns = [t for t in all_tile_centers
                        if t not in assignment_db and t not in new_pending]
            for t in unknowns[:3]:   # query a few candidates per round
                new_pending[t] = 0
                spawn(key=(self_uid(), t, 'query'), threshold=SPAWN_THRESHOLD,  # noqa: F821
                      value={'q': t})
            my_tile = self_state.my_tile
            status  = STATUS_SEEKING

    # ── Step 4: STATUS_MOVING ────────────────────────────────────────────────
    elif self_state.status == STATUS_MOVING:
        follow_target(self_state.my_tile, MOVE_SPEED)                   # noqa: F821
        dist_to_tile = math.dist(self_pos(), self_state.my_tile)        # noqa: F821
        status  = STATUS_EXPLORING if dist_to_tile < CELL_SIZE / 2 else STATUS_MOVING
        my_tile = self_state.my_tile

    # ── Step 5: STATUS_EXPLORING ─────────────────────────────────────────────
    elif self_state.status == STATUS_EXPLORING:
        ticks = old(self_state.exploring_ticks) + 1                     # noqa: F821
        if ticks >= EXPLORE_TICKS:
            my_tile = None
            status  = STATUS_SEEKING
            # Store explored tile shape in local_db (from scattered_database)
        else:
            my_tile = self_state.my_tile
            status  = STATUS_EXPLORING

    # ── Step 6: STATUS_DONE ──────────────────────────────────────────────────
    else:
        my_tile = self_state.my_tile
        status  = STATUS_DONE

    exploring_ticks = self_state.exploring_ticks if status == STATUS_EXPLORING else 0

    return IterAreaDiscoveryState(
        ...,
        my_tile          = my_tile,
        assignment_db    = assignment_db,
        exploring_ticks  = exploring_ticks,
        pending_queries  = new_pending,
        status           = status,
    )
```

### Movement primitive note

`follow_target(target_pos, max_speed)` maps to `follow_target(CALL, target_pos, max_speed)`
in C++ (geometry.hpp). `self_pos()` — if needed — would need to be retrieved from the
node's own position (a C++-side field, not a DSL primitive). In the Python-side simulation
fallback, positions are updated manually in `on_round_complete`.

### `AbstractExample` subclass

```python
class IterAreaDiscoveryExample(AbstractExample):
    @property
    def aggregate_class(self): return IterAreaDiscoveryAggregate

    def initial_positions(self): return rnd_in_area(N, AREA, seed=7)

    def on_simulation_start(self, swarm):
        tile_centers = grid_tile_centers(AREA, CELL_SIZE)
        tile_shapes  = compute_tile_shapes(tile_centers, AREA, CELL_SIZE)
        storage = {i: {'local_db': {}, 'assignment_db': {},
                        'status': STATUS_SEEKING,
                        'pending_queries': {}, 'exploring_ticks': 0,
                        'my_tile': None}
                   for i in range(N)}
        swarm.set_initial_storage(storage)
        self._total_tiles = len(tile_centers)

    def on_round_complete(self, snapshot):
        explored = sum(1 for n in snapshot.nodes
                       if len(n.state_data.get('local_db', {})) > 0)
        done_nodes = sum(1 for n in snapshot.nodes
                         if n.state_data.get('status') == STATUS_DONE)
        log.info("Round %d: %d/%d tiles explored, %d nodes done",
                 snapshot.round_number, explored, self._total_tiles, done_nodes)
        if explored >= self._total_tiles:
            log.info("All tiles explored — simulation complete.")
            swarm.stop()
```

### Anti-double-assignment protocol (revised — second `scattered_database`)

> ⚠️ **CORRECTION (higher-priority spec)**: The original protocol used `first_ever_tile`
> scattered via `nbr` + `fold_hood` accumulation. That mechanism is **replaced** by the
> protocol below. `first_ever_tile` and `known_assigned` state fields are removed;
> `assignment_db` replaces both.

A **second distributed key-value store** (`assignment_db`) tracks tile assignments
separately from the tile-shape DB (`local_db` from FE-9/FE-10):

| DB | Keys | Values |
|----|------|--------|
| `local_db` | `TileCenter` | tile polygon (shape) |
| `assignment_db` (new) | `TileCenter` | assigned node ID (`int`) |

#### Filling `assignment_db` (assignment propagation)

When node `n` claims tile `t` (transitions `SEEKING → MOVING` after winning election):

1. Node `n` inserts `(t → n_id)` into its own `assignment_db`.
2. Node `n` emits a **1-hop `spawn`** keyed on `(n_id, t, 'assign')`.
3. The spawn's **liveness function** checks two conditions for each candidate node `c`:
   - `hops_distance(n, c) ≤ 1` — limits scope to the immediate neighbourhood only.
   - `t NOT IN c.assignment_db` — once `c` inserts the entry, re-evaluation fails
     → `c` exits the spawn immediately (**no node ever stays "at the border"**).
4. Any `c` satisfying both conditions inserts `(t → n_id)` and exits.

**Optimisation (verbatim from spec)**: place the entire insert operation inside the
spawned sub-program. The liveness guard becomes the insert guard — a node either
participates (inserts + exits) or is excluded entirely. This avoids a separate
border-detection step. Successive `assignment_db` inclusion tests fail after the tile
centre is inserted, so the condition is self-enforcing.

#### Querying `assignment_db` (double-assignment avoidance)

Before a node claims tile `t`:

1. **Local check**: if `t in assignment_db` → tile already assigned; skip `t`.
2. **Network query** (if not in local DB): emit a query spawn; wait up to
   `QUERY_TIMEOUT_MULT × DIAMETER_ESTIMATE + QUERY_TIMEOUT_MARGIN + QUERY_TIMEOUT_TOLERANCE` rounds.
3. **Reply received** → tile is assigned; update local `assignment_db`; skip `t`.
4. **Timeout** → tile is unassigned → **distributed election**:
   - Each candidate computes Euclidean distance to `t`'s centre.
   - Share via `nbr`; `min_hood` selects the minimum.
   - A node wins iff its distance `≤ min_hood(nbr_distances)`
     (same idiom as FE-6 min-UID election, keyed on distance instead of UID).
   - Winner claims `t`, transitions to `STATUS_MOVING`, emits the 1-hop
     assignment spawn described above.

### Version B extension (non-rectangular area)

1. The area boundary is given as an ordered list of vertices (polygon).
2. Replace `grid_tile_centers(area, cell_size)` with a polygon-aware version that only
   yields tile centres strictly inside the polygon.
3. Replace border tile clipping from `clip_rect_to_rect` to `clip_polygon_to_polygon`
   (Sutherland-Hodgman, already planned in `tiles.py`).
4. The FCPP algorithm is identical; only the Python-side tile initialisation changes.

---

## Open Design Questions

| # | Question | Recommended resolution |
|---|----------|------------------------|
| 1 | **Response routing in `scattered_database`**: reverse `spawn` vs `bis_distance` + `channel_broadcast`? | Start with reverse `spawn` (more general, no bi-directional gradient required). Add `channel_broadcast` as a commented-out variant. |
| 2 | **Diameter estimation**: live FCPP primitive vs constant? | Constant for the exercise; note the live version with `max_hood(bis_distance(...))` + `broadcast` as an advanced extension. |
| 3 | **`fold_hood` with set-union lambda**: does the transpiler support complex lambdas as `fold_hood` args? | Yes — `visit_Lambda` emits C++14 generic lambdas `[=](auto a, auto b){...}`. Verify that `frozenset` folding transpiles correctly after v1.9-A. |
| 4 | **`self_pos()` in `compute()`**: FCPP does not expose node position as a DSL primitive; geometry primitives (e.g., `follow_target`) implicitly use it. | Leave movement and distance-to-tile-centre as Python-side computations in the fallback; document that in a full FCPP deployment, the C++ runtime provides node position automatically. |
| 5 | **Polygon support (Version B)**: is a non-convex polygon ever used? | The user spec says "non-self-intersecting polygon" — which may be non-convex. Sutherland-Hodgman requires a convex clip boundary. For non-convex areas, decompose into convex sub-polygons and union the results. Include this note in `tiles.py`. |
| 6 | **1-hop spawn liveness for assignment propagation**: how to restrict a `spawn` to exactly 1-hop neighbours and prevent re-entry into `assignment_db`? | Two complementary mechanisms: (a) set spawn threshold to decay below `SPAWN_THRESHOLD` after 1 hop (e.g. `value × 0.0005`), limiting geographic reach; (b) include a DB membership guard in the spawned sub-program body (`if tile not in assignment_db: insert(…)`), preventing double-insertion without relying solely on liveness decay. Both conditions from the spec are satisfied. Verify that the transpiler handles stateful closure captures in liveness lambdas. |

---

## Files to Create / Modify

| Action | File | Contents |
|--------|------|----------|
| **Create** | `examples/ex_utils/tiles.py` | `grid_tile_centers`, `nearest_tile_center`, `compute_tile_shapes`, `clip_rect_to_rect`, `clip_polygon_to_polygon` |
| **Update** | `examples/ex_utils/__init__.py` | Re-export tile utilities |
| **Create** | `examples/scattered_database.py` | `ScatteredDBState`, `ScatteredDBAggregate`, `ScatteredDBExample` |
| **Create** | `examples/area_discovery.py` | `AreaDiscoveryState`, `AreaDiscoveryAggregate`, `AreaDiscoveryExample` |
| **Create** | `examples/iteratively_area_discovery.py` | `IterAreaDiscoveryState`, `IterAreaDiscoveryAggregate`, `IterAreaDiscoveryExample`, `STATUS_*` constants |
