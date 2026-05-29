# fcpp_bridge v1.9 — Development Plan

**Created:** 2026-05-28  
**Revised:** 2026-05-28 (added Steps E + F; reordered for dependency optimality)

**Revision rationale:** The original plan addressed transpiler gaps, IPC robustness, and
output-channel design.  A subsequent session (2026-05-28g) added the `AbstractExample`
Template Method base class, but each subclass still re-implements the aggregate algorithm
in pure Python — which defeats the entire purpose of `fcpp_bridge` for developers using
the examples as a starting point.  Steps E and F replace the pure-Python simulation path
with a full toolchain invocation: validate → transpile → compile → run C++ binary →
consume state updates as per-node log files.  The `@aggregate_function` class becomes the
actual executable algorithm, not just a transpilation specimen.

---

## Table of Contents

1. [Step A — Transpiler completeness](#step-a--transpiler-completeness)
2. [Step B — Library foundations](#step-b--library-foundations)
3. [Step C — OutputChannel + DeviceManager integration](#step-c--outputchannel--devicemanager-integration)
4. [Step D — Runtime and physical-device support](#step-d--runtime-and-physical-device-support)
5. [Step E — AbstractExample toolchain bridge](#step-e--abstractexample-toolchain-bridge)
6. [Step F — Examples subclasses migration](#step-f--examples-subclasses-migration)
7. [Implementation Checklist](#implementation-checklist)
8. [Estimated test delta](#estimated-test-delta)

---

## Step A — Transpiler completeness

*Absorbs original Gaps #1, #2, #3, #4.*

Must be completed before Step E so that every `@aggregate_function` class in the examples
transpiles to correct C++ from day one.

---

### A.1 — Receiver UID placeholder (was Gap #1)

#### Problem

In `worker_role_assignment.py`, the spawn key is `(self_uid(), 0)`.  The `0` is a
placeholder for the receiver's UID.  All spawn keys therefore share the same destination
`0`, so the routing logic treats every message as going to node 0, not the actual nearest
RECEIVER.

#### Why `broadcast` fixes it

`broadcast(root_flag, value)` distributes a value from any root (where `root_flag=True`)
outward through a gradient; every non-root node receives the nearest root's value.
RECEIVER nodes are the roots; all other nodes receive the nearest RECEIVER's UID:

```python
# New step before the spawn block:
receiver_uid = broadcast(is_receiver, self_uid())   # noqa: F821
new_msg = (self_uid(), receiver_uid) if is_endpoint else None   # noqa: F821
```

Why not `channel_broadcast`? That primitive creates an *elliptical channel* between two
*known* endpoints.  Here the receiver UID is discovered dynamically — using
`channel_broadcast` would be circular.

#### Actions

1. Add `broadcast` as **step 5a** in `WorkerRoleAssignmentAggregate.compute()`.
2. Replace `(self_uid(), 0)` spawn key with `(self_uid(), receiver_uid)`.
3. Update algorithm-step comment count (becomes 8).
4. Update `WORKER_ROLE_ASSIGNMENT.md` — mark "receiver UID placeholder" ✅ resolved.
5. Update `node_uid__placeholder_flagging.md` §1 (affected call-sites table).

---

### A.2 — `frozenset` → `set_t{...}` transpilation (was Gap #2)

#### Problem

`frozenset({self_uid()})` currently transpiles verbatim because `frozenset` is not in
`_FCPP_PRIMITIVES`.  The correct C++ is `set_t{node.uid}`.

#### Fix

Add a handler in `PythonAstVisitor.visit_Call`:

```python
if func_name == "frozenset":
    if args:
        return f"set_t{{{', '.join(args)}}}"   # frozenset({x}) → set_t{x}
    return "set_t{}"                             # frozenset()   → set_t{}
```

#### Actions

1. Add the two-line `frozenset` handler in `visit_Call`.
2. Test: `frozenset({self_uid()})` → `set_t{node.uid}`.
3. Test: `frozenset()` → `set_t{}`.
4. Update `node_uid__placeholder_flagging.md` §3.3 (mark resolved).

---

### A.3 — `min_hood`/`max_hood` + tuple → `std::make_tuple` (was Gap #3)

#### Problem

```python
parent = min_hood((nbr_dists, self_uid()))
# currently transpiles to:
parent = min_hood(CALL, (nbr_dists, node.uid));
```

`(x, y)` in C++ is a *comma expression* — evaluates both operands and returns the last.
The correct C++ is `std::make_tuple(nbr_dists, node.uid)`.

#### Fix (heuristic, Option A)

Detect a Tuple literal as the sole argument to `min_hood` / `max_hood`:

```python
if func_name in ("min_hood", "max_hood") and len(node.args) == 1:
    arg = node.args[0]
    if isinstance(arg, ast.Tuple):
        elems = [self.visit(e) for e in arg.elts]
        return f"{func_name}(CALL, std::make_tuple({', '.join(elems)}))"
```

Note: extracting the UID component requires `std::get<1>(tup)` at the call site.  This
cannot be automated without type inference; document it as a manual post-step in callers.

#### Actions

1. Add the heuristic in `visit_Call` (before the general `_FCPP_PRIMITIVES` path).
2. Test: `min_hood((x, y))` → `min_hood(CALL, std::make_tuple(x, y))`.
3. Test: `max_hood((a, b, c))` → `max_hood(CALL, std::make_tuple(a, b, c))`.
4. Update `node_uid__placeholder_flagging.md` §3.5 (mark `make_tuple` side resolved;
   note `std::get<N>` extraction remains a manual post-step).

---

### A.4 — `nbr_uid()` documentation (was Gap #4)

`self_uid()` already fills the "local UID" gap; a `node_uid()` alias is redundant.
The open item is the *neighbour* UID field: `node.nbr_uid()` in C++.

#### Actions

1. Verify `nbr_uid` is in `_FCPP_PRIMITIVES` and emits `nbr_uid(CALL)` correctly.
2. Add a docstring note to `nbr_uid.py` distinguishing it from `self_uid`:
   - `self_uid()` → `node.uid` (scalar, local device UID).
   - `nbr_uid()` → `nbr_uid(CALL)` (neighbourhood field of neighbour UIDs).
3. No new test needed unless `nbr_uid` is currently broken.

---

### A.5 — Step A: Documentation and session save

| File | Action |
|---|---|
| `transpiler/python_ast_visitor.py` | `frozenset` handler + `min_hood` tuple handler |
| `tests/transpiler/test_python_ast_visitor.py` | +5 new tests |
| `examples/worker_role_assignment.py` | add step 5a; fix spawn key |
| `development_history/node_uid__placeholder_flagging.md` | mark §1, §3.3, §3.5 resolved |
| `development_history/WORKER_ROLE_ASSIGNMENT.md` | mark receiver UID gap ✅ |
| `development_history/session_<date>_stepA_transpiler.txt` | session record |
| memory `project_fcpp_bridge.md` | update step A status |

---

## Step B — Library foundations

*Absorbs original v1.8 (logging refactor) and Gap #8 (PhysicalNode RAII).*

Cleans up the library before Steps C–F add more code.  No user-visible behaviour change.

---

### B.1 — `print()` → `get_logger()` in library code (was v1.8 §9.1)

| File | Level mapping |
|---|---|
| `compiler/compiler_core.py` | cache hit → `DEBUG`; compile start/success → `INFO`; failure → `ERROR` |
| `ipc/swarm_process.py` | start/connected/closed → `INFO` |
| `ipc/physical_node.py` | connected/disconnected/reconnect-fail → `INFO` / `WARNING` |
| `ipc/device_manager.py` | start errors → `WARNING`; step errors → `WARNING` |
| `runtime/runtime_generator.py` | generated headers → `INFO` |
| `visualization/text_dashboard.py` | **leave `print`** — it IS the output by design |
| `grammar/generate_antlr.py` | CLI tool — `print` appropriate, not library code |

---

### B.2 — Validation helper in `_example_utils.py` (was v1.8 §9.2)

Every example repeats:

```python
warnings = AggregateValidator.validate(MyClass)
print(f"    OK — {len(warnings)} warning(s)")
for w in warnings:
    print(f"       {w}")
```

Extract to `examples/_example_utils.py`:

```python
def report_validation(cls, logger=None, indent="    "):
    from fcpp_bridge.python_dsl.validators import AggregateValidator
    warnings = AggregateValidator.validate(cls)
    msg = f"{indent}OK — {len(warnings)} warning(s)"
    (logger.info if logger else print)(msg)
    for w in warnings:
        (logger.warning if logger else print)(f"{indent}  {w}")
    return warnings
```

---

### B.3 — `PhysicalNode.connect()` RAII-style reset (was Gap #8)

If `connect()` raises partway through, `_connected` can be left `True` while `backend`
is in a partially initialised state.

Fix: pessimistic reset before any allocation; rollback on failure:

```python
def connect(self) -> None:
    if self.backend is not None:
        self.backend.close()
        self.backend = None
    self._connected = False          # pessimistic reset
    try:
        # ... create backend ...
        self._connected = True       # only set True on full success
    except Exception:
        if self.backend is not None:
            try: self.backend.close()
            except Exception: pass
        self.backend = None
        raise
```

Also wrap `get_state()` and `send_command()` callers: set `_connected = False` on
`ConnectionError` / `OSError`.

---

### B.4 — Step B: Documentation and session save

| File | Action |
|---|---|
| `compiler/compiler_core.py` | print → logger |
| `ipc/swarm_process.py` | print → logger |
| `ipc/physical_node.py` | print → logger + RAII reset |
| `ipc/device_manager.py` | print → logger |
| `runtime/runtime_generator.py` | print → logger |
| `examples/_example_utils.py` | add `report_validation()` |
| `tests/ipc/test_physical_node.py` | +3 tests (RAII: backend raises, partial init, etc.) |
| `development_history/session_<date>_stepB_foundations.txt` | session record |
| memory `project_fcpp_bridge.md` | update step B status |

---

## Step C — OutputChannel + DeviceManager integration

*Absorbs original Gap #9.*

Provides the pluggable output-channel abstraction used by `DeviceManager` for status
messages, and available to `AbstractExample` (Step E) as an optional fan-out mechanism.

---

### C.1 — Design

The design mirrors the existing `ListenerProxy` pattern applied to fleet-wide output.

#### Class hierarchy

```
OutputChannel (ABC)         — abstract base; Prototype pattern (clone())
├── LoggingOutputChannel    — writes via get_logger() (configurable level/format)
├── FileOutputChannel       — writes JSON/CSV lines to a file or stream
├── CallbackOutputChannel   — wraps Callable[[str, Any], None] (name, state)
└── ProxyOutputChannel      — fan-out to N channels; sequential or parallel
```

#### API

```python
class OutputChannel(ABC):
    def send(self, name: str, payload: Any) -> None: ...
    def close(self) -> None: ...
    def clone(self) -> "OutputChannel": ...   # Prototype pattern

class ProxyOutputChannel(OutputChannel):
    def __init__(self, mode: str = "sequential"): ...   # "sequential"|"parallel"
    def add_channel(self, ch: OutputChannel) -> int: ...
    def remove_channel(self, channel_id: int) -> None: ...
```

#### `DeviceManager` integration

```python
class DeviceManager:
    def __init__(self, output_channel: Optional[OutputChannel] = None):
        self._output = output_channel or LoggingOutputChannel()
```

Methods that currently `print(...)` status messages route through
`self._output.send(name, payload)` instead.

---

### C.2 — Step C: Actions and Documentation

| File | Action |
|---|---|
| `ipc/output_channel.py` | `OutputChannel` ABC + `clone()` mixin (NEW) |
| `ipc/logging_output_channel.py` | `LoggingOutputChannel` (NEW) |
| `ipc/file_output_channel.py` | `FileOutputChannel(path_or_stream, format="json")` (NEW) |
| `ipc/callback_output_channel.py` | `CallbackOutputChannel(fn)` (NEW) |
| `ipc/proxy_output_channel.py` | `ProxyOutputChannel(mode="sequential")` (NEW) |
| `ipc/__init__.py` | re-export all five |
| `ipc/device_manager.py` | `output_channel=` kwarg; route status prints |
| `tests/ipc/test_output_channel.py` | +15 tests (NEW) |
| `TUTORIAL_in_depth.md` | add §"Multi-swarm output channels" |
| `README.md` | add `OutputChannel` to feature table |
| `development_history/session_<date>_stepC_outputchannel.txt` | session record |
| memory `project_fcpp_bridge.md` | update step C status |

---

## Step D — Runtime and physical-device support

*Absorbs original Gap #6 (ActivePingStrategy C++ handler) and Gap #7
(DeviceManager.accept_registrations).*

Both concerns are C++ / IPC-layer additions that the examples will use indirectly
(liveness checking during simulation runs).

---

### D.1 — ActivePingStrategy: C++ ping handler (was Gap #6)

`ActivePingStrategy` is fully implemented in Python but the C++ binary has no `ping`
branch in its IPC server loop.  Add to `runtime_generator.py`'s generated
`ipc_server.hpp`:

```cpp
} else if (cmd == "ping") {
    int nid = request["node_id"];
    response["status"] = "pong";
    response["node_id"] = nid;
```

No FCPP round is executed; this is a pure IPC-layer acknowledgement.

#### Actions

1. Add `ping` branch to the C++ template in `RuntimeGenerator.ipc_server_header()`.
2. Update `ActivePingStrategy` docstring: remove "Requires C++ ping handler" warning.
3. Extend `tests/ipc/test_liveness_strategy.py` to cover the pong round-trip scenario.

---

### D.2 — `DeviceManager.accept_registrations(port)` (was Gap #7)

Allows physical devices to self-register instead of requiring Python to initiate
connections.

#### Design

```python
def accept_registrations(
    self,
    port: int,
    on_registered: Optional[Callable[[str, PhysicalNode], None]] = None,
) -> None: ...

def stop_accepting_registrations(self) -> None: ...
```

Payload schema (JSON, POST to `/register`):

```json
{"version": "1.0", "name": "drone-7", "host": "192.168.1.50", "port": 8080, "backend": "http"}
```

Runs a daemon HTTP server thread; on receipt calls `add_physical(name, host, port, backend)`.

#### Actions

1. `ipc/device_manager.py`: add `accept_registrations`, `stop_accepting_registrations`,
   `_registration_server_loop` (daemon thread using `http.server`).
2. `tests/ipc/test_device_manager.py`: +5 tests (registration flow via
   `urllib.request.urlopen`).
3. `TUTORIAL_in_depth.md`: add §"Self-registering physical devices".
4. `README.md`: add `accept_registrations` to DeviceManager bullet.

---

### D.3 — Step D: Documentation and session save

| File | Action |
|---|---|
| `runtime/runtime_generator.py` | add ping handler to C++ template |
| `ipc/device_manager.py` | `accept_registrations` + loop |
| `tests/ipc/test_liveness_strategy.py` | +3 tests (pong round-trip) |
| `tests/ipc/test_device_manager.py` | +5 tests (registration flow) |
| `TUTORIAL_in_depth.md` | §"Self-registering physical devices" |
| `README.md` | feature table updates |
| `development_history/session_<date>_stepD_runtime.txt` | session record |
| memory `project_fcpp_bridge.md` | update step D status |

---

## Step E — AbstractExample toolchain bridge

*New.  Depends on Steps A–D being complete (or at least Step A for correct C++ output
and Step B for clean library foundations).*

---

### E.1 — Motivation

After the 2026-05-28g session, every example file has two classes:

- `@aggregate_function` class — the algorithm specification; meant to be transpiled to
  C++.  Its `compute()` calls DSL primitives (`bis_distance`, `broadcast`, etc.) that do
  not exist in Python.
- `AbstractExample` subclass — a pure-Python simulation that *re-implements the same
  algorithm* using regular Python math, bypassing the entire toolchain.

This defeats the purpose of `fcpp_bridge` for developers reading the examples.  A
developer should see the Python DSL being transpiled and run through FCPP, not a
lookalike re-implementation in plain Python.

The fix: `AbstractExample.run()` must invoke the full pipeline:

```
validate(@aggregate_function class)
  → transpile → C++ source
  → compile → binary  (SHA-256 cached; recompile only when source changes)
  → SwarmProcess.start()
  → add nodes with initial positions
  → for each round: SwarmProcess.step()
  → receive SwarmSnapshot via UpdatesListener callback
  → write per-node log files from snapshot.nodes
```

---

### E.2 — New AbstractExample interface

#### Abstract methods (required)

| Method | Signature | Notes |
|---|---|---|
| `aggregate_class` | `@property → Type` | The `@aggregate_function` class to transpile and run |
| `log_prefix` | `@property → str` | Unchanged — used in log file names |
| `initial_positions` | `() → dict[int, tuple]` | Unchanged — seeds node positions in C++ binary |
| `log_header` | `(node_id, state_data) → str` | `state_data` is now `Any` from `NodeState.state_data` |
| `log_line` | `(round_num, node_id, state_data) → str` | Same signature; `state_data` comes from the FCPP snapshot |

#### Removed abstract methods

| Removed | Reason |
|---|---|
| `round_step(round_num, positions, states) → (positions, states)` | Algorithm runs in C++; Python no longer re-implements it |
| `initial_states(positions) → dict` | C++ binary owns initial state via `initial_state()` in the aggregate class |

#### Optional hooks (updated signatures)

| Hook | Old signature | New signature | Notes |
|---|---|---|---|
| `on_simulation_start()` | `→ None` | unchanged | Called once before the first round |
| `on_simulation_end()` | `→ None` | unchanged | Called once after all rounds |
| `on_round_complete` | `(round_num, positions, states) → None` | `(round_num, snapshot: SwarmSnapshot) → None` | `SwarmSnapshot` replaces the Python-computed dicts |

#### New properties (optional override)

```python
@property
def build_dir(self) -> Path:
    """Cache directory for compiled C++ binaries.  Default: examples/.fcpp_build/"""
    return Path(__file__).parent / ".fcpp_build"

@property
def cpp_dir(self) -> Path:
    """Directory where transpiled C++ source is written.  Default: examples/.fcpp_cpp/"""
    return Path(__file__).parent / ".fcpp_cpp"
```

#### New `run()` skeleton

```python
def run(self, num_rounds: int) -> None:
    from fcpp_bridge.transpiler import Transpiler
    from fcpp_bridge.compiler import Compiler
    from fcpp_bridge.python_dsl.validators import AggregateValidator
    from fcpp_bridge.ipc.swarm_process import SwarmProcess
    from fcpp_bridge.ipc.swarm_snapshot import SwarmSnapshot

    # Validate
    AggregateValidator.validate(self.aggregate_class)

    # Transpile
    t = Transpiler(self.aggregate_class)
    cpp_code = t.generate()

    # Compile (cached by SHA-256)
    self.build_dir.mkdir(parents=True, exist_ok=True)
    self.cpp_dir.mkdir(parents=True, exist_ok=True)
    compiler = Compiler(cache_dir=self.build_dir, cpp_dir=self.cpp_dir)
    binary = compiler.get_or_compile(cpp_code, self.log_prefix)

    # Prepare log directory
    self.log_dir.mkdir(exist_ok=True)

    # Launch swarm
    positions = self.initial_positions()
    swarm = SwarmProcess(binary_path=binary, num_nodes=len(positions))

    log_files: dict = {}

    def _on_snapshot(snapshot: SwarmSnapshot) -> None:
        for ns in snapshot.nodes:
            nid, state = ns.node_id, ns.state_data
            if nid not in log_files:
                path = self.log_dir / f"node_{nid}_{self.log_prefix}.log"
                lf = open(path, "w")
                lf.write(self.log_header(nid, state))
                log_files[nid] = lf
            log_files[nid].write(
                self.log_line(snapshot.round_number, nid, state))
        # Close files for nodes no longer in snapshot
        live = {ns.node_id for ns in snapshot.nodes}
        for gone in set(log_files) - live:
            log_files.pop(gone).close()

    swarm.add_listener(_on_snapshot)
    swarm.start()

    for nid, pos in positions.items():
        swarm.add_node_explicit(nid, pos)

    self.on_simulation_start()

    for round_num in range(num_rounds):
        swarm.step()
        # _on_snapshot fires synchronously within step(); snapshot already written
        last_snapshot = swarm.latest_snapshot()   # or equivalent API
        self.on_round_complete(round_num, last_snapshot)

    for lf in log_files.values():
        lf.close()

    swarm.close()
    self.on_simulation_end()
```

**Note:** the exact API for retrieving the latest snapshot (`swarm.latest_snapshot()` or
`swarm.last_snapshot`) must be verified against the current `SwarmProcess` implementation
and added if missing.

---

### E.3 — Impact on `SwarmProcess`

Verify / add:

- `SwarmProcess.latest_snapshot() → Optional[SwarmSnapshot]` — returns the snapshot from
  the most recent `step()` call (needed by `on_round_complete`).
- `SwarmProcess.add_node_explicit(node_id, position)` — already exists; confirm signature
  accepts `dict[int, tuple]` keys.

---

### E.4 — Step E: Actions and Documentation

| File | Action |
|---|---|
| `examples/abstract_example.py` | Full redesign per E.2 |
| `ipc/swarm_process.py` | Verify/add `latest_snapshot()` |
| `tests/examples/test_abstract_example.py` | NEW — +10 tests (mock Transpiler, Compiler, SwarmProcess; verify run() lifecycle) |
| `development_history/abstract_example_toolchain.md` | NEW — design rationale + interface diff old→new |
| `development_history/EXAMPLES_JOURNAL.md` | Add v2.1 section (toolchain bridge) |
| `DSL_GUIDE.md` | Update §"Running examples" to describe toolchain invocation |
| `README.md` | Update example usage section |
| `TUTORIAL_simple.md` | Update to show that running an example invokes the toolchain |
| `development_history/session_<date>_stepE_toolchain_bridge.txt` | session record |
| memory `project_fcpp_bridge.md` | update step E status + new interface |

---

## Step F — Examples subclasses migration

*New.  Depends on Step E being complete.*

Each of the seven example files must be updated to match the new `AbstractExample`
interface.  The pure-Python algorithm re-implementations are removed; the
`@aggregate_function` class becomes the actual running code.

---

### F.1 — What changes in every subclass

**Removed per subclass:**

- `round_step()` implementation — was a Python re-implementation of the aggregate
  algorithm; no longer needed
- `initial_states()` implementation — C++ handles it; Python-side dataclass constructors
  in `round_step` are gone
- Module-level `_bis_distance_*()` helpers — were pure-Python approximations of FCPP
  primitives; remove entirely
- Other pure-Python helpers that mirror C++ primitives (e.g., `_spanning_tree()`,
  `_routing_sets()`, etc.)

**Added per subclass:**

- `aggregate_class` property returning the existing `@aggregate_function` class defined
  in the same file
- `log_line(round_num, node_id, state_data)` updated: `state_data` is now `Any`
  (dict/JSON from the FCPP binary), not a Python `@dataclass` — field access changes
  from `state.in_channel` to `state_data["in_channel"]` or similar (depends on
  serialization format agreed with the C++ runtime)

**Updated per subclass:**

- `on_round_complete(round_num, snapshot: SwarmSnapshot)` — new signature; any logic
  that previously extracted aggregate counts from the Python-computed states dict is now
  extracted from `snapshot.nodes`
- `on_simulation_end()` — same purpose; `_final_states` attribute pattern is removed
  (get data from `snapshot` in `on_round_complete` instead)
- `log_header(node_id, state_data)` — usually unchanged in content; type annotation
  update only

**Potentially updated in `@aggregate_function` classes:**

Some examples used Python-side scheduling (e.g., `collection_compare.py` switches the
source node at round `NUM_ROUNDS // 2` from inside `round_step`).  In the toolchain
path the C++ binary runs autonomously; Python cannot inject per-round state changes
without an explicit IPC mechanism.  For each such example, choose one of:

a) **Model the scheduling inside `compute()`** using FCPP time primitives (`counter()`,
   `round_since()`, `constant_after()`) — preferred, educationally valuable.
b) **Accept static behaviour** — simplify the example to remove the dynamic aspect.
c) **Extend AbstractExample with a `pre_round_inject(round_num)` optional hook** that
   sends an IPC command to specific nodes before `step()` is called — add to Step E if
   this turns out to be necessary for more than one example.

---

### F.2 — Per-example migration checklist

| Example | Pure-Python helpers to remove | Scheduling logic | Extra logs |
|---|---|---|---|
| `spreading_collection.py` | `_spreading_collection_step()` | none | none |
| `chain_decaying.py` | `_decay_step()` | none | none |
| `channel_broadcast.py` | `_bis_distance()` | none | none |
| `collection_compare.py` | BIS/broadcast manual loop | source switches at round 12.5 → move to `compute()` using `counter()` | none |
| `message_dispatch.py` | `_bis_distance_msg()`, spanning-tree, routing-set loops | message generation rounds 10–50 → move to `compute()` using `counter()` | none (in-flight tracking moves to C++ state) |
| `worker_role_assignment.py` | `_bis_distance_worker()`, routing-set loops | none | `receiver_messages.log` — hook remains in `on_simulation_start/end`; write via `on_round_complete(snapshot)` |
| `communication_roles_assignment.py` | `_bis_dist_comm()`, 6-step algorithm body | none | `comm_receiver_messages.log` — same as above |

For `message_dispatch.py` and `worker_role_assignment.py`, the state structs
(`MessageState`, `WorkerState`) need additional fields to expose what was previously
Python-side cross-round state (e.g., `total_received: int`, `in_flight_count: int`) so
that `log_line()` can write them from `state_data`.

---

### F.3 — Step F: Actions and Documentation

| File | Action |
|---|---|
| `examples/spreading_collection.py` | Remove `round_step` + helpers; add `aggregate_class` |
| `examples/chain_decaying.py` | Same |
| `examples/channel_broadcast.py` | Same |
| `examples/collection_compare.py` | Same; update `compute()` to use `counter()` for source switch |
| `examples/message_dispatch.py` | Same; update `compute()` + state dataclass for in-flight exposure |
| `examples/worker_role_assignment.py` | Same; update `on_round_complete(snapshot)` for recv log |
| `examples/communication_roles_assignment.py` | Same |
| `development_history/EXAMPLES_JOURNAL.md` | Add v2.1 entry per example |
| `development_history/session_<date>_stepF_examples_migration.txt` | session record |
| memory `project_fcpp_bridge.md` | update test count + step F status |

**Verification per example:** smoke-test with `--steps validate transpile` (can run
without FCPP installed); full `--steps validate transpile compile run` requires FCPP
headers.

---

## Implementation Checklist

Ordered by dependency; each step must end with docs, memory save, and session record.

### Step A — Transpiler completeness

- [ ] `frozenset` → `set_t{...}` in `PythonAstVisitor.visit_Call`
- [ ] `min_hood`/`max_hood` + Tuple → `std::make_tuple(...)` in `visit_Call`
- [ ] `worker_role_assignment.py`: add step 5a `receiver_uid = broadcast(...)`; fix spawn key
- [ ] Tests: `test_frozenset_to_set_t` (2), `test_min_max_hood_tuple` (2), `test_worker_broadcast_transpiles` (1)
- [ ] Docs: `node_uid__placeholder_flagging.md`, `WORKER_ROLE_ASSIGNMENT.md`
- [ ] Save session record `session_<date>_stepA_transpiler.txt`
- [ ] Save memory

### Step B — Library foundations

- [ ] `print` → `get_logger()` in: `compiler_core.py`, `swarm_process.py`,
  `physical_node.py`, `device_manager.py`, `runtime_generator.py`
- [ ] `PhysicalNode.connect()`: pessimistic `_connected` reset + exception rollback
- [ ] `_IpcNodeBase`: wrap `get_state()`/`send_command()` to set `_connected = False` on error
- [ ] `_example_utils.py`: add `report_validation()`
- [ ] Tests: `test_physical_node.py` +3 (RAII scenarios)
- [ ] Save session record `session_<date>_stepB_foundations.txt`
- [ ] Save memory

### Step C — OutputChannel

- [ ] `ipc/output_channel.py` — ABC + `clone()`
- [ ] `ipc/logging_output_channel.py`
- [ ] `ipc/file_output_channel.py`
- [ ] `ipc/callback_output_channel.py`
- [ ] `ipc/proxy_output_channel.py`
- [ ] `ipc/__init__.py` re-exports
- [ ] `device_manager.py`: `output_channel=` kwarg; route status messages
- [ ] Tests: `test_output_channel.py` +15
- [ ] Docs: `TUTORIAL_in_depth.md` §, `README.md`
- [ ] Save session record `session_<date>_stepC_outputchannel.txt`
- [ ] Save memory

### Step D — Runtime & physical-device support

- [ ] `runtime_generator.py`: add `ping` handler to C++ IPC server template
- [ ] `ActivePingStrategy` docstring: remove "Requires C++ ping handler" warning
- [ ] `device_manager.py`: `accept_registrations(port)` + `stop_accepting_registrations()`
- [ ] Tests: `test_liveness_strategy.py` +3; `test_device_manager.py` +5
- [ ] Docs: `TUTORIAL_in_depth.md` §, `README.md`
- [ ] Save session record `session_<date>_stepD_runtime.txt`
- [ ] Save memory

### Step E — AbstractExample toolchain bridge

- [ ] Investigate `SwarmProcess.latest_snapshot()` — add if missing
- [ ] `abstract_example.py`: rewrite `run()` per E.2; update abstract method set
- [ ] Verify `log_header`/`log_line` signatures with `state_data: Any` (not dataclass)
- [ ] `tests/examples/test_abstract_example.py` — NEW, +10 tests (mocked pipeline)
- [ ] Docs: `abstract_example_toolchain.md` (NEW), `EXAMPLES_JOURNAL.md`, `DSL_GUIDE.md`,
  `README.md`, `TUTORIAL_simple.md`
- [ ] Save session record `session_<date>_stepE_toolchain_bridge.txt`
- [ ] Save memory

### Step F — Examples subclasses migration

For each of the 7 examples:
- [ ] `spreading_collection.py`: remove `round_step`, helpers; add `aggregate_class`
- [ ] `chain_decaying.py`: same
- [ ] `channel_broadcast.py`: same
- [ ] `collection_compare.py`: same + update `compute()` (source switch → `counter()`)
- [ ] `message_dispatch.py`: same + update `compute()` + state struct fields
- [ ] `worker_role_assignment.py`: same + update `on_round_complete(snapshot)` for recv log
- [ ] `communication_roles_assignment.py`: same + update `on_round_complete(snapshot)` for comm log
- [ ] Smoke-test all examples (`--steps validate transpile` minimum)
- [ ] Docs: `EXAMPLES_JOURNAL.md` v2.1 section; update per-example entries
- [ ] Save session record `session_<date>_stepF_examples_migration.txt`
- [ ] Save memory

---

## Estimated test delta

| Step | Component | New tests |
|---|---|---|
| A | Transpiler (frozenset, min_hood tuple, broadcast) | +5 |
| B | PhysicalNode RAII | +3 |
| C | OutputChannel + ProxyOutputChannel | +15 |
| D | ActivePingStrategy pong round-trip; DeviceManager.accept_registrations | +8 |
| E | AbstractExample toolchain (mocked pipeline) | +10 |
| F | Example smoke tests (validate+transpile path) | +7 |
| **Total** | | **+48** |

Projected total: **624 + 48 = 672 tests**

*(The previous estimate of 644 did not include Steps E and F.)*
