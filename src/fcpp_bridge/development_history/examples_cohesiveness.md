# fcpp_bridge — Examples Folder Cohesiveness Plan

**Created**: 2026-05-28
**Status**: Approved / being executed

---

## 1. Scope

This document analyses the six "main" example files (those with a full `_demo_simulate()` +
`main()` structure and `@aggregate_function` aggregate classes) and the shared
`examples/_example_utils.py`.  The four early-stage examples
(`simple_averaging.py`, `gossip_protocol.py`, `distance_broadcast.py`, `end_to_end.py`)
follow a different, minimal pattern and are out-of-scope for this refactoring.

Main examples in scope:

| File | DSL primitives |
|---|---|
| `spreading_collection.py` | `rectangle_walk`, `abf_distance`, `mp_collection`, `broadcast` |
| `channel_broadcast.py` | `rectangle_walk`, `bis_distance` ×2, `broadcast` |
| `collection_compare.py` | `rectangle_walk`, `abf_distance`, `sp_collection`, `mp_collection`, `wmp_collection` |
| `message_dispatch.py` | `rectangle_walk`, `bis_distance`, `min_hood`, `sp_collection`, `spawn`, `old` |
| `chain_decaying.py` | `nbr`, `min_hood` |
| `worker_role_assignment.py` | `bis_distance`, `nbr`, `min_hood`, `count_hood`, `sp_collection`, `spawn`, `old`, `self_uid()` |

---

## 2. Repeated-Code Inventory

### 2.1 `neighbors_of` inner function — **duplicated in all 6 examples**

Every `_demo_simulate()` defines a closed-over helper:

```python
def neighbors_of(nid):           # slight signature variations across files
    x, y = positions[nid]
    return [
        j for j in range(DEVICES / NUM_NODES)
        if j != nid and math.dist((x, y), positions[j]) <= COMM
    ]
```

Variations observed:
- `spreading_collection.py`: no type hint, uses `NUM_NODES`
- `channel_broadcast.py`: no type hint, uses `DEVICES`
- `collection_compare.py`: no type hint, uses `NUM_NODES`
- `message_dispatch.py`: no type hint, uses `DEVICES`
- `chain_decaying.py`: `nid: int -> list[int]`, uses `NUM_NODES`
- `worker_role_assignment.py`: `nid: int -> list`, uses `DEVICES`

The function body is identical in structure. The only differences are:
1. The set of node IDs to iterate (`range(DEVICES)` vs `range(NUM_NODES)`) — solved by iterating `positions.keys()` instead
2. Whether a type hint is present

**Proposed shared version** (`_example_utils.py`):
```python
def neighbors_of(positions: dict, nid: int, comm: float) -> list[int]:
    """Return IDs of all nodes within comm radius of nid (excluding self)."""
    return [j for j in positions if j != nid and math.dist(positions[nid], positions[j]) <= comm]
```

---

### 2.2 Spawn status constants — **duplicated in 2 examples, needed in new ones**

`message_dispatch.py` and `worker_role_assignment.py` both define:

```python
STATUS_BORDER = 0
STATUS_INTERNAL = 1
STATUS_TERMINATED = 2
```

These mirror `fcpp::status::border`, `fcpp::status::internal`, `fcpp::status::terminated_output`.

**Proposed shared constants** (`_example_utils.py`):
```python
SPAWN_STATUS_BORDER = 0      # fcpp::status::border
SPAWN_STATUS_INTERNAL = 1    # fcpp::status::internal
SPAWN_STATUS_TERMINATED = 2  # fcpp::status::terminated_output
```

The per-file names (`STATUS_BORDER`, etc.) will be kept as local aliases for backwards
compatibility, pointing at the shared constants.

---

### 2.3 Node-position initialization — **near-identical in 5 examples**

All `_demo_simulate()` functions except `chain_decaying.py` build a positions dict like:

```python
positions = {
    i: (random.uniform(0.0, SIDE), random.uniform(0.0, SIDE))
    for i in range(NUM_NODES)   # or DEVICES
}
```

**Proposed helper** (`_example_utils.py`):
```python
def build_positions(
    n: int, side_x: float, side_y: float | None = None,
    *, seed: int | None = None,
) -> dict[int, tuple[float, float]]:
    """Build a random 2-D positions dict for n nodes in [0,side_x] × [0,side_y]."""
```

This is lower-priority than `neighbors_of` (less savings, more API surface). Included in
plan but marked *optional*.

---

### 2.4 Log-file opening header — **repeated pattern, not extracted yet**

Every `_demo_simulate()` contains:
```python
LOG_DIR.mkdir(exist_ok=True)
lf = open(log_path, "w")
lf.write(f"# <example name> — node {nid}\n# round,...\n")
```

Extracting this into a helper would reduce boilerplate but also risks making the log
format less visible to the reader.  **Deferred** — not part of this refactoring pass.

---

### 2.5 Simulation constants — **convention documented, not shared**

| Constant | Present in | Value |
|---|---|---|
| `COMM` | all 6 | varies (80–100) |
| `SIDE` | all 6 | varies |
| `HEIGHT` | 4 of 6 | varies |
| `SPEED` | 5 of 6 | varies |
| `NUM_ROUNDS` | all 6 | varies |
| `LOG_DIR` | all 6 | always `Path(__file__).parent / "logs"` |

`LOG_DIR` is identical in all 6 files but depends on `__file__`, so it cannot be usefully
shared.  All constants differ semantically per example; sharing them would create
confusing dependencies.  **No action** — just document the convention.

Node-count naming inconsistency (`NUM_NODES` vs `DEVICES`) is cosmetic; do **not** rename
existing examples to avoid unnecessary churn.  New examples should use `NODES` (shorter,
unambiguous).

---

### 2.6 `RoleCommunicationType` (worker_role_assignment) vs `CommunicationRole` (new example)

`worker_role_assignment.py` defines `RoleCommunicationType` with three values:
`ENDPOINT(0) / RECEIVER(1) / REPEATER(2)`.

The new `communication_roles_assignment.py` example defines `CommunicationRole` with four
values: `UNASSIGNED(0) / SENDER(1) / REPEATER(2) / RECEIVER(3)`.  The semantics are
related but not identical (`ENDPOINT → SENDER`; `UNASSIGNED` is new).  **Not shared** —
kept as two separate enums.  The relationship is documented in the EXAMPLES_JOURNAL.

---

## 3. Refactoring Actions

### 3.1 `_example_utils.py` additions

| Addition | Priority | Notes |
|---|---|---|
| `neighbors_of(positions, nid, comm)` | **required** | Removes 6 duplicate inner functions |
| `SPAWN_STATUS_BORDER/INTERNAL/TERMINATED` | **required** | Removes 2 duplicate constant blocks |
| `build_positions(n, side_x, side_y, seed)` | optional | Low priority; saves ~3 lines/file |

### 3.2 Per-example changes

All changes are **minimal**: only replace the duplicated code with the shared version.
No algorithmic, structural, or docstring changes.

| File | Change |
|---|---|
| `spreading_collection.py` | Import `neighbors_of`; remove inner `neighbors_of`; call as `neighbors_of(positions, nid, COMM)` |
| `channel_broadcast.py` | Same |
| `collection_compare.py` | Same |
| `message_dispatch.py` | Same + import `SPAWN_STATUS_BORDER/INTERNAL/TERMINATED`; keep local `STATUS_*` aliases |
| `chain_decaying.py` | Same (neighbors_of only) |
| `worker_role_assignment.py` | Same (neighbors_of + status constants + local aliases) |

---

## 4. New Example: `communication_roles_assignment.py`

Created after applying the above refactoring.  Uses:
- `neighbors_of` from `_example_utils` (no local re-definition)
- `SPAWN_STATUS_BORDER/INTERNAL/TERMINATED` (if spawn is used)
- `CommunicationRole` enum (defined locally — see §2.6)
- `bis_distance` ×2, `nbr`, `min_hood`, `old` ×2, `broadcast`, `match/case`

Detailed design: see `EXAMPLES_JOURNAL.md` → `communication_roles_assignment.py` section.
Future exercise hints: see `FUTURE_EXERCISES.md`.

---

## 5. Execution Order

1. ✅ This document written
2. Update `_example_utils.py` — add `neighbors_of` + status constants
3. Update 6 existing examples — use shared helpers
4. **Save session checkpoint #1**
5. Create `communication_roles_assignment.py`
6. Create `FUTURE_EXERCISES.md`
7. Update `EXAMPLES_JOURNAL.md`
8. **Save session checkpoint #2** + update memory

---

## 6. Out-of-Scope Items

The following were considered but explicitly excluded:

- Refactoring `distance_broadcast.py`, `simple_averaging.py`, `gossip_protocol.py`,
  `end_to_end.py` — different structural pattern; no shared boilerplate with the main 6
- Unifying `NUM_NODES` / `DEVICES` naming across existing files — unnecessary churn
- Merging `_demo_simulate` scaffolding into a framework class — over-engineered for demos
- Moving `LOG_DIR` to `_example_utils` — depends on `__file__`, cannot be shared cleanly
