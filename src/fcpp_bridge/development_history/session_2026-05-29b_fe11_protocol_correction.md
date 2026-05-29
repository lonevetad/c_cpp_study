# Session 2026-05-29b — FE-11 anti-double-assignment protocol correction

## Summary

The FE-11 (`iteratively_area_discovery`) anti-double-assignment protocol described in
`EXERCISES_PLAN.md` had a mistake. The protocol has been corrected per the higher-priority
spec provided in the session.

---

## Correction

**Original (wrong)**: Nodes scatter `first_ever_tile` (the first tile ever claimed, immutable)
via `nbr` + `fold_hood` accumulation into a `known_assigned` frozenset. A claim spawn token
added tiles to `known_assigned` per recipient.

**Correct**: A **second `scattered_database`** (`assignment_db: Dict[TileCenter, int]`) is used.
`first_ever_tile` and `known_assigned` are removed from the state entirely.

---

## Corrected protocol

### `assignment_db` structure

| DB | Keys | Values |
|----|------|--------|
| `local_db` (FE-9/10) | `TileCenter` | tile polygon shape |
| `assignment_db` (FE-11 new) | `TileCenter` | assigned node ID (`int`) |

Holds all tiles known to be assigned (from the current node's perspective), populated
by local claims and by incoming 1-hop spawn payloads from neighbours.

### Filling `assignment_db` (assignment propagation)

When node `n` claims tile `t`:

1. Node `n` inserts `(t → n_id)` into its own `assignment_db`.
2. Node `n` emits a **1-hop `spawn`** keyed `(n_id, t, 'assign')`.
3. Spawn liveness function for each candidate node `c`:
   - `hops_distance(n, c) ≤ 1` — only immediate neighbours
   - `t NOT IN c.assignment_db` — once inserted, re-evaluation fails → `c` exits
4. Any `c` satisfying both conditions inserts `(t → n_id)` and immediately exits.

No node stays at the spawn boundary. The entire operation is self-terminating.

**Optimisation**: place the insert inside the spawned sub-program — the liveness guard
acts as the insert guard. Either a node participates (inserts + exits) or is excluded.

### Querying (double-assignment avoidance)

Before claiming tile `t`:

1. Local check: `t in assignment_db` → assigned, skip.
2. Network query spawn with timeout `QUERY_TIMEOUT_MULT × DIAMETER_ESTIMATE + QUERY_TIMEOUT_MARGIN`.
3. Reply → assigned; update local DB; skip.
4. Timeout → unassigned → **distributed election**:
   - Each candidate shares its Euclidean distance to `t`'s centre via `nbr`.
   - `min_hood` picks the minimum.
   - Winner: node whose distance `≤ min_hood(nbr_distances)`.
   - Winner claims `t`, transitions to `STATUS_MOVING`, emits 1-hop spawn.

---

## State changes

**Removed**: `first_ever_tile: Optional[TileCenter]`, `known_assigned: FrozenSet[TileCenter]`

**Added**: `assignment_db: Dict[TileCenter, int]`

---

## Constants added

`QUERY_TIMEOUT_MARGIN = 4` — extra rounds beyond `2 × diameter` (the "+margin" from spec).

---

## Files changed

| File | Change |
|------|--------|
| `development_history/EXERCISES_PLAN.md` | State dataclass corrected; constants: added `QUERY_TIMEOUT_MARGIN`; `compute()` outline: Steps 1a/1b replace old Step 1, return drops `first_ever_tile`/`known_assigned`, adds `assignment_db`; anti-double-assignment section: full rewrite with correction note; `on_simulation_start`: removed old fields, added `assignment_db`; Open Design Questions: added Q6 (1-hop spawn liveness) |
| `development_history/FUTURE_EXERCISES.md` | FE-11 entry: DSL primitives updated (`fold_hood` → `min_hood`); description updated to second-DB protocol |
| `memory/project_fcpp_bridge.md` | FE-11 row and design decisions updated |
