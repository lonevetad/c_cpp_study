# fcpp_bridge — Deployment & Development History

This document is the single consolidated record of all development phases for
`fcpp_bridge`. It covers every major topic in chronological order: primitive
coverage, visualization, test-suite restructuring, C++ algorithm examples,
networking, and physical device deployment.

**Run tests:**

```bash
PYTHONPATH=src src/expr_eval_py/expr_eval_py_env/bin/pytest src/fcpp_bridge/tests/ -v
```

---

## Test Count Progression

| Milestone                            | Tests   | Delta                              |
| ------------------------------------ | ------- | ---------------------------------- |
| Baseline (before Phase A)            | 217     | —                                  |
| After Phase A (15 target primitives) | 268     | +51                                |
| After Phase B (all 64 primitives)    | 379     | +111                               |
| After Phases 1-7 (full bridge)       | 482     | +103                               |
| After v1.0 (listener pipeline)       | 520     | +38                                |
| After v1.1 (compiler + tutorials)    | 523     | +3                                 |
| After v1.2 (physical deployment)     | 555     | +32 PhysicalNode, +8 DeviceManager |
| After v1.3 (pluggable liveness)      | **578** | +23                                |

---

## Phases A & B — Primitive Coverage Audit (2026-05-23)

### Goal

Ensure every FCPP aggregate primitive from the C++ coordination library has a
corresponding Python DSL class, transpiler mapping, and grammar rule.

### C++ Source Inventory

| Header           | Primitives                                                                                                                                                                                                                                                                          |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `basics.hpp`     | `nbr`, `old`, `nbr_uid`, `oldnbr`, `align`, `align_inplace`, `mod_other`, `split`, `fold_hood`, `count_hood`, `spawn`                                                                                                                                                               |
| `utils.hpp`      | `min_hood`, `max_hood`, `sum_hood`, `mean_hood`, `all_hood`, `any_hood`, `list_hood`                                                                                                                                                                                                |
| `spreading.hpp`  | `abf_distance`, `abf_hops`, `bis_distance`, `flex_distance`, `broadcast`, `bis_ksource_broadcast`                                                                                                                                                                                   |
| `collection.hpp` | `gossip`, `gossip_min/max/mean`, `sp_collection`, `mp_collection`, `wmp_collection`, `list_idem_collection`, `list_arith_collection`                                                                                                                                                |
| `geometry.hpp`   | `follow_target`, `follow_path`, `follow_track`, `rectangle_walk`, `random_rectangle_target`, `neighbour_elastic_force`, `neighbour_gravitational_force`, `neighbour_charged_force`, `line_elastic_force`, `plane_elastic_force`, `point_elastic_force`, `point_gravitational_force` |
| `election.hpp`   | `diameter_election`, `diameter_election_distance`, `color_election`, `color_election_distance`, `wave_election`, `wave_election_distance`                                                                                                                                           |
| `time.hpp`       | `constant`, `constant_after`, `counter`, `delay`, `round_since`, `time_since`, `timed_decay`, `exponential_filter`, `shared_clock`, `shared_decay`, `shared_filter`, `toggle`, `toggle_filter`                                                                                      |

**Excluded (3):** `spawn_deprecated` (deprecated), `color_election_internal` /
`wave_election_internal` (internal implementation details).

**Total covered: 64 primitives.**

### Phase A — 15 Target Primitives

**Gap analysis:**

- Python DSL: 8 classes missing (`Gossip`, `SpCollection`, `MpCollection`, `WmpCollection`, `BisDistance`, `AbfDistance`, `RectangleWalk`, `FollowTarget`)
- Transpiler: no FCPP primitive was recognized — all passed through without the mandatory `CALL` first argument
- Grammar: only 6 primitives tokenized; only 5 in the parse rule; `primitiveCall` had hardcoded arities

**Changes:**

| Layer            | File                          | What changed                                                                                                           |
| ---------------- | ----------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Python DSL       | `python_dsl/primitives.py`    | 8 new primitive classes                                                                                                |
| Python DSL       | `python_dsl/decorators.py`    | Mixin stubs replaced with real `return SpCollection(...)` etc.                                                         |
| Transpiler       | `transpiler/__init__.py`      | `_FCPP_PRIMITIVES` dict; `visit_Call` injects `CALL` as first arg for all 16 primitives; per-primitive header tracking |
| Grammar (Python) | `grammar/__init__.py`         | PRIMITIVE regex + `_parse_call_expr` for all 16 primitives; variable-arg parsing                                       |
| Grammar (ANTLR)  | `grammar/AggregateProgram.g4` | 10 new lexer tokens; `primitiveCall` rule uses `argList?`; `primitive` rule lists all 16                               |

### Phase B — All 64 Primitives

Added the remaining 48 classes (basics*6, utils*5, spreading*3, collection*5,
geometry*10, election*6, time\*13). Extended `_FCPP_PRIMITIVES`, `_ALL_PRIMITIVES`
frozenset, and ANTLR grammar to cover all 64. Added `mixin_election` (6 methods)
and `mixin_time` (13 methods).

### Primitive → Bridge Layer Mapping

| Primitive                       | Python class                  | C++ header       |
| ------------------------------- | ----------------------------- | ---------------- |
| `nbr`                           | `Neighborhood`                | `basics.hpp`     |
| `old`                           | `OldValue`                    | `basics.hpp`     |
| `nbr_uid`                       | `NbrUid`                      | `basics.hpp`     |
| `oldnbr`                        | `OldNbr`                      | `basics.hpp`     |
| `align`                         | `Align`                       | `basics.hpp`     |
| `align_inplace`                 | `AlignInplace`                | `basics.hpp`     |
| `mod_other`                     | `ModOther`                    | `basics.hpp`     |
| `split`                         | `Split`                       | `basics.hpp`     |
| `fold_hood`                     | `FoldHood`                    | `basics.hpp`     |
| `count_hood`                    | `CountHood`                   | `basics.hpp`     |
| `spawn`                         | `Spawn`                       | `basics.hpp`     |
| `min_hood`                      | `MinHood`                     | `utils.hpp`      |
| `max_hood`                      | `MaxHood`                     | `utils.hpp`      |
| `sum_hood`                      | `SumHood`                     | `utils.hpp`      |
| `mean_hood`                     | `MeanHood`                    | `utils.hpp`      |
| `all_hood`                      | `AllHood`                     | `utils.hpp`      |
| `any_hood`                      | `AnyHood`                     | `utils.hpp`      |
| `list_hood`                     | `ListHood`                    | `utils.hpp`      |
| `abf_distance`                  | `AbfDistance`                 | `spreading.hpp`  |
| `abf_hops`                      | `AbfHops`                     | `spreading.hpp`  |
| `bis_distance`                  | `BisDistance`                 | `spreading.hpp`  |
| `flex_distance`                 | `FlexDistance`                | `spreading.hpp`  |
| `broadcast`                     | `Broadcast`                   | `spreading.hpp`  |
| `bis_ksource_broadcast`         | `BisKsourceBroadcast`         | `spreading.hpp`  |
| `gossip`                        | `Gossip`                      | `collection.hpp` |
| `gossip_min`                    | `GossipMin`                   | `collection.hpp` |
| `gossip_max`                    | `GossipMax`                   | `collection.hpp` |
| `gossip_mean`                   | `GossipMean`                  | `collection.hpp` |
| `sp_collection`                 | `SpCollection`                | `collection.hpp` |
| `mp_collection`                 | `MpCollection`                | `collection.hpp` |
| `wmp_collection`                | `WmpCollection`               | `collection.hpp` |
| `list_idem_collection`          | `ListIdemCollection`          | `collection.hpp` |
| `list_arith_collection`         | `ListArithCollection`         | `collection.hpp` |
| `follow_target`                 | `FollowTarget`                | `geometry.hpp`   |
| `follow_path`                   | `FollowPath`                  | `geometry.hpp`   |
| `follow_track`                  | `FollowTrack`                 | `geometry.hpp`   |
| `rectangle_walk`                | `RectangleWalk`               | `geometry.hpp`   |
| `random_rectangle_target`       | `RandomRectangleTarget`       | `geometry.hpp`   |
| `neighbour_elastic_force`       | `NeighbourElasticForce`       | `geometry.hpp`   |
| `neighbour_gravitational_force` | `NeighbourGravitationalForce` | `geometry.hpp`   |
| `neighbour_charged_force`       | `NeighbourChargedForce`       | `geometry.hpp`   |
| `line_elastic_force`            | `LineElasticForce`            | `geometry.hpp`   |
| `plane_elastic_force`           | `PlaneElasticForce`           | `geometry.hpp`   |
| `point_elastic_force`           | `PointElasticForce`           | `geometry.hpp`   |
| `point_gravitational_force`     | `PointGravitationalForce`     | `geometry.hpp`   |
| `diameter_election`             | `DiameterElection`            | `election.hpp`   |
| `diameter_election_distance`    | `DiameterElectionDistance`    | `election.hpp`   |
| `color_election`                | `ColorElection`               | `election.hpp`   |
| `color_election_distance`       | `ColorElectionDistance`       | `election.hpp`   |
| `wave_election`                 | `WaveElection`                | `election.hpp`   |
| `wave_election_distance`        | `WaveElectionDistance`        | `election.hpp`   |
| `constant`                      | `Constant`                    | `time.hpp`       |
| `constant_after`                | `ConstantAfter`               | `time.hpp`       |
| `counter`                       | `Counter`                     | `time.hpp`       |
| `delay`                         | `Delay`                       | `time.hpp`       |
| `round_since`                   | `RoundSince`                  | `time.hpp`       |
| `time_since`                    | `TimeSince`                   | `time.hpp`       |
| `timed_decay`                   | `TimedDecay`                  | `time.hpp`       |
| `exponential_filter`            | `ExponentialFilter`           | `time.hpp`       |
| `shared_clock`                  | `SharedClock`                 | `time.hpp`       |
| `shared_decay`                  | `SharedDecay`                 | `time.hpp`       |
| `shared_filter`                 | `SharedFilter`                | `time.hpp`       |
| `toggle`                        | `Toggle`                      | `time.hpp`       |
| `toggle_filter`                 | `ToggleFilter`                | `time.hpp`       |

---

## Phase 7 — Visualization & ANTLR Generation

### Part 1 — ANTLR Code Generation

`grammar/AggregateProgram.g4` describes the full FCPP aggregate DSL grammar.
`AntlrParser` uses dual-path dispatch: if the generated stubs and the
`antlr4-python3-runtime` are both present it uses the full ANTLR4 parser (with
`line:col` error recovery); otherwise it falls back to the hand-written
`AggregateLanguageParser`.

**Generating the stubs (first time only):**

```bash
cd src/fcpp_bridge/grammar
python3 generate_antlr.py --download
../../expr_eval_py/expr_eval_py_env/bin/pip install -r requirements_antlr.txt
```

Generated in `grammar/__antlr_gen/` (git-ignored): `AggregateProgramLexer.py`,
`AggregateProgramParser.py`, `AggregateProgramListener.py`,
`AggregateProgramVisitor.py`. Re-run after any grammar change.

**New files:** `grammar/generate_antlr.py`, `grammar/requirements_antlr.txt`.

### Part 2 — Visualization Plugin

Data flow:

```
SwarmSnapshot (via IPC)
  → MetricsCollector.record(snapshot)
    → on_update callback
      → Visualizer.update(snapshot)
        → SwarmVisualizer (live matplotlib)  /  TextDashboard (terminal)
```

The visualization plugin is a passive consumer — attaching it adds a lightweight
callback and does not affect the IPC pipeline.

| Class                  | Description                                                                                               |
| ---------------------- | --------------------------------------------------------------------------------------------------------- |
| `VisualizerBase` (ABC) | `update`, `start`, `stop`, `attach(collector)`, `detach`, `replay_from_history`                           |
| `TextDashboard`        | Terminal output, no external dependencies                                                                 |
| `SwarmVisualizer`      | Live matplotlib: node-count subplot + mean/min/max shaded-band subplot; `get_data()` for headless testing |
| `create_visualizer`    | Factory — tries `SwarmVisualizer`, falls back to `TextDashboard` if matplotlib absent                     |

**New files:** `visualization/__init__.py`, `tests/test_visualization.py` (16 tests).

---

## Test Suite Refactoring (2026-05-24)

**Goal:** Mirror the one-file-per-class source layout in the test suite. Each
monolithic `test_<phase>.py` becomes a sub-package with one file per component.

**Baseline at refactor time:** 482 tests.

### Final layout

```
tests/
├── conftest.py              (unchanged)
├── __init__.py              (unchanged)
├── test_logging.py          (kept flat — 166 lines, single cohesive component)
├── visualization/           (4 files, was test_visualization.py 256 lines)
├── compiler/                (3 files, was test_compiler.py 266 lines)
├── metrics/                 (6 files, was test_metrics.py 397 lines)
├── ipc/                     (7 files total after v1.2-v1.3, was test_ipc.py 545 lines)
├── grammar/                 (5 files, was test_parser.py 677 lines)
├── transpiler/              (3 files, was test_transpiler.py 1107 lines)
└── dsl/                     (6 files, was test_dsl.py 1578 lines)
```

### Rules applied

- Old monolithic file deleted after its sub-package verified passing.
- Sub-packages have `__init__.py` (pytest requires it when parent has one).
- No new `conftest.py` in sub-packages — pytest inherits `tests/conftest.py`.
- Mid-file inline imports become top-of-file imports in the split file.

### IPC sub-package (extended through v1.3)

| File                        | Coverage                                                 |
| --------------------------- | -------------------------------------------------------- |
| `test_data_types.py`        | `NodeState`, `SwarmSnapshot` (8 tests)                   |
| `test_backends.py`          | `UnixSocketBackend`, `HttpBackend` init/parse (15 tests) |
| `test_swarm_process.py`     | `SwarmProcess` lifecycle (17 tests)                      |
| `test_device_manager.py`    | `DeviceManager` (14 original + 8 new v1.2 tests)         |
| `test_network_listener.py`  | Listener pipeline, heartbeat (38 tests added v1.0)       |
| `test_physical_node.py`     | `PhysicalNode` (32 tests added v1.2)                     |
| `test_liveness_strategy.py` | All 3 strategies + integration (23 tests added v1.3)     |

---

## C++ Algorithm Examples (2026-05-24)

Five Python ports of real FCPP C++ algorithms in `examples/`. Each file contains
an `@aggregate_function` class (transpilable) plus a `_demo_simulate()` function
(pure Python, no compiler needed). Per-node log files written to `examples/logs/`.

```bash
PYTHONPATH=src python src/fcpp_bridge/examples/<name>.py
```

| File                      | C++ source                     | Key primitives                                                     |
| ------------------------- | ------------------------------ | ------------------------------------------------------------------ |
| `spreading_collection.py` | `lib/spreading_collection.hpp` | `abf_distance`, `mp_collection`, `broadcast`                       |
| `channel_broadcast.py`    | `lib/channel_broadcast.hpp`    | `bis_distance`, `broadcast`                                        |
| `collection_compare.py`   | `lib/collection_compare.hpp`   | `sp_collection`, `mp_collection`, `wmp_collection`                 |
| `message_dispatch.py`     | `lib/message_dispatch.hpp`     | `bis_distance`, `sp_collection`, `spawn`, `old`, `nbr`, `min_hood` |
| `chain_decaying.py`       | `run/chain_decaying.hpp`       | `nbr`, `min_hood`                                                  |

**Algorithm notes:**

- `spreading_collection`: Python port uses a static `is_source` flag; C++ rotates source every 50 simulated seconds via `node.current_time()`.
- `channel_broadcast`: channel condition `ds + dd < broadcast(ds, dd) + width` — broadcast of ds gives the source-to-destination straight-line distance.
- `collection_compare`: C++ selects distance algorithm via storage tag; Python port always uses `abf_distance` (algorithm 0).
- `message_dispatch`: `spawn` creates per-message aggregate processes routing across the spanning tree.
- `chain_decaying`: TTL-based chain — `nbr` lambda returns updated 4-tuple `(should_hold, hops, ttl, next_uid)`. Source condition: `node_uid % 17 == 0`.

**Excluded** (learning exercises with partial solutions, simulation-runner variants, and files using navigator components outside aggregate primitives).

---

## v1.0 — Network Listener Pipeline (2026-05-24)

### Goal

Replace `SwarmProcess.add_nodes(count)` (the only node-addition method) with
three strategies, add `remove_node`, add a passive heartbeat/liveness monitor,
and replace the single push-callback slot with a multi-listener proxy system.

### New files

| File                      | Purpose                                                                      |
| ------------------------- | ---------------------------------------------------------------------------- |
| `ipc/updates_listener.py` | `UpdatesListener = Callable[[SwarmSnapshot], None]`                          |
| `ipc/listener_proxy.py`   | `ListenerProxy(mode="sequential"\|"parallel")` — multi-listener, integer IDs |

### `SwarmProcess` new API

```python
# Node addition
add_nodes_random(count, *, area, comm_range, max_speed, propulsion) → List[int]
add_node_explicit(node_id, position, **kw)
add_nodes_sequential(count, start_positions=None) → List[int]
add_nodes(count)            # backward-compat alias → add_nodes_sequential

# Node removal
remove_node(node_id)

# Liveness (passive — based on last received snapshot timestamp)
check_liveness(timeout=30.0)  → Dict[int, bool]
start_heartbeat_monitor(interval=5.0, timeout=30.0, on_dead=None)
stop_heartbeat_monitor()

# Listener management (global)
add_listener(fn)    → listener_id: int
remove_listener(id)

# Listener management (per-node override)
add_node_listener(node_id, fn) → listener_id: int
remove_node_listener(node_id, listener_id)
```

**Dispatch logic:** `_dispatch_update(snapshot)` routes each node update to its
per-node listener if one is registered, otherwise to the global listener. Also
updates heartbeat timestamps. `get_state()` (pull path) also updates timestamps
so passive liveness works without a live push subscription.

**Design decisions:**

- `ListenerProxy` always used internally — `add_listener` always returns an integer ID for later removal.
- Passive heartbeat: tracks `last_seen` timestamp per node. Active ping/pong would require C++ side support — left for v1.3.
- `_known_node_ids` initialized from `range(num_nodes)` at `start()` time.

**New tests:** `tests/ipc/test_network_listener.py` (38 tests). Total: 520.

---

## v1.1 — Compiler Customization & Tutorials (2026-05-24)

**`Compiler.__init__`** now accepts `std: str = "c++26"`, `opt_level: str = "2"`,
`extra_includes: Optional[List[str]] = None`. The `compile()` method also accepts
`extra_flags` for per-call overrides (appended last).

**New docs:** `TUTORIAL_simple.md` (beginner: 20-node hop-channel using BIS
distance, `nbr`/`min_hood` hops, `broadcast`), `TUTORIAL_in_depth.md` (production:
`HopChannelSimulation` class with full lifecycle, `ListenerProxy`, per-node listeners,
compiler customization, node addition strategies, liveness monitoring).

**New tests:** 3 in `tests/compiler/test_compiler_core.py`. Total: 523.

---

## v1.2 — Physical Device Deployment (2026-05-25)

### Background

FCPP's intended deployment lifecycle:

1. Write the aggregate program once.
2. Compile to a binary.
3. Deploy the binary to every physical device (robots, drones, phones, sensors, …).
4. Each device runs its own round loop — Python is not in the critical path.
5. Devices join and leave unpredictably via radio range.
6. Python optionally observes the fleet.

**Problem:** `SwarmProcess` was simulation-only (always spawned a subprocess, always
drove rounds with `step()`). `DeviceManager` could only hold `SwarmProcess` instances.
The IPC backend interface was already generic; the gap was in the layer above it.

### What was missing

1. A class that connects TO a physical device without spawning a subprocess.
2. Auto-reconnect for transient network drops.
3. FCPP-level neighbor join/leave notifications (distinct from Python connection events).
4. A `DeviceManager` that holds both simulation and physical entries.
5. `step_all()` must not drive physical devices.
6. A shared base class to avoid duplicating heartbeat + listener code.

### Architecture

```
_IpcNodeBase
├── get_state()
├── check_liveness(), start/stop_heartbeat_monitor()
├── add/remove_listener(), add/remove_node_listener(), _dispatch_update()
└── close()                ← stops heartbeat, closes backend

SwarmProcess(_IpcNodeBase)
├── start()                ← spawns subprocess
├── close()                ← super().close() + terminates process
├── step()
└── add_nodes_*, remove_node, _create_backend

PhysicalNode(_IpcNodeBase)
├── connect()              ← creates HttpBackend / GrpcBackend (no subprocess)
├── close()                ← stops reconnect, super().close(); device keeps running
├── start/stop_auto_reconnect()
├── on_neighbor_joined(cb) ← fires when new node_id appears in snapshot
├── on_neighbor_left(cb)   ← fires via heartbeat when node goes silent
└── _dispatch_update, start_heartbeat_monitor overrides
```

### `DeviceManager` heterogeneous fleet

```python
mgr = DeviceManager()
mgr.add_simulation("lab", binary_path, num_nodes=100)      # SwarmProcess
mgr.add("lab2", binary_path)                               # backward-compat alias
mgr.add_physical("robot-1", "192.168.1.10", 8080)          # PhysicalNode (HTTP)
mgr.add_physical("drone-1", "192.168.1.20", 50051, backend_type="grpc")

mgr.start_all()        # starts SwarmProcess instances only
mgr.connect_all()      # connects PhysicalNode instances only
mgr.step_all()         # steps SwarmProcess only (physical devices drive themselves)
mgr.get_all_states()   # works for both types
mgr.close_all()
```

### Design decisions

**`PhysicalNode` as a separate class (not a mode flag on `SwarmProcess`):**
A `mode="simulation"|"physical"` parameter would have turned `SwarmProcess` into a
branching monolith. The two modes have fundamentally different contracts (`connect` vs
`start`, no `step`, no `add_nodes`).

**`_IpcNodeBase` (private base class):**
Both subclasses share the listener pipeline and heartbeat. Duplicating the code
would guarantee divergence. The underscore prefix signals it is an implementation
detail, not part of the public API.

**Autonomous join/leave at the FCPP level:**
`on_neighbor_joined` fires on the first appearance of a `node_id` in any `SwarmSnapshot`
— no C++ runtime changes required. `on_neighbor_left` reuses the passive heartbeat
timeout, composed with `_seen_node_ids.discard()` in the overridden `start_heartbeat_monitor`.

**Auto-reconnect (best-effort):**
A daemon thread checks `is_connected` every `reconnect_interval` seconds. `is_connected`
is not automatically set to `False` on backend exception — the caller calls `node.close()`
to trigger a reconnect cycle. Mixing exception propagation with the reconnect state
machine was deemed overly complex.

**`step_all()` skips `PhysicalNode` via `isinstance`:**
A no-op `step()` on `_IpcNodeBase` was rejected — calling `step()` on a physical
node is a programming error that should surface as `AttributeError`, not be silently swallowed.

**`DeviceManager.total_nodes()`:**
Uses `node_count` property: `SwarmProcess.node_count → num_nodes`;
`PhysicalNode.node_count → len(_seen_node_ids) or 1`.

### Files changed

| File                               | Change                                                                                                  |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `ipc/_ipc_node_base.py`            | New — shared base class                                                                                 |
| `ipc/physical_node.py`             | New — `PhysicalNode`                                                                                    |
| `ipc/swarm_process.py`             | Inherits from `_IpcNodeBase`; ~80 lines removed                                                         |
| `ipc/device_manager.py`            | `_devices: Dict[str, _IpcNodeBase]`; `add_simulation`, `add_physical`, `connect_all`, split `start_all` |
| `ipc/__init__.py`                  | Exports `_IpcNodeBase`, `PhysicalNode`                                                                  |
| `tests/ipc/test_physical_node.py`  | New — 32 tests                                                                                          |
| `tests/ipc/test_device_manager.py` | +8 tests                                                                                                |

**Total: 555 tests (+40).**

---

## v1.3 — Pluggable Liveness Strategies (2026-05-25)

### Goal

The passive heartbeat was hardwired into `_IpcNodeBase`. Liveness checking is now
decoupled via the **Strategy pattern** — configurable at construction time and
replaceable at runtime.

### `LivenessStrategy` ABC

```
on_snapshot(snapshot)          # called on every received snapshot
check(**kwargs) → {id: bool}   # query liveness; unknown kwargs silently ignored
discard(node_id)               # remove a node from tracking (no-op default)
close()                        # release resources (no-op default)
```

### Built-in implementations

| Strategy                                               | How it works                                                                                                  | C++ requirement            |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- | -------------------------- |
| `PassiveHeartbeatStrategy(timeout=30.0)`               | Alive if last snapshot ≤ timeout s ago; `_timestamps` dict                                                    | None                       |
| `ActivePingStrategy(backend_getter, ping_timeout=2.0)` | Sends `{"cmd":"ping","node_id":n}`, expects `{"status":"pong"}`; returns False on any exception or no backend | Ping handler in C++ binary |
| `AlwaysAliveStrategy()`                                | Always returns True                                                                                           | None                       |

### `_IpcNodeBase` changes

| Addition                                 | Description                                                                                                                          |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `__init__(liveness_strategy=None)`       | Defaults to `PassiveHeartbeatStrategy()`                                                                                             |
| `set_liveness_strategy(strat)`           | Closes old strategy, installs new one                                                                                                |
| `_heartbeat_timestamps` (property)       | Returns `strat._timestamps` live reference for `PassiveHeartbeatStrategy`; empty dict otherwise — backward compat for existing tests |
| `check_liveness(timeout=30.0, **kwargs)` | Delegates to `strategy.check(timeout=timeout, **kwargs)`                                                                             |
| `_discard_node_from_liveness(node_id)`   | Delegates to `strategy.discard(node_id)`                                                                                             |
| `close()`                                | Calls `strategy.close()` before closing backend                                                                                      |

`SwarmProcess.remove_node` changed from direct `_heartbeat_timestamps.pop()` to
`_discard_node_from_liveness()`.

Constructor propagation: `SwarmProcess`, `PhysicalNode`, `DeviceManager.add_simulation`,
and `DeviceManager.add_physical` all accept `liveness_strategy=`.

### Design rationale

**Strategy pattern over `mode="passive"|"active"` enum:**

- New strategies can be added without touching `_IpcNodeBase` (Open/Closed Principle).
- `ActivePingStrategy`'s `backend_getter` lambda means reconnects are transparent — the strategy always uses the latest backend without re-registration.
- `AlwaysAliveStrategy` lets tests and fixed-topology deployments opt out of liveness entirely, without special-casing in the monitor loop.
- Strategies are first-class objects — shareable, composable, mockable.

**Backward compat for `_heartbeat_timestamps`:**
Seven existing tests directly access `_heartbeat_timestamps` as a mutable dict. The
property returns a live reference to `PassiveHeartbeatStrategy._timestamps`, so
reads and writes on the returned dict modify the strategy's internal state directly.
Tests are unchanged.

### Files changed

| File                                  | Change                                                                                              |
| ------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `ipc/liveness_strategy.py`            | New — `LivenessStrategy` ABC + 3 implementations                                                    |
| `ipc/_ipc_node_base.py`               | Delegation to strategy; `_heartbeat_timestamps` property                                            |
| `ipc/swarm_process.py`                | `remove_node` uses `_discard_node_from_liveness`; `liveness_strategy` kwarg                         |
| `ipc/physical_node.py`                | `liveness_strategy` kwarg                                                                           |
| `ipc/device_manager.py`               | `liveness_strategy` kwarg propagated through `add_*`                                                |
| `ipc/__init__.py`                     | Exports `LivenessStrategy`, `PassiveHeartbeatStrategy`, `ActivePingStrategy`, `AlwaysAliveStrategy` |
| `tests/ipc/test_liveness_strategy.py` | New — 23 tests                                                                                      |

**Total: 578 tests (+23). 0 regressions.**

---

## Known Gaps & Future Work

| Gap                                                  | Notes                                                                                                   |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `ActivePingStrategy` C++ side                        | The C++ binary needs a `{"cmd":"ping"}` → `{"status":"pong"}` handler; not yet in the runtime templates |
| Auto-set `is_connected = False` on backend exception | Currently user must call `node.close()` to trigger reconnect; complex contract                          |
| `DeviceManager.accept_registrations(port)`           | Server-side listener for self-registering devices                                                       |
| Multi-swarm coordination UI                          | `DeviceManager` backend done; frontend TBD                                                              |
| Activate ANTLR4 parser                               | Run `grammar/generate_antlr.py --download` (requires Java 11+)                                          |
