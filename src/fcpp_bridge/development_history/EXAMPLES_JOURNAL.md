# fcpp_bridge — C++ → Python Examples Journal

**Goal**: For each high-level/complex C++ FCPP algorithm example, create a Python
`fcpp_bridge` equivalent that demonstrates the same algorithm using the Python DSL.
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

| Python file | C++ source | Key primitives | Status |
|---|---|---|---|
| `spreading_collection.py` | `fcpp-sample-project/lib/spreading_collection.hpp` | `rectangle_walk`, `abf_distance`, `mp_collection`, `broadcast` | ✅ Done |
| `channel_broadcast.py` | `fcpp-sample-project/lib/channel_broadcast.hpp` | `rectangle_walk`, `bis_distance`, `broadcast` | ✅ Done |
| `collection_compare.py` | `fcpp-sample-project/lib/collection_compare.hpp` | `rectangle_walk`, `abf_distance`/`bis_distance`/`flex_distance`, `sp_collection`, `mp_collection`, `wmp_collection` | ✅ Done |
| `message_dispatch.py` | `fcpp-sample-project/lib/message_dispatch.hpp` | `rectangle_walk`, `bis_distance`, `sp_collection`, `spawn`, `old` | ✅ Done |
| `chain_decaying.py` | `fcpp-sample-project/run/chain_decaying.hpp` + `fcpp-exercises/run/chain_decaying.hpp` | `nbr`, `min_hood` | ✅ Done |

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

---

## Resume instructions

If interrupted, check the **Status** table above. Find the first ⬜ Pending row and
continue from there. After each file is written, run:

```bash
PYTHONPATH=src python -c "import fcpp_bridge.examples.spreading_collection"
```

(or the relevant module) to verify the import does not crash.
