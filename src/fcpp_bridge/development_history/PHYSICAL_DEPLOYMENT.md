# Physical Device Deployment — Analysis, Changes, and Rationale

**Date:** 2026-05-25  
**Branch:** `bugfix/fcpp_bridge/it1`  
**Scope:** `fcpp_bridge/ipc/`  
**Test delta:** 523 → 555 (+32 PhysicalNode, +8 DeviceManager)

---

## 1. Background

FCPP (Field Calculus C++) is a framework for **aggregate computing**: the programmer
writes a *single* aggregate program expressing the collective behaviour of a network,
and the framework distributes it so that every node in the network runs the same code.
Each node only sees its own local state and the states of its immediate neighbors
(those within communication range).

The intended deployment lifecycle is:
1. **Write** the aggregate program once (in C++, or via the Python DSL in this project).
2. **Compile** it to an executable binary.
3. **Deploy** that binary to *every* physical device in the fleet (robots, drones,
   mobile phones, sensors, fixed workstations, …).
4. Each device **runs the binary autonomously** — its round loop is driven by the
   device's own clock, not by an external controller.
5. Devices **join and leave** the network unpredictably: a drone might fly out of
   radio range; a phone might lose WiFi; a robot might be powered off.
6. A **Python controller** (this project) can optionally observe the fleet, collect
   metrics, adjust parameters, or visualize state — but it is *not* in the critical
   path; the aggregate program keeps running without it.

---

## 2. Analysis — What Was Checked

Before writing any code, the following files were read in full and analyzed:

| File | Purpose | Finding |
|------|---------|---------|
| `ipc/swarm_process.py` | Main runtime management class | Simulation-only; always spawns a local subprocess |
| `ipc/device_manager.py` | Fleet manager | Subprocess-centric; no concept of remote device |
| `ipc/ipc_backend.py` | Backend ABC | Interface is generic enough to support both modes |
| `ipc/__init__.py` | Package exports | Missing exports for the new classes to be added |

### Findings in `SwarmProcess`

```python
# start() — hardwired to spawn a local binary
self.process = subprocess.Popen(
    [str(self.binary_path), f"--num-nodes={self.num_nodes}"],
    ...
)

# step() — simulation-only: no physical device accepts a "step" command
self.backend.send_command({"cmd": "step"})

# add_nodes_random / add_nodes_sequential / add_node_explicit
# — physical devices join the network on their own; Python cannot "add" them
self.backend.send_command({"cmd": "add_nodes", "nodes": [...]})
```

**Conclusion**: `SwarmProcess` models *one central process that owns all nodes*.
Physical devices own themselves; the central-control model does not apply.

### Findings in `DeviceManager`

```python
def add(self, name, binary_path, num_nodes, ipc_backend, ipc_port) -> SwarmProcess:
    proc = SwarmProcess(binary_path=binary_path, ...)  # always a local binary
    ...
```

**Conclusion**: `DeviceManager` can only hold `SwarmProcess` instances; it has no
way to represent a connection to a remote device.

### Findings in `IpcBackend`

```python
class IpcBackend(ABC):
    def send_command(self, cmd) -> dict: ...
    def get_state(self) -> SwarmSnapshot: ...
    def subscribe_state_updates(self, callback): ...
    def close(self): ...
```

**Conclusion**: The backend interface is backend-agnostic.  `HttpBackend` and
`GrpcBackend` already use a host:port argument — they can connect to a remote
device.  The gap is in the layer *above* the backend, not inside it.

### What Was Identified as Missing

1. A class that **connects TO** a physical device without spawning a subprocess.
2. Auto-reconnect logic for transient network drops (a drone crossing a WiFi dead
   zone should not crash the Python controller permanently).
3. Notification when **FCPP-level neighbors join or leave** the device's radio
   neighborhood (distinct from "device connects/disconnects to Python").
4. A `DeviceManager` that can hold both simulation and physical entries in the
   same fleet.
5. `step_all()` must not attempt to drive physical devices (they run their own loop).
6. A shared base class to eliminate the heartbeat and listener pipeline code that
   would otherwise have to be duplicated between `SwarmProcess` and the new class.

---

## 3. Design Decisions

### 3.1 — New class: `PhysicalNode` rather than a mode flag on `SwarmProcess`

**Option considered but rejected**: Add `mode="simulation"|"physical"` parameter
to `SwarmProcess`.

**Why rejected**: `SwarmProcess` would have become a branching monolith — many
methods (`step`, `add_nodes_*`, `remove_node`, `start`) would need
`if self.mode == "simulation":` guards, making the class harder to reason about
and test. The two modes are fundamentally *different contracts*, not the same
contract with different parameters.

**Decision**: A new, separate class `PhysicalNode` with a completely different
lifecycle (`connect` instead of `start`; no `step`, no `add_nodes`). This keeps
each class focused and its contract clear.

### 3.2 — Shared base class: `_IpcNodeBase`

`SwarmProcess` and `PhysicalNode` share a large block of identical behavior:

- The listener pipeline (`ListenerProxy`, `add_listener`, `add_node_listener`, …)
- Passive heartbeat (`_heartbeat_timestamps`, `check_liveness`, `start_heartbeat_monitor`)
- `get_state()` pull path

**Option considered but rejected**: Duplicate the code into both classes (copy-paste).

**Why rejected**: Any future fix or feature (e.g., adding a parallel-mode listener)
would need to be applied in two places, guaranteed to diverge over time.

**Decision**: Extract a private base class `_IpcNodeBase` (underscore prefix signals
it is an implementation detail, not part of the public API). Both `SwarmProcess` and
`PhysicalNode` inherit from it. `_IpcNodeBase` also defines `close()` as the shared
teardown path, so each subclass calls `super().close()` and then does its own cleanup.

The `node_count` property is declared on the base (returns 0) and overridden
by each subclass: `SwarmProcess.node_count → num_nodes`;
`PhysicalNode.node_count → len(_seen_node_ids) or 1`.  This allows
`DeviceManager.total_nodes()` to work uniformly across both types.

### 3.3 — Autonomous join/leave at the FCPP level

In FCPP, a "node joining the network" can mean two distinct things:

| Event | Who controls it | How it arrives |
|-------|----------------|----------------|
| Python adds a virtual node | Python (`add_nodes_*` command) | Sent to simulation via IPC |
| A neighbor device enters radio range | FCPP runtime (C++ side) | Appears in next SwarmSnapshot |

For `PhysicalNode`, only the second kind is relevant.  `on_neighbor_joined(cb)` is
triggered by the **first time** a `node_id` appears in any incoming `SwarmSnapshot`.
This is a software-side detection of the radio-level FCPP join event — no C++ runtime
changes required.

`on_neighbor_left(cb)` is driven by the existing **passive heartbeat** mechanism:
when a node's timestamp in `_heartbeat_timestamps` exceeds the configured timeout,
the heartbeat monitor fires `on_dead(node_id)`.  In `PhysicalNode.start_heartbeat_monitor`,
this is composed with the `_neighbor_leave_callbacks` list and a `_seen_node_ids.discard(nid)`
call, so the node is also removed from the "seen" set for future join detection.

**Why passive heartbeat (not active ping/pong)**: Active heartbeat requires C++ runtime
support — the binary would need to respond to a "ping" IPC command with a "pong" response.
The C++ runtime is outside this project's scope.  Passive heartbeat (absence of updates
within a timeout window) is a pure Python-side mechanism that works with any backend.

### 3.4 — Auto-reconnect design

Physical devices have transient connectivity.  A robot might move out of WiFi range
for 10 seconds and then come back.  The Python controller should survive this without
requiring a manual `connect()` call.

**Design**: `start_auto_reconnect()` launches a daemon thread that checks `is_connected`
every `reconnect_interval` seconds and calls `connect()` if False.

`is_connected` is a simple boolean flag: `True` after `connect()`, `False` after
`close()`.  The current implementation does **not** automatically set `is_connected = False`
when a backend call raises an exception — this is a known gap documented as future work.
For now, the caller can call `node.close()` to trigger a reconnect cycle, or wrap
backend calls with a try/except that calls `close()`.

**Why not raise immediately on exception?** The reconnect thread is designed for
predictable, expected disconnections (link drops, device reboots), not for exception
handling. Mixing exception propagation with the reconnect state machine would add
complexity without a clear contract for the caller.

### 3.5 — `DeviceManager` changes

The existing `add(name, binary_path, ...)` is kept as a backward-compatible alias for
the new `add_simulation(name, binary_path, ...)`.  All existing tests pass unchanged.

`_devices` was changed from `Dict[str, SwarmProcess]` to `Dict[str, _IpcNodeBase]`.
This is a minor type-annotation change — at runtime the stored objects are the same
`SwarmProcess` instances as before for simulation entries.

`step_all()` now skips `PhysicalNode` instances with an `isinstance` check.  The
docstring explains that physical devices drive themselves.  An alternative would have
been to give `_IpcNodeBase` a `step()` no-op — this was rejected because calling
`step()` on a physical node is a programming error that should be visible as an
`AttributeError`, not silently swallowed.

`start_all()` and `connect_all()` are split: `start_all` calls `start()` on every
`SwarmProcess`; `connect_all` calls `connect()` on every `PhysicalNode`.  Mixing them
into a single "start_or_connect_all" would obscure the semantics.

---

## 4. Changes Made

### New files

| File | Description |
|------|-------------|
| `ipc/_ipc_node_base.py` | `_IpcNodeBase`: shared listener pipeline + heartbeat + close |
| `ipc/physical_node.py` | `PhysicalNode`: physical device connection |
| `tests/ipc/test_physical_node.py` | 32 tests covering all PhysicalNode behavior |
| `PHYSICAL_DEPLOYMENT_JOURNAL.md` | Step-by-step status tracker for this refactor |
| `PHYSICAL_DEPLOYMENT.md` | This document |

### Modified files

**`ipc/swarm_process.py`**:
- `class SwarmProcess(_IpcNodeBase)` — now inherits from the base
- `__init__` calls `super().__init__(listener_mode=listener_mode)`, removes fields
  now owned by the base (`_heartbeat_timestamps`, `_heartbeat_thread`, etc.)
- `close()` calls `super().close()` then terminates the subprocess
- Added `node_count` property returning `self.num_nodes`
- Removed ~80 lines of code that are now in `_IpcNodeBase`

**`ipc/device_manager.py`**:
- `_devices: Dict[str, _IpcNodeBase]` (was `Dict[str, SwarmProcess]`)
- `add()` kept as backward-compatible alias → delegates to `add_simulation()`
- New `add_simulation(name, binary_path, ...)` → `SwarmProcess`
- New `add_physical(name, host, port, ...)` → `PhysicalNode`
- New `connect(name)` / `connect_all()` for physical nodes
- `start_all()` now skips `PhysicalNode` entries
- `step_all()` now skips `PhysicalNode` entries (with comment explaining why)
- `total_nodes()` changed to `sum(device.node_count for …)` (uses new property)
- New `start(name)` / `connect(name)` raise `TypeError` with helpful message if
  wrong method is called for the wrong device type

**`ipc/__init__.py`**:
- Added `_IpcNodeBase` and `PhysicalNode` to imports and `__all__`

**`tests/ipc/test_device_manager.py`**:
- Import added: `PhysicalNode`
- 8 new tests: `add_physical`, `add_simulation`, duplicate raises, `get` returns
  `PhysicalNode`, `step_all` skips physical, `total_nodes` mixed, `device_count`
  includes both types

### Documentation updated

| File | Change |
|------|--------|
| `README.md` | Added v1.2 row to phase table; updated test count to 555; updated file-structure tree; added v1.2 narrative section; updated comparison table |
| `src/bridge.md` | Status → v1.2; date → 2026-05-25; added step 15 to phase-by-phase rollout; updated total count |
| `REFACTOR_TESTS_JOURNAL.md` | Updated current total to 555 |
| `memory/project_fcpp_bridge.md` | Updated description, phase table, phase-4 narrative, total count |
| `memory/MEMORY.md` | Updated one-liner for fcpp_bridge entry |

---

## 5. What Was Not Changed

- The three IPC backends (`UnixSocketBackend`, `HttpBackend`, `GrpcBackend`) —
  `HttpBackend` and `GrpcBackend` already support remote endpoints via their
  constructor arguments; they needed no changes.
- The `IpcBackend` ABC — its interface was already generic enough.
- The `ListenerProxy` and `UpdatesListener` types — reused as-is.
- Existing `SwarmProcess` tests — all 17 tests pass without modification.
  The `add_nodes(count)` backward-compat alias was preserved; the test that checks
  `add_nodes(5)` increments `num_nodes` by 5 and calls `send_command` once still passes.

---

## 6. Known Gaps (After v1.2)

| Gap | Reason not addressed |
|-----|----------------------|
| Auto-set `is_connected = False` on backend exception | Complex exception-propagation contract; documented as user responsibility |
| `DeviceManager.accept_registrations(port)` | Requires socket server; out of scope |
| Active heartbeat (ping/pong) | Requires C++ runtime support — addressed as `ActivePingStrategy` in v1.3 (C++ side still needed) |
| Multi-swarm coordination UI | Frontend work; unrelated to IPC layer |

---

## 7. Test Coverage Summary (v1.2)

| Test file | Tests | What is covered |
|-----------|-------|-----------------|
| `test_physical_node.py` | 32 | Construction, connect (HTTP/gRPC), connect with invalid type, close, context manager, get_state, listeners (inherited), liveness (inherited), on_neighbor_joined (new/duplicate/multiple), on_neighbor_left via heartbeat, on_dead + on_neighbor_left combined, auto-reconnect idempotency and stop, node_count |
| `test_device_manager.py` (new tests only) | 8 | add_physical, add_simulation, duplicate raises, get returns PhysicalNode, step_all skips physical, total_nodes mixed, device_count both types |
| `test_swarm_process.py` (unchanged) | 17 | All pass — backward compatibility verified |
| `test_device_manager.py` (existing) | 14 | All pass — total_nodes still sums correctly via node_count |

---

## 8. v1.3 — Pluggable Liveness Strategies

### What Was Changed

The "passive heartbeat" was hardwired directly into `_IpcNodeBase` with no abstraction.
The user's requirement was that liveness checking be configurable at both construction time
and runtime, and support modern alternatives alongside the passive approach.

**New file: `ipc/liveness_strategy.py`**

`LivenessStrategy` ABC defines the contract:

```
on_snapshot(snapshot)          # called on every received snapshot
check(**kwargs) → {id: bool}   # query current liveness; unknown kwargs ignored
discard(node_id)               # remove a node from tracking (explicit removal)
close()                        # release resources (threads, sockets)
```

Three built-in implementations:

| Strategy | How it works | C++ requirement |
|----------|-------------|-----------------|
| `PassiveHeartbeatStrategy(timeout=30.0)` | Alive if last snapshot ≤ timeout s ago | None |
| `ActivePingStrategy(backend_getter, ping_timeout=2.0)` | Sends `{"cmd":"ping"}`, expects `{"status":"pong"}` | Ping handler in binary |
| `AlwaysAliveStrategy()` | Always returns True | None |

**`_IpcNodeBase` changes** (all backward-compatible):

- `__init__(liveness_strategy=None)` — default: `PassiveHeartbeatStrategy()`
- `set_liveness_strategy(strat)` — closes old strategy, installs new one
- `_heartbeat_timestamps` — property returning `strat._timestamps` for passive strategy
  (backward compat for the 7 existing tests that accessed this dict directly)
- `check_liveness(timeout=30.0, **kwargs)` — delegates to `strategy.check(timeout=timeout, **kwargs)`
- `_discard_node_from_liveness(node_id)` — calls `strategy.discard(node_id)`
- `close()` — calls `strategy.close()` before closing backend

**`SwarmProcess.remove_node`** changed `self._heartbeat_timestamps.pop(node_id)` →
`self._discard_node_from_liveness(node_id)` — decoupled from the passive strategy's internals.

**Constructor propagation**: `SwarmProcess`, `PhysicalNode`, `DeviceManager.add_simulation`,
`DeviceManager.add_physical` all accept `liveness_strategy=`.

### Design Rationale

**Strategy pattern** was chosen over a simple `mode="passive"|"active"` enum because:
- New strategies can be added without touching `_IpcNodeBase` (Open/Closed principle)
- The `backend_getter` lambda in `ActivePingStrategy` means reconnects are transparent —
  the strategy always uses the latest backend without being re-registered
- `AlwaysAliveStrategy` lets tests and simple deployments opt out of liveness entirely
  without special-casing in the monitor code
- Strategies are first-class objects — they can be shared, composed, or mocked in tests

**Backward compatibility**: `_heartbeat_timestamps` as a property keeps all 7 existing tests
that poke the dict directly working unchanged.  The property returns a live reference to
the passive strategy's `_timestamps` dict, so reads and writes work as before.

### Test Coverage (v1.3)

| Test file | Tests | What is covered |
|-----------|-------|-----------------|
| `test_liveness_strategy.py` | 23 | PassiveHeartbeatStrategy (default timeout, on_snapshot, check alive/dead, timeout override, discard, unknown kwargs); ActivePingStrategy (on_snapshot, pong→alive, wrong response→dead, exception→dead, no backend, ping_timeout override, discard); AlwaysAliveStrategy (always alive, discard, ignore kwargs); integration: set_liveness_strategy replaces + closes old, constructor kwarg on SwarmProcess + PhysicalNode, check_liveness delegates to active strategy |
| All pre-existing tests | 555 | All pass — 0 regressions |
