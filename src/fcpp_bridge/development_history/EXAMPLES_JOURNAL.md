# fcpp_bridge — C++ → Python Examples Journal

**Goal**: For each high-level/complex C++ FCPP algorithm example, create a Python
`fcpp_bridge` equivalent that demonstrates the same algorithm using the Python DSL.
Additionally, create original DSL-showcase examples that highlight specific language
features (e.g. `match/case`, `spawn`, `old`).
Each Python file is for **demonstration and learning purposes** and includes explanatory
comments.

**Run an example** (once compilation pipeline is set up):
```bash
cd <repo-root>
PYTHONPATH=src python src/fcpp_bridge/examples/<example>.py
```

Per-node log files are written to `src/fcpp_bridge/examples/logs/`.

---

## Status

| Python file | C++ source / origin | Key primitives | Status |
|---|---|---|---|
| `spreading_collection.py` | `fcpp-sample-project/lib/spreading_collection.hpp` | `rectangle_walk`, `abf_distance`, `mp_collection`, `broadcast` | ✅ Done |
| `channel_broadcast.py` | `fcpp-sample-project/lib/channel_broadcast.hpp` | `rectangle_walk`, `bis_distance`, `broadcast` | ✅ Done |
| `collection_compare.py` | `fcpp-sample-project/lib/collection_compare.hpp` | `rectangle_walk`, `abf_distance`/`bis_distance`/`flex_distance`, `sp_collection`, `mp_collection`, `wmp_collection` | ✅ Done |
| `message_dispatch.py` | `fcpp-sample-project/lib/message_dispatch.hpp` | `rectangle_walk`, `bis_distance`, `sp_collection`, `spawn`, `old` | ✅ Done |
| `chain_decaying.py` | `fcpp-sample-project/run/chain_decaying.hpp` + `fcpp-exercises/run/chain_decaying.hpp` | `nbr`, `min_hood` | ✅ Done |
| `worker_role_assignment.py` | **original** — v1.5/v1.6/v1.7 DSL showcase | `bis_distance`, `nbr`, `min_hood`, `count_hood`, `sp_collection`, `spawn`, `old`, `self_uid()` + `match/case` + `RoleCommunicationType` | ✅ Done |

---

## C++ source inventory

### Collected as high-level / complex algorithm examples:

| C++ file | Location | Algorithm |
|---|---|---|
| `spreading_collection.hpp` | `fcpp-sample-project/lib/` | Distance spreading + diameter collection + broadcast |
| `channel_broadcast.hpp` | `fcpp-sample-project/lib/` | Elliptical channel detection using BIS distances |
| `collection_compare.hpp` | `fcpp-sample-project/lib/` | Compares SP / MP / WMP collection algorithms |
| `message_dispatch.hpp` | `fcpp-sample-project/lib/` | Spawn-based point-to-point message routing |
| `chain_decaying.hpp` | `fcpp-sample-project/run/` and `fcpp-exercises/run/` | TTL-based decaying chain with `nbr` |

### Excluded as learning-focused exercises:

| C++ file | Reason |
|---|---|
| `exercises.cpp`, `exercises_3.cpp`, `exercises_4.cpp` | Explicitly numbered TODO exercises with partial solutions |
| `exercises_1_mountains_peaks.cpp` | Exercise template with peak-detection solution only partially filled |
| `exercises_old_phd_1.cpp` | Early exercise scaffold from PhD course |
| `es_basics.cpp`, `es_01.cpp` | Basic exercise templates |
| `apartment_walk.cpp` | Uses `node.net.is_obstacle()` / `node.net.closest_obstacle()` (navigator component, not aggregate primitives) |
| `spreading_collection_batch.cpp`, `spreading_collection_gui.cpp`, `spreading_collection_mpi.cpp`, `spreading_collection_run.cpp` | Simulation runner variants for `spreading_collection.hpp` — algorithm is in the shared header |

---

## Algorithm notes per example

### spreading_collection.py
- **Source selection**: original C++ rotates source every 50 simulated seconds using
  `node.current_time()`. Python port uses a static source (`is_source` flag in state).
- **State type**: `SpreadingState` dataclass — 4 fields: `is_source`, `calc_distance`,
  `source_diameter`, `diameter`.

### channel_broadcast.py
- **Source / destination**: C++ hardcodes device 0 as source, device 1 as destination.
  Python port carries `is_source` and `is_dest` in state.
- **Channel condition**: `ds + dd < broadcast(ds, dd) + width` — the broadcast of
  ds (distance-to-source) gives the source-to-destination straight-line distance, so
  the ellipse condition comes from the sum of both distances.

### collection_compare.py
- **Three distance algorithms**: ABF (`abf_distance`), BIS (`bis_distance`), FLEX
  (`flex_distance`) — C++ selects via a `dist_algo` storage tag. Python port
  always uses `abf_distance` (algorithm 0) for simplicity.
- **Two case studies**: `device_counting` (sum=1.0 per node) and `progress_tracking`
  (max=value derived from position + time).

### message_dispatch.py
- **Spawn**: the C++ uses `spawn(CALL, lambda, msg)` to create per-message aggregate
  processes that route across the spanning tree. Python port demonstrates `spawn` with
  the same lambda structure; the demo simulation approximates routing.
- **Message struct**: simplified to `tuple[int, int, int]` (from, to, time).

### chain_decaying.py
- **Custom algorithm**: the original `is_alive_decaying` template uses `nbr` with a
  complex in-place-mutating lambda. Python port calls `nbr` with an equivalent lambda
  that returns the updated 4-tuple `(should_hold, hops, ttl, next_uid)`.
- **Source condition**: `is_source = (node_uid % 17 == 0)` — same as original.

### worker_role_assignment.py
- **Origin**: original DSL-showcase example (not ported from C++); designed to exercise
  the `match/case` → `switch`, `spawn`/`old`, (v1.6) `self_uid()`, and (v1.7)
  `RoleCommunicationType` features.
- **Role assignment**: `role = node_id % 8` gives 3 nodes per role with `DEVICES = 24`.
  Endpoint roles (2, 3, 5, 6, 7): LIDAR, INFRARED_SENSOR, TORCHLIGHT_MICROPHONE,
  RUBBLES_REMOVER, FLYING_OVERSEER.  Receiver role (1): RECEIVER base station.
  Repeater roles (0, 4): UNASSIGNED (passive), REPEATER (active relay).
- **RoleCommunicationType** (v1.7): new enum (ENDPOINT=0, RECEIVER=1, REPEATER=2)
  associated with each WorkerRole via `ROLE_COMM_TYPE` dict.  Endpoint nodes gather
  sensor data and inject readings; repeater nodes relay data without originating it.
- **CALL-counter constraint**: all 7 CALL-based primitives (`bis_distance`, `nbr`,
  `min_hood`, `count_hood`, `sp_collection`, `spawn`, `old`) are called before the
  `match/case` block.  Placing primitives inside switch branches would desynchronise the
  FCPP `CALL` counter across nodes and produce incorrect C++ behavior.
- **Integer case labels**: Python 3.10+ bare names in `case NAME:` are capture patterns
  (always match); integer literals `case 0:`, `case 1:`, … are value patterns (correct).
- **self_uid()** (v1.6): `self_uid()` → `node.uid` in generated C++ (no CALL counter);
  used in step 2 (tie-breaking), step 4 (sp_collection local value), step 5 (spawn key
  sender half).  Receiver UID in spawn key is still `0` (placeholder — v1.9 fix planned).
- **Step 7 role tasks**: each `match/case` branch contains a role-specific task
  description and a local placeholder variable; tasks without a real-world implementation
  are marked with `# [Placeholder]` comments.
- **routing_set_size repurposing**: LIDAR (2) and REPEATER (4) store `count_hood()`
  (coverage metric); UNASSIGNED (0) stores `0` (passive); all other roles store
  `len(sp_collection set)`.
- **v1.8**: `main()` uses shared `report_validation`/`report_transpilation` helpers from
  `examples/_example_utils.py`; no algorithm changes.
- **Full design notes**: `development_history/WORKER_ROLE_ASSIGNMENT.md` — scenario,
  algorithm table, DSL feature rationale, limitations, 7 evolution paths.
- **v1.9 plan**: `development_history/V1_9_PLAN.md` — receiver UID fix via `broadcast`,
  `frozenset` → `set_t` transpilation, `min_hood` tuple → `std::make_tuple`, and more.

---

## Resume instructions

If interrupted, check the **Status** table above. Find the first ⬜ Pending row and
continue from there. After each file is written, run:

```bash
PYTHONPATH=src python -c "import fcpp_bridge.examples.spreading_collection"
```

(or the relevant module) to verify the import does not crash.
