# fcpp_bridge — Future Exercise Hints

This file collects hints for future development sessions.
Each entry was noted as a "future exercise" during the writing of an existing example.
Entries are grouped by origin and roughly ordered from simpler to more complex.

> **FE-9, FE-10, FE-11** (the `scattered_database` → `area_discovery` →
> `iteratively_area_discovery` series) are documented in full detail in
> [`EXERCISES_PLAN.md`](EXERCISES_PLAN.md).
> The summary entries below serve as index entries only.

---

## From `communication_roles_assignment.py`

### FE-1: Multiple independent communication instances (spawn)
**Complexity**: High
**DSL primitives involved**: `spawn`, `old`, `bis_distance`, `broadcast`

The current exercise defines a single set of roles for a single communication process.
A natural extension is to allow multiple concurrent, independent communication processes
(e.g., 3 active Sender→Receiver channels at the same time).

In this scenario:
- A node may have different roles in different communication processes simultaneously
  (e.g., REPEATER for process A, SENDER for process B).
- The `spawn` primitive is well-suited for creating a per-process aggregate sub-program
  that runs only on nodes relevant to that process.
- Each spawned process would carry its own routing gradient and message state.
- The challenge is determining the spawn key (a unique identifier per communication
  instance) and handling process lifecycle (start, relay, terminate).

This is a natural follow-on to `message_dispatch.py` (which already uses `spawn`)
and `worker_role_assignment.py` (which uses `spawn` for per-endpoint routing).

---

### FE-2: Dynamic sink/source points (changing over time)
**Complexity**: Medium
**DSL primitives involved**: `broadcast`, `old`, `bis_distance`

The current exercise uses fixed sink/source points (set at initialisation, never changed).
A more realistic scenario would have sink/source points move or appear/disappear over time:
- After a configurable number of ticks (e.g., 35), reassign sink/source points to new locations.
- Roles would need to re-converge after the change — this tests the algorithm's adaptability.
- The `old` primitive can be used to detect when the point location changes
  (compare current with previous; if different, reset the role election).

---

### FE-3: Mobile nodes searching for sink/source points
**Complexity**: High
**DSL primitives involved**: `rectangle_walk` (or custom movement), `bis_distance`, `old`

In the current exercise, all nodes know the sink/source point locations from the start.
A more realistic scenario:
- Nodes start with no knowledge of sink/source point locations.
- Nodes wander (using `rectangle_walk` or a directed search algorithm) to discover points.
- When a node detects a point (within some sensing radius), it broadcasts its discovery.
- Other nodes update their role based on this discovery broadcast.

This also naturally introduces a "search and converge" phase before the communication
phase, making the simulation more dynamic and true to a real rescue-swarm scenario.

---

### FE-4: Area partition + node scanning assignment
**Complexity**: Very High
**DSL primitives involved**: `bis_distance`, `sp_collection`, `broadcast`, `spawn`, `old`

A complex two-phase algorithm:
- **Phase 1 (Area partition)**: The swarm collectively divides the deployment area into
  regions, one per node (a Voronoi-style partition based on node positions).
- **Phase 2 (Scanning assignment)**: Each node is assigned its own region to scan;
  it navigates through the region to cover it fully.

Phase 2 is a follow-on to Phase 1 — a node needs its assigned region boundary before
it can plan a scanning path.

This exercise would be significant in scope; it would likely warrant its own design
document before implementation.

---

## From `worker_role_assignment.py`

### FE-5: Dynamic Receiver count via broadcast
**Complexity**: Medium
**DSL primitives involved**: `broadcast`, `bis_distance`, `old`

Currently in `worker_role_assignment.py`, the spawn key for a message uses
`(self_uid(), 0)` where `0` is a placeholder for the receiver's UID.
A proper fix (tracked as v1.9 plan item) involves broadcasting the actual
RECEIVER UID back to all Senders:
```python
receiver_uid = broadcast(is_receiver, self_uid())
```
This could be demonstrated as a standalone "v1.9 example" that shows the corrected
spawn key.

---

### FE-6: Role election among candidates (distributed min-UID election)
**Complexity**: Medium
**DSL primitives involved**: `nbr`, `min_hood`, `old`, `bis_distance`

A generalisation of the Sender election in `communication_roles_assignment.py`:
a distributed algorithm where an arbitrary number of nodes are candidates for a
single leadership role, and the network converges to elect exactly one leader
(the one with the globally minimum UID, or minimum distance to a target).

This is a classic distributed algorithms exercise and a natural showcase for
`nbr + min_hood + old` combined.

---

## From project-level observations

### FE-7: Store-and-forward Repeater with TTL
**Complexity**: Medium
**DSL primitives involved**: `nbr`, `old`, `bis_distance`

The current `communication_roles_assignment.py` relies on `broadcast` to propagate
messages, which means Repeaters do not explicitly forward; the primitive handles it.
An alternative — more educational for demonstrating `old` and explicit relay logic — is:
- Each Repeater maintains a buffer (via `old`) of messages it has seen.
- When a message expires (TTL reaches 0), it is dropped from the buffer.
- Repeaters actively forward buffer contents to neighbors each round.
This is reminiscent of `chain_decaying.py` but generalised to message payloads.

---

### FE-8: Adaptive communication range (power control)
**Complexity**: Low-Medium
**DSL primitives involved**: `count_hood`, `nbr`, `old`

Nodes adjust their effective communication radius based on local density:
- In dense areas: reduce radius to save energy and avoid redundant relays.
- In sparse areas: increase radius to maintain connectivity.
- Use `count_hood()` to estimate local density and `old` to smooth changes over time.

A simple showcase for `count_hood` + `old` without complex routing.

---

## Planned exercise series — `ex_utils` → distributed data & area coverage

> Full design: [`EXERCISES_PLAN.md`](EXERCISES_PLAN.md)

### FE-9: `scattered_database`
**Complexity**: High  
**DSL primitives**: `spawn`, `old`, `bis_distance`, `broadcast`, `nbr`, `min_hood`  
**Builds on**: `spread_data_coprime_ID_pos` (ex_utils)

Emulates a sharded, distributed, replicated key-value store. Each node holds a coprime-
neighbour shard (populated by `spread_data_coprime_ID_pos`). When a node needs an entry
it does not own, it sends a query via `spawn`; the holder routes the value back via a
reverse `spawn` (or `bis_distance` + `channel_broadcast`).

---

### FE-10: `area_discovery`
**Complexity**: High  
**DSL primitives**: `nbr`, `fold_hood` + all of FE-9  
**Builds on**: FE-9, `ex_utils/tiles.py` (new)

A rectangular area is divided into a regular grid. Each node claims its nearest tile
centre and shares only that centre via `nbr` (never the full map). Tile shapes (polygon
corners) are stored as `scattered_database` values keyed on tile centre. One node per
tile is guaranteed (`n ≥ num_tiles`).

---

### FE-11: `iteratively_area_discovery`
**Complexity**: Very High  
**DSL primitives**: `spawn`, `old`, `nbr`, `min_hood`, `bis_distance`, `follow_target` + all of FE-10  
**Builds on**: FE-10

Tiles outnumber nodes. Nodes iteratively claim, move to, and explore tiles
(`EXPLORE_TICKS = 7`). Double-assignment is prevented by a **second
`scattered_database`** (`assignment_db: {tile_center → node_id}`): when a node claims
a tile, it propagates the assignment to 1-hop neighbours via a self-terminating 1-hop
`spawn` (liveness: `hops ≤ 1 AND tile NOT IN recipient.assignment_db`). A
query-with-timeout protocol (`2 × diameter + margin` rounds) verifies whether a tile
is unassigned; on timeout, a distributed min-distance election (node closest to tile
centre wins, via `nbr` + `min_hood`) determines the claimant. Supports rectangular
(Version A) and non-self-intersecting polygon (Version B) areas.
