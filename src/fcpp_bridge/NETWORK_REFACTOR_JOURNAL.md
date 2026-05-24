# Network Listener & Node Addition Refactor Journal

**Started:** 2026-05-24  
**Branch:** bugfix/fcpp_bridge/it1  
**Scope:** `fcpp_bridge/ipc/` only

## Goal

Refactor two related concerns in the IPC layer:

1. **Node addition strategies** — `SwarmProcess.add_nodes(count)` was the only way to
   add nodes.  Three strategies are now supported (random ID, sequential ID, explicit
   ID+position) plus `remove_node(node_id)` and a passive heartbeat/liveness monitor.

2. **Updates listener pipeline** — `IpcBackend.subscribe_state_updates(callback)` was a
   single, noop-default slot.  Now `SwarmProcess` exposes a multi-listener proxy system
   with per-node listener overrides.

The "updates listener is NOT defined per-node" condition was confirmed (the existing
`subscribe_state_updates` is per-backend/per-swarm), so both parts are in scope.

---

## Steps

| # | File(s) | Description | Status |
|---|---------|-------------|--------|
| 1 | `NETWORK_REFACTOR_JOURNAL.md` | Create this journal | ✅ Done |
| 2 | `ipc/updates_listener.py` | `UpdatesListener` type alias | ✅ Done |
| 3 | `ipc/listener_proxy.py` | `ListenerProxy` (sequential / parallel-async) | ✅ Done |
| 4 | `ipc/swarm_process.py` | Node strategies, remove, heartbeat, listener mgmt | ✅ Done |
| 5 | `ipc/ipc_backend.py` + `ipc/__init__.py` | Signature update + new exports | ✅ Done |
| 6 | `tests/ipc/test_network_listener.py` | New test file (38 tests) | ✅ Done |
| 7 | Test suite run | 520 pass, 0 fail (was 482) | ✅ Done |
| 8 | README.md, memory | Documentation update | ✅ Done |

## v1.1 additions (same session, 2026-05-24)

| # | File(s) | Description | Status |
|---|---------|-------------|--------|
| 9  | `compiler/compiler_core.py` | Add `std`, `opt_level`, `extra_includes` constructor params | ✅ Done |
| 10 | `tests/compiler/test_compiler_core.py` | 3 new tests for new params | ✅ Done |
| 11 | `TUTORIAL_simple.md` | Beginner tutorial: hop-channel (20 nodes) | ✅ Done |
| 12 | `TUTORIAL_in_depth.md` | Production tutorial: `HopChannelSimulation` class | ✅ Done |
| 13 | README.md, memory | Documentation + v1.1 section | ✅ Done |

**Final test count: 523 pass, 0 fail.**

---

## Architecture

### New files

```
ipc/
├── updates_listener.py    UpdatesListener = Callable[[SwarmSnapshot], None]
└── listener_proxy.py      ListenerProxy   sequential / parallel-async
```

### `ListenerProxy`

```
ListenerProxy(mode="sequential"|"parallel")
  .add_listener(fn)   → listener_id: int
  .remove_listener(id)
  .__call__(snapshot)  dispatches to all registered listeners
  .close()             shuts down thread pool (parallel mode)
```

### `SwarmProcess` new API

```
# Node addition
add_nodes_random(count, *, area=None, comm_range=None, max_speed=None, propulsion=None)
  → List[int]   # newly assigned random IDs
add_node_explicit(node_id, position, *, comm_range=None, max_speed=None, propulsion=None)
  → None
add_nodes_sequential(count, start_positions=None)
  → List[int]
add_nodes(count)  # backward-compat; delegates to add_nodes_sequential

# Node removal
remove_node(node_id)

# Heartbeat / liveness (passive: based on last received snapshot)
check_liveness(timeout=30.0)  → Dict[int, bool]
start_heartbeat_monitor(interval=5.0, timeout=30.0, on_dead=None)
stop_heartbeat_monitor()

# Listener management (global)
add_listener(listener)          → listener_id: int   (auto-creates proxy)
remove_listener(listener_id)

# Listener management (per-node override)
add_node_listener(node_id, listener)     → listener_id: int
remove_node_listener(node_id, listener_id)
```

### Dispatch logic

`SwarmProcess._dispatch_update(snapshot)` is wired as the push callback of the
IPC backend.  It also updates heartbeat timestamps.  Routing:

```
for each node in snapshot.nodes:
    if node.node_id in _node_listeners → call per-node listener
    elif _global_listener is set       → call global listener
```

`SwarmProcess.get_state()` (pull path) also calls `_update_heartbeats` so that
passive liveness detection works even without a live push subscription.

---

## Design Decisions

* **Proxy always used internally** — `add_listener` always creates/uses a
  `ListenerProxy`, so the caller always gets back an integer ID they can use to
  remove the listener later.  The single-listener fast-path is available through
  plain `_dispatch_update` skipping the proxy if none is installed.

* **Passive heartbeat** — Tracks the timestamp of the last received `NodeState`
  per node ID.  Active ping/pong would require C++ side support; that is left for
  future work.  The `start_heartbeat_monitor` background thread calls
  `check_liveness` periodically and invokes `on_dead(node_id)` for stale nodes.

* **Backward compatibility** — `add_nodes(count)` is preserved; it delegates to
  `add_nodes_sequential`.  Existing tests are unaffected.

* **`_known_node_ids`** — Initialised from `range(num_nodes)` at `start()` time
  (assumes initial nodes got sequential IDs 0..N-1).  Random IDs are guaranteed
  unique within the set; explicit IDs are validated against it.

---

## Resume Instructions

If the task is interrupted, resume by checking which rows in the Steps table above
are NOT marked ✅ Done, then continue from that step.
