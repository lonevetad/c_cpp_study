# Physical Device Deployment Refactor Journal

**Started:** 2026-05-25  
**Branch:** bugfix/fcpp_bridge/it1  
**Scope:** `fcpp_bridge/ipc/` — add physical device deployment support

## Goal

The project previously only supported **simulation mode**: all nodes ran inside a
single C++ subprocess spawned and controlled by Python.

FCPP's actual purpose is to write **one** aggregate program and run it on a fleet
of heterogeneous physical devices (robots, drones, mobile phones, sensors, …) that
connect and disconnect **autonomously** at unpredictable times.

This refactor adds **physical deployment mode** while keeping simulation mode
fully backward-compatible.

---

## Steps

| # | File(s) | Description | Status |
|---|---------|-------------|--------|
| 1 | `PHYSICAL_DEPLOYMENT_JOURNAL.md` | Create this journal | ✅ Done |
| 2 | `ipc/_ipc_node_base.py` | `_IpcNodeBase`: shared listener pipeline + heartbeat | ✅ Done |
| 3 | `ipc/physical_node.py` | `PhysicalNode`: connects to an already-running device | ✅ Done |
| 4 | `ipc/swarm_process.py` | Inherit from `_IpcNodeBase`; remove duplicated code | ✅ Done |
| 5 | `ipc/device_manager.py` | Heterogeneous fleet: `add_simulation`, `add_physical` | ✅ Done |
| 6 | `ipc/__init__.py` | Export `_IpcNodeBase`, `PhysicalNode` | ✅ Done |
| 7 | `tests/ipc/test_physical_node.py` | 32 new tests | ✅ Done |
| 8 | `tests/ipc/test_device_manager.py` | 8 new tests | ✅ Done |
| 9 | Test suite run | 555 pass, 0 fail (was 523) | ✅ Done |
| 10 | README.md, memory | Documentation update | ✅ Done |

**Test count after v1.2: 555 pass (+32 PhysicalNode, +8 DeviceManager).**  
**Test count after v1.3: 578 pass (+23 liveness strategies).**

---

## Architecture

### Simulation mode (unchanged)

```
Python
  └─ SwarmProcess(binary_path, num_nodes)
       └─ spawns:  ./binary --num-nodes=N
       └─ drives:  step() → {"cmd": "step"}
       └─ queries: get_state() → SwarmSnapshot (all nodes)
       └─ listens: add_listener(fn) → push updates
```

Python owns the simulation lifecycle entirely.  Nodes are added/removed on
Python's command via IPC (`add_nodes_*`, `remove_node`).

### Physical deployment mode (new)

```
Physical network
  ├─ device-A  runs ./binary  (e.g. robot, port 8080)
  ├─ device-B  runs ./binary  (e.g. drone, port 8080)
  └─ device-C  runs ./binary  (e.g. phone, port 8080)

Python
  └─ DeviceManager
       ├─ add_physical("robot",  "192.168.1.10", 8080)  → PhysicalNode
       ├─ add_physical("drone",  "192.168.1.11", 8080)  → PhysicalNode
       └─ add_physical("phone",  "192.168.1.12", 8080)  → PhysicalNode

PhysicalNode("192.168.1.10", 8080)
  └─ connect()   →  HttpBackend / GrpcBackend  (no subprocess!)
  └─ get_state() → SwarmSnapshot (pull path)
  └─ add_listener(fn)         → push updates
  └─ on_neighbor_joined(fn)   → FCPP-level neighbor joins
  └─ on_neighbor_left(fn)     → FCPP-level neighbor leaves (heartbeat)
  └─ start_auto_reconnect()   → background thread retries on drop
  └─ close()                  → disconnects Python; device keeps running
```

Devices run their own FCPP round loop.  No `step()` command is issued by Python.
Nodes join/leave the FCPP neighborhood autonomously via radio.

### Inheritance hierarchy

```
_IpcNodeBase
├── get_state()
├── check_liveness(), start/stop_heartbeat_monitor()
├── add/remove_listener(), add/remove_node_listener(), _dispatch_update()
└── close()                ← base close: stops heartbeat, closes backend

SwarmProcess(_IpcNodeBase)
├── __init__(binary_path, num_nodes, ...)
├── start()                ← spawns subprocess
├── close()                ← super().close() + terminates process
├── step()
└── add_nodes_*, remove_node, _create_backend

PhysicalNode(_IpcNodeBase)
├── __init__(host, port, backend_type, ...)
├── connect()              ← creates HttpBackend / GrpcBackend (no subprocess)
├── close()                ← stops reconnect, super().close(); device keeps running
├── start/stop_auto_reconnect()
├── on_neighbor_joined(cb) ← fires when new node_id appears in snapshot
├── on_neighbor_left(cb)   ← fires via heartbeat when node goes silent
└── override: _dispatch_update, start_heartbeat_monitor
```

### `DeviceManager` heterogeneous fleet

```python
mgr = DeviceManager()

# Simulation
mgr.add_simulation("lab", binary_path, num_nodes=100)   # SwarmProcess
mgr.add("lab2", binary_path)                            # backward-compat alias

# Physical deployment
mgr.add_physical("robot-1", "192.168.1.10", 8080)      # PhysicalNode (HTTP)
mgr.add_physical("drone-1", "192.168.1.20", 50051,
                 backend_type="grpc")                   # PhysicalNode (gRPC)

# Fleet-wide operations
mgr.start_all()        # starts all SwarmProcess instances
mgr.connect_all()      # connects to all PhysicalNode instances
mgr.step_all()         # steps only SwarmProcess; PhysicalNodes are skipped
mgr.get_all_states()   # works for both
mgr.close_all()        # closes everything
```

---

## Design Decisions

* **`_IpcNodeBase` not exported as public API** — underscore prefix; advanced users
  who need to subclass can import it explicitly.  Both `SwarmProcess` and
  `PhysicalNode` are the intended public classes.

* **No `step()` on `PhysicalNode`** — FCPP devices run a self-paced round loop
  determined by the C++ binary.  Sending a Python "step" command to a physical
  device would be wrong and is not modeled.

* **Autonomous join/leave is FCPP-level** — `on_neighbor_joined` / `on_neighbor_left`
  describe neighbors within radio range of the device, not device-to-Python
  connection events.  Connection events are managed by `connect()` / `close()` /
  `start_auto_reconnect()`.

* **Passive heartbeat is shared** — both simulation and physical nodes use the same
  timestamp-based liveness mechanism.  For physical nodes, heartbeat also drives
  the `on_neighbor_left` callbacks via the overridden `start_heartbeat_monitor`.

* **Auto-reconnect is best-effort** — the reconnect thread calls `connect()` every
  `reconnect_interval` seconds while `is_connected is False`.  There is a race
  condition window where a close-and-reconnect can create a brief dangling backend;
  this is acceptable for the expected usage (network transience) and documented
  as a known limitation.

* **`DeviceManager.total_nodes()`** — uses the new `node_count` property from
  `_IpcNodeBase`: `SwarmProcess.node_count` returns `num_nodes`; `PhysicalNode.node_count`
  returns `len(_seen_node_ids) or 1` (at least 1 — the device itself).

---

## Resume Instructions

If the task is interrupted, check the Steps table above for any row not marked
✅ Done, then continue from there.
