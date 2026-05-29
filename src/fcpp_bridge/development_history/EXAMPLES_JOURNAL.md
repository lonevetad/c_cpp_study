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
| `communication_roles_assignment.py` | **original** — v1.9 DSL showcase | `bis_distance` ×2, `nbr`, `min_hood`, `old` ×2, `broadcast`, `self_uid()` + `match/case` + `CommunicationRole` + setup: isolation migration + point placement | ✅ Done |

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
- **Role assignment** (v1.8.1): `ROLE_CYCLE[nid % len(ROLE_CYCLE)]` — 13-slot cycle
  with 5 extra `WorkerRole.REPEATER` slots; `DEVICES = 26` (2 full cycles).
  Totals: REPEATER-type=14, ENDPOINT-type=10, RECEIVER-type=2.
  Endpoint roles: LIDAR, INFRARED_SENSOR, TORCHLIGHT_MICROPHONE, RUBBLES_REMOVER,
  FLYING_OVERSEER.  Receiver role: RECEIVER.  Repeater roles: UNASSIGNED (passive),
  REPEATER (active relay).
- **ROLE_COMM_TYPE bug fix** (v1.8.1): `{**frozenset}` in dict literal raises
  `TypeError`; fixed to `{**{r: ... for r in frozenset}}` comprehension form.
- **RoleCommunicationType** (v1.7): new enum (ENDPOINT=0, RECEIVER=1, REPEATER=2)
  associated with each WorkerRole via `ROLE_COMM_TYPE` dict.  Endpoint nodes gather
  sensor data and inject readings; repeater nodes relay data without originating it.
- **CALL-counter constraint**: all 7 CALL-based primitives (`bis_distance`, `nbr`,
  `min_hood`, `count_hood`, `sp_collection`, `spawn`, `old`) are called before the
  `match/case` block.  Placing primitives inside switch branches would desynchronise the
  FCPP `CALL` counter across nodes and produce incorrect C++ behavior.
- **Enum-value case labels** (v1.8.2): `case WorkerRole.X.value:` dotted-name value
  patterns (Python 3.10+ `a.b.c` chains are always value patterns, never capture
  patterns).  Replaces integer literals `case 0:`, `case 1:`, … — no magic numbers.
- **Enum-value comparisons** (v1.8.2): `role == WorkerRole.X.value` replaces `role == N`
  throughout `compute()`.  `ROLE_CYCLE` uses `WorkerRole.X` members directly.
  `WorkerRole(x).name` calls replaced by `x.name` since `roles[nid]` is now a
  `WorkerRole` member.  `int(r)` / `int(ct)` in `main()` replaced by `r.value` /
  `ct.value`.
- **Named swarm-size constants** (v1.8.3): `ADDITIONAL_REPEATERS_EACH_CYCLE = 5`
  (extra REPEATER slots per cycle; keep `> 3` for REPEATER-type > ENDPOINT-type) and
  `FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS = 2` (number of full ROLE_CYCLE repetitions);
  `DEVICES = len(ROLE_CYCLE) * FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS` (derived).
  `ROLE_CYCLE` uses `*([WorkerRole.REPEATER] * ADDITIONAL_REPEATERS_EACH_CYCLE)`
  instead of 5 explicit entries.
- **Transpiler enum constant-folding** (v1.8.4): `PythonAstVisitor` now accepts a
  `constants` dict (populated from `compute.__globals__`).  Dotted chains like
  `WorkerRole.RECEIVER.value` are resolved to integer literals, making `case`
  labels and comparisons emit valid C++.  5 new tests added.
- **self_uid()** (v1.6): `self_uid()` → `node.uid` in generated C++ (no CALL counter);
  used in step 2 (tie-breaking), step 4 (sp_collection local value), step 5 (spawn key
  sender half).  Receiver UID in spawn key is still `0` (placeholder — v1.9 fix planned).
- **Step 7 role tasks**: each `match/case` branch contains a role-specific task
  description and a local placeholder variable; tasks without a real-world implementation
  are marked with `# [Placeholder]` comments.
- **routing_set_size repurposing**: LIDAR and REPEATER store `count_hood()`
  (coverage metric); UNASSIGNED stores `0` (passive); all other roles store
  `len(sp_collection set)`.
- **v1.8**: `main()` uses shared `report_validation`/`report_transpilation` helpers from
  `examples/_example_utils.py`; no algorithm changes.
- **v1.8.5**: Import path fixed across all 6 example files: `from examples._example_utils import` →
  `from fcpp_bridge.examples._example_utils import`.  The bare `examples` package name was not
  resolvable under either `PYTHONPATH=src` (from repo root) or `PYTHONPATH=..` (from
  `src/fcpp_bridge/`) because neither puts `src/fcpp_bridge/` on `sys.path`.
- **Full design notes**: `development_history/WORKER_ROLE_ASSIGNMENT.md` — scenario,
  algorithm table, DSL feature rationale, limitations, 7 evolution paths.
- **Pre-v1.9 refactoring**: `development_history/PRE_V19_REFACTORING.md` — v1.8.1
  ROLE_CYCLE + bug fix; v1.8.2 enum-value magic-number elimination.
- **v1.9 plan**: `development_history/V1_9_PLAN.md` — receiver UID fix via `broadcast`,
  `frozenset` → `set_t` transpilation, `min_hood` tuple → `std::make_tuple`, and more.

### communication_roles_assignment.py
- **Origin**: original DSL-showcase example (not ported from C++); designed to exercise
  `bis_distance` ×2, `nbr + min_hood` election, `old` ×2, `broadcast`, and `match/case`
  with a simulated communication scenario.
- **CommunicationRole enum**: `UNASSIGNED(0)`, `SENDER(1)`, `REPEATER(2)`, `RECEIVER(3)`.
  Relationship to `worker_role_assignment.py`: `RoleCommunicationType.ENDPOINT → SENDER`,
  `RoleCommunicationType.RECEIVER → RECEIVER`, `RoleCommunicationType.REPEATER → REPEATER`;
  `UNASSIGNED` is new (pre-convergence default before roles are resolved).
- **Configuration** (defaults): `NODES=15`, `SINK_POINTS=2`, `SOURCE_POINTS=3`,
  `COMM=100.0`, `MSG_TICKS_INTERVAL=10`, `ISOLATION_THRESHOLD=0.20`,
  `MAX_MIGRATION_ITERS=50`, `MAX_POINT_PLACEMENT_ITERS=10`.
- **Consistency check**: `SINK_POINTS + SOURCE_POINTS <= NODES` enforced; raises
  `ValueError("Inconsistent configuration: ...")` if violated.
- **Isolation migration**: `_build_and_migrate_network()` — places nodes randomly,
  counts isolated nodes (no neighbors within COMM), migrates isolated ones by random
  relocation in a while loop (up to `MAX_MIGRATION_ITERS`); logs each pass.
- **Sink/source placement**: `_place_points()` — for each of the n points:
  chooses a random unlocked anchor node, samples a random position within COMM of
  that anchor, checks that the candidate does not fall within COMM of any
  already-locked node (conflict → retry up to `MAX_POINT_PLACEMENT_ITERS`);
  locks the anchor. A `locked` dict maps `nid → (point_pos, is_sink)`.
- **Role assignment**: `_assign_initial_roles()` — Receivers: one per sink point,
  closest node within COMM (tie → smallest ID); Senders: one per source point,
  closest non-Receiver within COMM (tie → smallest ID); others → Repeater.
- **Aggregate DSL steps** (all 7 run at EVERY node):
  1. `bis_distance(is_receiver)` — gradient toward Receivers
  2. `bis_distance(is_sender)` — gradient away from Senders
  3. `nbr(dist_to_nearest_source)` + `min_hood(...)` — Sender election
  4. `old(0, t+1)` — round counter
  5. `broadcast(dist_from_sender, payload)` — propagate Sender message outward
  6. `old({}, accumulate)` — received-message log at Receivers
  7. `match/case` — role-specific task + state assembly (no primitives inside)
- **Message payload**: `(sender_uid, round_tick, dist_to_nearest_source)` — dummy data
  for demonstration purposes; Sender creates a new payload every `MSG_TICKS_INTERVAL` rounds.
- **Shared helpers**: uses `neighbors_of` and `SPAWN_STATUS_*` from `_example_utils`;
  no local re-definitions.
- **`_example_utils` refactoring** (v1.9): added `neighbors_of`, `build_positions`,
  and `SPAWN_STATUS_BORDER/INTERNAL/TERMINATED` to `_example_utils.py`; all 6
  pre-existing main examples updated to use `neighbors_of` from shared module;
  `message_dispatch.py` and `worker_role_assignment.py` updated to use
  `SPAWN_STATUS_*` aliases.  Cohesiveness plan: `examples_cohesiveness.md`.
- **Future exercises**: see `FUTURE_EXERCISES.md` — FE-1 (spawn for multiple
  instances), FE-2 (dynamic points), FE-3 (mobile nodes), FE-4 (area partition),
  and more.

---

## v2.0 — AbstractExample refactor (2026-05-28)

All 7 example files refactored to replace `_demo_simulate()` with a proper
`AbstractExample` subclass (Template Method pattern).

### New base class: `examples/abstract_example.py`

`AbstractExample` provides:
- `run(num_rounds)` — simulation loop with log-file lifecycle management
- Abstract: `log_prefix`, `initial_positions()`, `initial_states()`, `round_step()`,
  `log_header()`, `log_line()`
- Optional hooks: `on_simulation_start()`, `on_simulation_end()`, `on_round_complete()`
- Log files opened on first appearance of a node; closed when node leaves `states` dict
- `log_dir` property defaults to `examples/logs/` (overridable per-subclass)

### Dynamic node dict

`positions: dict[int, tuple]` and `states: dict[int, state]` — node presence determined
by dict keys only.  Nodes join by inserting new keys into the returned dict; they leave
by omitting their key from the returned dict.  `AbstractExample.run()` opens/closes
per-node log files as keys appear/disappear.

### Per-example changes

| Example | Subclass name | Extra log(s) | Cross-round state |
|---|---|---|---|
| `spreading_collection.py` | `SpreadingCollectionExample` | — | — |
| `chain_decaying.py` | `ChainDecayingExample` | — | `_final_states` (double-sim bug fixed) |
| `channel_broadcast.py` | `ChannelBroadcastExample` | — | `_final_states` |
| `collection_compare.py` | `CollectionCompareExample` | — | `_final_states` |
| `message_dispatch.py` | `MessageDispatchExample` | — | `_in_flight`, `_total_received` |
| `worker_role_assignment.py` | `WorkerRoleExample` | `receiver_messages.log` | `_in_flight`, `_total_delivered`, `_recv_log` |
| `communication_roles_assignment.py` | `CommunicationRolesExample` | `comm_receiver_messages.log` | all per-round distance dicts; `_recv_log` |

`CommunicationRolesExample.__init__` calls `_setup_network()` to pre-compute positions
and roles.  `initial_positions()` / `initial_states()` return the pre-computed results.
Positions are static (no movement) — `round_step` returns the same positions dict.

### Bug fixed in chain_decaying.py

`main()` previously re-ran the entire simulation after `example.run()` to get final
states for summary printing (double execution).  Fixed: `on_round_complete` hook now
stores `self._final_states = states` each round; `main()` reads `example._final_states`.

### Tests

+8 new transpiler tests for match guard clause and OR patterns (see `match_guard_or_pattern.md`).
Total: 624 tests — 624 pass, 0 fail.

---

## v2.1 — AbstractExample toolchain bridge (2026-05-28, v1.9 Step E)

`AbstractExample.run()` now invokes the **full toolchain** instead of a pure-Python
simulation.  The `@aggregate_function` class is the actual running algorithm.

### Interface changes

**Removed abstract methods:**
- `round_step(round_num, positions, states)` — algorithm runs in C++ now
- `initial_states(positions)` — C++ binary owns initial state

**Added abstract property:**
- `aggregate_class` — the `@aggregate_function` class to validate, transpile, and run

**Added optional properties (with defaults):**
- `build_dir` — cache dir for compiled binaries (`examples/.fcpp_build/`)
- `cpp_dir` — dir for transpiled C++ source (`examples/.fcpp_cpp/`)

**Updated hook signature:**
- `on_round_complete(round_num, snapshot: Optional[SwarmSnapshot])` — receives a
  `SwarmSnapshot` from the C++ binary instead of Python-computed position/state dicts

**`log_header` / `log_line`:** same signatures; `state_data` is now `Any` from
`NodeState.state_data` (dict/JSON from the FCPP binary) instead of a Python dataclass.

### SwarmProcess.latest_snapshot()

New method added to `ipc/swarm_process.py`.  Returns the snapshot from the most
recent `_dispatch_update` call, or `None` before the first step.  Used by `run()`
to pass the current snapshot to `on_round_complete`.

### Tests

+10 new tests in `tests/examples/test_abstract_example.py` (mocked pipeline).
Total: **665 tests — 665 pass, 0 fail**.

### Step F dependency

Step F migrates the 7 concrete example subclasses to the new interface
(removing `round_step`, `initial_states`, pure-Python helpers; adding `aggregate_class`).

---

## v2.2 — Examples subclasses migration to toolchain path (2026-05-28, v1.9 Step F)

All 7 concrete `AbstractExample` subclasses migrated to the new toolchain interface
introduced in v2.1.

### Per-example changes

| Example | Removed | Added / Updated | compute() change |
|---|---|---|---|
| `spreading_collection.py` | `initial_states`, `round_step`; `math`, `neighbors_of` imports | `aggregate_class`; `state_data: Any` log methods; `on_round_complete(snap)` | step 2: `self_uid() == SOURCE_ID`; `float('inf')` in dataclass |
| `chain_decaying.py` | `_is_source_node`, `_chain_update`, `initial_states`, `round_step`; `math`, `neighbors_of` imports | `aggregate_class`; dict-access log methods; `on_round_complete(snap)` storing `_last_snapshot`; `on_simulation_end` uses snapshot | step 1: `self_uid() % 17 == 0` |
| `channel_broadcast.py` | `_bis_distance`, `initial_states`, `round_step`; `neighbors_of` import | `aggregate_class`; dict-access log methods | steps 2–3: `self_uid() == 0 / 1`; step 5: same |
| `collection_compare.py` | `initial_states`, `round_step`; `neighbors_of` import | `aggregate_class`; `old()` round counter; dict-access log methods | step 2: `old(0, t+1)` counter + source switch via `self_uid()` |
| `message_dispatch.py` | `_bis_distance_msg`, `initial_states`, `round_step`; `neighbors_of` import | `aggregate_class`; `old()` round counter; dict-access log methods | step 2: `self_uid() == 0`; step 5: `old()` counter + conditional `new_msg` injection |
| `worker_role_assignment.py` | `_bis_distance_worker`, `initial_states`, `round_step`; `neighbors_of` import | `aggregate_class`; dict-access log methods; `on_round_complete` writes receiver log from snapshot | — (compute unchanged) |
| `communication_roles_assignment.py` | `_bis_dist_comm`, `initial_states`, `round_step`; `_bis_dist_comm` import removed | `aggregate_class`; dict-access log methods; `on_round_complete` writes receiver log from snapshot | — (compute unchanged) |

### Receiver log format change

`worker_role_assignment.py` and `communication_roles_assignment.py` previously wrote
detailed per-message delivery entries inside `round_step()`.  In the toolchain path,
per-message data is not available from the C++ IPC snapshot.  The receiver log format
is simplified to a per-round summary:

- `receiver_messages.log`: `round,receiver_node,received_count`
- `comm_receiver_messages.log`: `round,receiver_nid,received_log_size`

### Role assignment in toolchain mode

`CommunicationRolesExample` and `WorkerRoleExample` previously called `_setup_network()`
and `initial_states()` to inject Python-computed roles into the C++ binary.  Since
`initial_states()` is removed from the interface, the C++ binary uses `initial_state()`
from the aggregate class (UNASSIGNED / default role 0) for all nodes.  Role-specific
behaviour will only execute correctly once role injection is added to the IPC protocol
(planned future work).

### `old()` counter additions

`collection_compare.py` and `message_dispatch.py` received `old(0, lambda t: t+1)` round
counters in `compute()` to replace Python-side round tracking:

- `collection_compare`: source switches from `self_uid()==0` to `self_uid()==1` when
  `round_tick >= SOURCE_SWITCH (250)`.
- `message_dispatch`: non-source nodes inject a new message every 10 rounds during
  `round_tick` in `[MSG_START=10, MSG_END=50]`.

### Smoke tests

`tests/examples/test_examples_smoke.py` — 7 new tests (one per aggregate class):
`validate` + `transpile` path, no C++ compiler required.

### Tests

+7 smoke tests in `tests/examples/test_examples_smoke.py`.
Total: **672 tests — 672 pass, 0 fail**.

---

## Resume instructions

If interrupted, check the **Status** table above. Find the first ⬜ Pending row and
continue from there. After each file is written, run:

```bash
PYTHONPATH=src python -c "import fcpp_bridge.examples.spreading_collection"
```

(or the relevant module) to verify the import does not crash.
