# fcpp_bridge — In-Depth Tutorial (Production & Professional)

**Goal**: Same hop-channel algorithm as the simple tutorial (20 nodes, source=3,
destination=18, BIS distance + hop count + broadcast), but wrapped in a
production-quality simulation class that supports:

- Fully customised compilation (C++ standard, optimisation level, include paths,
  output paths for generated sources and compiled binaries)
- A multi-listener update pipeline (`ListenerProxy`) with per-node overrides
- Dynamic listener addition and removal
- Clean start / pause / resume / stop lifecycle
- Node addition (random, sequential, explicit ID) and removal at runtime
- Passive heartbeat monitoring for disconnection detection

---

## 1. Prerequisites

Same as the simple tutorial plus:

```bash
pip install fcpp_bridge    # or PYTHONPATH=.../src
```

Verify:

```bash
python -c "import fcpp_bridge; print('ok')"
```

---

## 2. Algorithm — same as the simple tutorial

```python
# algorithm.py
import math
from dataclasses import dataclass
from fcpp_bridge.python_dsl import aggregate_function, Neighborhood

NUM_NODES = 20
SOURCE_ID = 3
DEST_ID   = 18
COMM      = 100.0
INF       = 999_999


@dataclass
class HopChannelState:
    is_source:          bool  = False
    is_dest:            bool  = False
    dist:               float = math.inf
    hops:               int   = INF
    received_source_id: int   = -1


@aggregate_function
class HopChannelAggregate:
    def initial_state(self) -> HopChannelState:
        return HopChannelState()

    def compute(
        self,
        self_state: HopChannelState,
        neighbors: Neighborhood[HopChannelState],
    ) -> HopChannelState:
        is_src  = self_state.is_source
        is_dest = self_state.is_dest

        dist = bis_distance(is_src, 1.0, COMM)              # noqa: F821
        hop_field = nbr(0 if is_src else INF)               # noqa: F821
        hops = 0 if is_src else min_hood(hop_field) + 1     # noqa: F821
        received_source_id = broadcast(is_src, SOURCE_ID)   # noqa: F821

        return HopChannelState(is_src, is_dest, dist, hops, received_source_id)
```

---

## 3. Compilation pipeline — customisation

### 3.1 Available `Compiler` parameters

```python
from fcpp_bridge.compiler import Compiler

compiler = Compiler(
    # ── Output paths ──────────────────────────────────────────────────────
    cache_dir       = Path("my_project/build"),          # compiled binaries
    cpp_dir         = Path("my_project/generated_cpp"),  # C++ source files
    # ── Toolchain ─────────────────────────────────────────────────────────
    gcc_path        = "/usr/bin/g++-12",    # specific g++ version
    std             = "c++17",              # C++ standard (≥ c++14 for FCPP)
    opt_level       = "3",                  # -O3 (production); use "g" for debug
    extra_includes  = [
        "/path/to/fcpp/src",                # FCPP headers (mandatory)
        "/path/to/my_runtime_headers",      # any additional headers
    ],
)
```

### 3.2 Per-compilation flag overrides

`Compiler.compile(cpp_file, output_binary, extra_flags=[...])` appends
`extra_flags` AFTER all base flags. GCC applies the last occurrence, so
you can override the constructor-level optimisation for a single file:

```python
result = compiler.compile(
    cpp_file      = Path("my_project/generated_cpp/hop_channel.cpp"),
    output_binary = Path("my_project/build/hop_channel_debug"),
    extra_flags   = ["-O0", "-g3", "-fsanitize=address"],
)
```

### 3.3 `get_or_compile` — caching shortcut

```python
binary_path = compiler.get_or_compile(cpp_code_str, "hop_channel")
# Internally:
#   1. SHA-256(cpp_code_str) → hash
#   2. If build/<program>_<hash> exists → return cached path
#   3. Otherwise write cpp_dir/<program>_<hash>.cpp, call compile(), store hash
```

Shell equivalent of what the compiler invokes:

```bash
g++-12 -std=c++17 -Wall -Wextra -O3 \
        -I /path/to/fcpp/src \
        -I /path/to/my_runtime_headers \
        my_project/generated_cpp/hop_channel_<hash>.cpp \
        -o my_project/build/hop_channel_<hash>
```

---

## 4. The `HopChannelSimulation` class

Everything—compilation, swarm lifecycle, listener management, node
management—lives in one reusable class.

```python
# simulation.py
import logging
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

from algorithm import HopChannelAggregate, HopChannelState, NUM_NODES, SOURCE_ID
from fcpp_bridge.transpiler import Transpiler
from fcpp_bridge.compiler import Compiler
from fcpp_bridge.ipc import SwarmProcess, SwarmSnapshot, ListenerProxy

log = logging.getLogger(__name__)


class HopChannelSimulation:
    """
    Production wrapper for the hop-channel aggregate program.

    Lifecycle
    ---------
    sim = HopChannelSimulation(...)
    sim.build()         # transpile + compile (idempotent: cached after first run)
    sim.start()         # spawn subprocess, wire listeners, begin rounds
    sim.pause()         # stop advancing rounds (subprocess stays alive)
    sim.resume()        # restart round loop
    sim.stop()          # gracefully terminate; flushes listeners
    """

    def __init__(
        self,
        num_nodes:      int   = NUM_NODES,
        # ── Compilation settings ──────────────────────────────────────────
        cpp_dir:        Path  = Path("generated_cpp"),
        build_dir:      Path  = Path("build"),
        fcpp_src:       str   = "/path/to/fcpp/src",
        std:            str   = "c++17",
        opt_level:      str   = "2",
        extra_includes: Optional[List[str]] = None,
        gcc_path:       str   = "g++",
        # ── Runtime settings ─────────────────────────────────────────────
        ipc_backend:    str   = "unix",
        round_interval: float = 0.1,        # seconds between rounds
        listener_mode:  str   = "sequential",  # "sequential" or "parallel"
        # ── Heartbeat settings ────────────────────────────────────────────
        heartbeat_interval: float = 5.0,
        heartbeat_timeout:  float = 30.0,
    ):
        self._num_nodes      = num_nodes
        self._round_interval = round_interval
        self._ipc_backend    = ipc_backend
        self._listener_mode  = listener_mode
        self._hb_interval    = heartbeat_interval
        self._hb_timeout     = heartbeat_timeout

        inc = list(extra_includes) if extra_includes else []
        inc = [fcpp_src] + inc          # FCPP src always first

        self._compiler = Compiler(
            cache_dir      = build_dir,
            cpp_dir        = cpp_dir,
            gcc_path       = gcc_path,
            std            = std,
            opt_level      = opt_level,
            extra_includes = inc,
        )

        self._binary_path: Optional[Path]    = None
        self._swarm:        Optional[SwarmProcess] = None
        self._running       = False
        self._paused        = False
        self._thread:       Optional[threading.Thread] = None
        self._lock          = threading.Lock()

    # ── Build ────────────────────────────────────────────────────────────────

    def build(self) -> Path:
        """Transpile the aggregate function to C++ and compile it.

        Idempotent: subsequent calls return the cached binary immediately
        if the source has not changed.
        """
        log.info("Transpiling HopChannelAggregate...")
        cpp_code = Transpiler(HopChannelAggregate).generate()
        log.info("Compiling (std=%s, -O%s)...",
                 self._compiler.std, self._compiler.opt_level)
        self._binary_path = self._compiler.get_or_compile(cpp_code, "hop_channel")
        log.info("Binary ready: %s", self._binary_path)
        return self._binary_path

    # ── Start ────────────────────────────────────────────────────────────────

    def start(self, binary_path: Optional[Path] = None) -> None:
        """Spawn the subprocess, wire listeners, and begin the round loop.

        If binary_path is None, build() is called automatically.
        """
        if binary_path is None:
            binary_path = self._binary_path or self.build()

        self._swarm = SwarmProcess(
            binary_path    = binary_path,
            num_nodes      = self._num_nodes,
            ipc_backend    = self._ipc_backend,
            listener_mode  = self._listener_mode,
        )

        self._wire_listeners()
        self._swarm.start()

        # Heartbeat monitor — passive liveness via last-seen timestamps
        self._swarm.start_heartbeat_monitor(
            interval = self._hb_interval,
            timeout  = self._hb_timeout,
            on_dead  = self._on_node_dead,
        )

        self._running = True
        self._paused  = False
        self._thread  = threading.Thread(
            target  = self._round_loop,
            daemon  = True,
            name    = "HopChannel-rounds",
        )
        self._thread.start()
        log.info("Simulation started (%d nodes)", self._num_nodes)

    def _wire_listeners(self) -> None:
        """Install the listener pipeline before the swarm starts."""
        # ── Global listener: LoggingListener + DebugPrint ────────────────
        # add_listener() automatically creates a ListenerProxy internally,
        # so both listeners are wrapped in the same proxy and share one
        # integer-ID namespace.
        self._log_lid   = self._swarm.add_listener(self._logging_listener)
        self._debug_lid = self._swarm.add_listener(self._debug_listener)

        # ── Per-node listener for node ID 5 ──────────────────────────────
        # This listener OVERRIDES the global proxy for node 5.
        # When node 5 appears in a snapshot, only this per-node proxy fires
        # (the global proxy is skipped for that node).
        self._swarm.add_node_listener(5, self._node5_listener)

        log.debug("Listeners wired (log_lid=%d, debug_lid=%d)",
                  self._log_lid, self._debug_lid)

    # ── Lifecycle: pause / resume / stop ─────────────────────────────────────

    def pause(self) -> None:
        """Stop advancing rounds.  The subprocess stays alive and connected."""
        with self._lock:
            self._paused = True
        log.info("Simulation paused")

    def resume(self) -> None:
        """Restart the round loop after a pause."""
        with self._lock:
            if not self._running:
                raise RuntimeError("Cannot resume: simulation is stopped")
            if not self._paused:
                return
            self._paused = False

        # Restart the thread if it exited while paused
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(
                target = self._round_loop, daemon=True, name="HopChannel-rounds"
            )
            self._thread.start()
        log.info("Simulation resumed")

    def stop(self) -> None:
        """Gracefully stop the simulation and close the subprocess."""
        with self._lock:
            self._running = False
            self._paused  = False

        if self._thread is not None:
            self._thread.join(timeout=self._round_interval * 5)
            self._thread = None

        if self._swarm is not None:
            self._swarm.stop_heartbeat_monitor()
            self._swarm.close()
            self._swarm = None

        log.info("Simulation stopped")

    def _round_loop(self) -> None:
        """Background thread: advance one round every `round_interval` seconds."""
        while self._running:
            with self._lock:
                if self._paused:
                    time.sleep(self._round_interval)
                    continue
            self._swarm.step()
            time.sleep(self._round_interval)

    # ── Dynamic listener management ──────────────────────────────────────────

    def add_listener(self, fn: Callable[[SwarmSnapshot], None]) -> int:
        """Add a global listener dynamically.  Returns its integer ID.

        Because `SwarmProcess.add_listener` always creates/uses a
        `ListenerProxy` internally, the first call creates the proxy; every
        subsequent call adds to the same proxy.  Listeners registered with
        different IDs are independent and can be removed individually.
        """
        if self._swarm is None:
            raise RuntimeError("Simulation not started")
        lid = self._swarm.add_listener(fn)
        log.debug("Added global listener id=%d", lid)
        return lid

    def remove_listener(self, listener_id: int) -> None:
        """Remove a global listener by the ID returned by add_listener."""
        if self._swarm is None:
            raise RuntimeError("Simulation not started")
        self._swarm.remove_listener(listener_id)
        log.debug("Removed global listener id=%d", listener_id)

    def add_node_listener(
        self,
        node_id: int,
        fn: Callable[[SwarmSnapshot], None],
    ) -> int:
        """Add a per-node listener override.  Returns its integer ID."""
        if self._swarm is None:
            raise RuntimeError("Simulation not started")
        return self._swarm.add_node_listener(node_id, fn)

    def remove_node_listener(self, node_id: int, listener_id: int) -> None:
        """Remove a per-node listener by node ID and listener ID."""
        if self._swarm is None:
            raise RuntimeError("Simulation not started")
        self._swarm.remove_node_listener(node_id, listener_id)

    # ── Node management ──────────────────────────────────────────────────────

    def add_nodes_random(
        self,
        count: int,
        *,
        area: Optional[tuple] = None,
        comm_range: Optional[float] = None,
        max_speed:  Optional[float] = None,
        propulsion: Optional[float] = None,
    ) -> List[int]:
        """Add nodes with random unique IDs.

        Returns the list of newly assigned IDs.

        area=(xmin, ymin, xmax, ymax)  — bounding box for placement
        comm_range, max_speed, propulsion  — physical parameters
        """
        if self._swarm is None:
            raise RuntimeError("Simulation not started")
        ids = self._swarm.add_nodes_random(
            count,
            area       = area,
            comm_range = comm_range,
            max_speed  = max_speed,
            propulsion = propulsion,
        )
        log.info("Added %d random nodes: %s", count, ids)
        return ids

    def add_node_explicit(
        self,
        node_id:   int,
        position:  tuple,
        *,
        comm_range: Optional[float] = None,
        max_speed:  Optional[float] = None,
        propulsion: Optional[float] = None,
    ) -> None:
        """Register a physical/production device by explicit ID and position.

        Use this when the device ID and location are known in advance
        (e.g., a real IoT sensor with a fixed MAC address).
        Raises ValueError if node_id is already in use.
        """
        if self._swarm is None:
            raise RuntimeError("Simulation not started")
        self._swarm.add_node_explicit(
            node_id, position,
            comm_range = comm_range,
            max_speed  = max_speed,
            propulsion = propulsion,
        )
        log.info("Added explicit node id=%d pos=%s", node_id, position)

    def add_nodes_sequential(
        self,
        count: int,
        start_positions: Optional[List[tuple]] = None,
    ) -> List[int]:
        """Add nodes with automatically assigned sequential IDs.

        Optional start_positions[i] sets the initial position of node i.
        Returns the list of new IDs.
        """
        if self._swarm is None:
            raise RuntimeError("Simulation not started")
        return self._swarm.add_nodes_sequential(count, start_positions)

    def remove_node(self, node_id: int) -> None:
        """Disconnect a node by ID.

        Removes the node from the swarm, clears its heartbeat timestamp,
        and discards any per-node listeners registered for it.
        """
        if self._swarm is None:
            raise RuntimeError("Simulation not started")
        self._swarm.remove_node(node_id)
        log.info("Removed node id=%d", node_id)

    # ── Monitoring ───────────────────────────────────────────────────────────

    def check_liveness(self, timeout: float = 30.0) -> Dict[int, bool]:
        """Return {node_id: True} for each node seen within `timeout` seconds.

        Uses *passive* heartbeating: a node is considered alive if a
        SwarmSnapshot containing its ID was received recently.  No explicit
        ping/pong is sent to the C++ side.

        For active heartbeats (ping/pong) the C++ runtime would need to
        expose a `/ping` endpoint; that is left as future work.
        """
        if self._swarm is None:
            return {}
        return self._swarm.check_liveness(timeout)

    def get_state(self) -> Optional[object]:
        """Pull the current swarm state (also updates heartbeat timestamps)."""
        if self._swarm is None:
            return None
        return self._swarm.get_state()

    # ── Listener implementations ─────────────────────────────────────────────

    def _logging_listener(self, snap: SwarmSnapshot) -> None:
        """Delegate to the Python logging module."""
        dest_nodes = [
            n for n in snap.nodes
            if isinstance(n.state_data, dict) and n.state_data.get("is_dest")
        ]
        for n in dest_nodes:
            d = n.state_data
            log.info(
                "Round %d | dest=%d | dist=%.2f hops=%d source_id=%d",
                snap.round_number, n.node_id,
                d.get("dist", float("inf")),
                d.get("hops", -1),
                d.get("received_source_id", -1),
            )

    def _debug_listener(self, snap: SwarmSnapshot) -> None:
        """Placeholder: print each update — replace with production logic."""
        print(f"[DEBUG] round={snap.round_number} nodes={len(snap.nodes)}")

    def _node5_listener(self, snap: SwarmSnapshot) -> None:
        """Per-node override for node 5.

        This fires instead of the global proxy for any snapshot that contains
        node 5.  Both listeners can be active independently; the per-node
        listener does NOT suppress the global one for other nodes in the same
        snapshot.
        """
        print("custom listener for ID 5")
        # Delegate to the logging listener for the structured log line
        self._logging_listener(snap)

    def _on_node_dead(self, node_id: int) -> None:
        """Called by the heartbeat monitor when a node stops responding."""
        log.warning(
            "Node %d has not sent a state update within %.0f seconds — "
            "possible disconnection",
            node_id, self._hb_timeout,
        )
```

---

## 5. Update delivery and consumption

### How updates reach Python

```
C++ binary (subprocess)
    ↓  IPC command {"cmd": "step"}       ← swarm.step()
    ↓  JSON response (SwarmSnapshot)
    ↓  backend.subscribe_state_updates(callback)   ← push path
SwarmProcess._dispatch_update(snapshot)
    ↓
    ┌─ node.node_id in _node_listeners?
    │   YES → per-node ListenerProxy(snapshot)
    │           ↓ all per-node listeners called
    └─ NO  → global ListenerProxy(snapshot)
                ↓ all global listeners called
                   (log_listener, debug_listener, …)
```

`get_state()` also updates heartbeat timestamps (pull path).

### Dispatch mode

Set `listener_mode="parallel"` in the constructor to dispatch all global
listeners concurrently via a thread pool:

```python
sim = HopChannelSimulation(listener_mode="parallel")
```

This is useful when a listener does I/O (writes to a DB, sends to a message
queue) and you do not want one slow listener to block the others.

### Adding a listener after start

```python
sim.start()

# Add a listener that saves snapshots to a database
def db_writer(snap):
    db.insert_many([{"node": n.node_id, "round": snap.round_number,
                     "dist": n.state_data.get("dist")} for n in snap.nodes])

db_lid = sim.add_listener(db_writer)

# Later — remove it without stopping the simulation
sim.remove_listener(db_lid)
```

---

## 6. Network lifecycle in detail

```
sim.build()   ← transpile + compile (once; cached afterward)
     ↓
sim.start()   ← subprocess spawned, listeners wired, round loop starts
     │
     ├──  sim.pause()   ← loop exits; subprocess stays alive
     │         │
     └──  sim.resume()  ← loop restarts; no new subprocess
     │
sim.stop()    ← loop exits, heartbeat thread stopped, subprocess terminated
```

**Suspend / resume** is purely a Python-side concept: the C++ binary does not
receive a "pause" command; it simply stops receiving `step` commands. If the
binary has its own internal timer, use `extra_flags=["-DFCPP_NO_TIMER"]` (or an
equivalent compile flag) to disable it and let Python control pacing entirely.

**Graceful stop** sequence (`sim.stop()`):

1. Set `_running = False` → round loop exits on next iteration.
2. Join the round thread (up to 5 \* round_interval seconds).
3. Call `swarm.stop_heartbeat_monitor()` → join the heartbeat daemon thread.
4. Call `swarm.close()` → send SIGTERM to the subprocess; SIGKILL after 5 s.

---

## 7. Node management in detail

### Add nodes at runtime

```python
# Strategy 1 — random IDs (good for dynamic simulations)
new_ids = sim.add_nodes_random(
    5,
    area       = (0.0, 0.0, 500.0, 500.0),  # bounding box
    comm_range = 100.0,
    max_speed  = 15.0,
)
print("New random nodes:", new_ids)   # e.g. [872341, 5123091, ...]

# Strategy 2 — explicit ID + position (physical/production devices)
sim.add_node_explicit(
    node_id   = 42,          # fixed hardware ID
    position  = (123.4, 56.7),
    comm_range = 80.0,
)

# Strategy 3 — sequential IDs (simplest; IDs are unique by construction)
ids = sim.add_nodes_sequential(3, start_positions=[(10,10),(20,20),(30,30)])
print("Sequential IDs:", ids)   # e.g. [20, 21, 22]
```

### Remove a node

```python
sim.remove_node(42)
# → sends {"cmd": "remove_node", "id": 42} to the C++ binary
# → clears heartbeat timestamp and per-node listener for node 42
```

### Monitor for disconnection

```python
# Manual check
liveness = sim.check_liveness(timeout=30.0)
dead = [nid for nid, alive in liveness.items() if not alive]
print("Possibly disconnected:", dead)

# Automatic via the heartbeat background thread (set in __init__):
# heartbeat_interval=5.0  → check every 5 seconds
# heartbeat_timeout=30.0  → node declared dead after 30 s without a state update
# on_dead → _on_node_dead() logs a warning; replace with reconnect logic
```

**Passive heartbeat mechanism**:

```
get_state()  →  SwarmProcess._update_heartbeats(snapshot)
                  updates _heartbeat_timestamps[node_id] = time.time()

heartbeat background thread (every interval seconds):
  for each nid in _heartbeat_timestamps:
      if time.time() - _heartbeat_timestamps[nid] > timeout:
          on_dead(nid)        ← _on_node_dead() in our class
```

---

## 8. Complete `production_run.py`

```python
# production_run.py
import logging
import time
from pathlib import Path

from simulation import HopChannelSimulation

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
log = logging.getLogger("production_run")

FCPP_SRC = "/path/to/fcpp/src"    # ← set this


def main():
    sim = HopChannelSimulation(
        num_nodes       = 20,
        cpp_dir         = Path("generated_cpp"),
        build_dir       = Path("build"),
        fcpp_src        = FCPP_SRC,
        std             = "c++17",
        opt_level       = "3",               # production: maximum optimisation
        gcc_path        = "g++-12",
        ipc_backend     = "unix",
        round_interval  = 0.05,              # 20 rounds / second
        listener_mode   = "sequential",
        heartbeat_interval = 5.0,
        heartbeat_timeout  = 30.0,
    )

    # ── Build (transpile + compile) ──────────────────────────────────────
    sim.build()

    # ── Start simulation ─────────────────────────────────────────────────
    sim.start()

    # ── Dynamically add a metrics listener after start ───────────────────
    metrics = {"rounds": 0, "max_hops": 0}

    def metrics_listener(snap):
        metrics["rounds"] += 1
        for n in snap.nodes:
            d = n.state_data
            if isinstance(d, dict):
                metrics["max_hops"] = max(metrics["max_hops"], d.get("hops", 0))

    m_lid = sim.add_listener(metrics_listener)

    # ── Run for 10 seconds ───────────────────────────────────────────────
    time.sleep(5.0)

    log.info("Pausing simulation for 2 seconds...")
    sim.pause()
    time.sleep(2.0)
    sim.resume()
    log.info("Resumed")

    time.sleep(5.0)

    # ── Add a physical device ────────────────────────────────────────────
    sim.add_node_explicit(node_id=999, position=(250.0, 250.0), comm_range=150.0)

    time.sleep(2.0)

    # ── Remove the metrics listener ──────────────────────────────────────
    sim.remove_listener(m_lid)

    # ── Check liveness ───────────────────────────────────────────────────
    liveness = sim.check_liveness(timeout=30.0)
    dead = [n for n, alive in liveness.items() if not alive]
    if dead:
        log.warning("Nodes not responding: %s", dead)
        for nid in dead:
            sim.remove_node(nid)

    # ── Stop ─────────────────────────────────────────────────────────────
    sim.stop()

    log.info("Done.  rounds=%d  max_hops=%d",
             metrics["rounds"], metrics["max_hops"])


if __name__ == "__main__":
    main()
```

---

## 9. Shell commands

```bash
# 0. Set up Python path
export PYTHONPATH=/path/to/c_cpp_study/src

# 1. Validate the aggregate function (no C++ needed)
python -c "
from algorithm import HopChannelAggregate
from fcpp_bridge.python_dsl.validators import AggregateValidator
w = AggregateValidator.validate(HopChannelAggregate)
print('Validation OK, warnings:', w)
"

# 2. Transpile only (inspect the generated C++)
python -c "
from algorithm import HopChannelAggregate
from fcpp_bridge.transpiler import Transpiler
print(Transpiler(HopChannelAggregate).generate())
" > generated_cpp/hop_channel_preview.cpp

# 3. Run the full production simulation
python production_run.py

# 4. Debug build (no optimisation, AddressSanitizer)
python -c "
from algorithm import HopChannelAggregate
from fcpp_bridge.transpiler import Transpiler
from fcpp_bridge.compiler import Compiler
from pathlib import Path
cpp = Transpiler(HopChannelAggregate).generate()
c = Compiler(
    cache_dir=Path('build_debug'), cpp_dir=Path('generated_cpp'),
    std='c++17', opt_level='0',
    extra_includes=['/path/to/fcpp/src']
)
import tempfile, pathlib
f = Path('generated_cpp/debug.cpp')
f.write_text(cpp)
result = c.compile(f, Path('build_debug/hop_channel'), extra_flags=['-g3','-fsanitize=address'])
print('Success:', result.success)
"
```

### Running individual pipeline stages

`examples/end_to_end.py` lets you run any subset of the four pipeline stages without
re-running earlier ones. Each stage saves an artifact to disk so the next stage can
load it directly:

```bash
# Validate + transpile only (no compiler required)
python src/fcpp_bridge/examples/end_to_end.py --steps validate transpile

# Resume from compile (reads consensus_latest.cpp written by transpile)
python src/fcpp_bridge/examples/end_to_end.py --from compile

# Jump straight to the simulation step
python src/fcpp_bridge/examples/end_to_end.py --steps run --nodes 20 --rounds 10
```

See `TUTORIAL_simple.md §Running individual steps` for the full flag reference and
the artifact path table.

---

## 10. Reference — `ListenerProxy` used internally

`SwarmProcess.add_listener()` always stores listeners in a `ListenerProxy`. You
can also build one explicitly for other purposes:

```python
from fcpp_bridge.ipc import ListenerProxy

# Sequential (default): listeners called in registration order
proxy = ListenerProxy(mode="sequential")

# Parallel: listeners called concurrently in a thread pool
proxy = ListenerProxy(mode="parallel")

# Add / remove
lid_a = proxy.add_listener(lambda snap: print("A", snap.round_number))
lid_b = proxy.add_listener(lambda snap: print("B", snap.round_number))
proxy.remove_listener(lid_a)

# Dispatch manually
proxy(some_snapshot)

# Clean up thread pool (parallel mode only)
proxy.close()
```

---

## 11. Feature reference table

| Feature                | API                                                         | Notes                                          |
| ---------------------- | ----------------------------------------------------------- | ---------------------------------------------- |
| Transpile              | `Transpiler(cls).generate()`                                | Returns C++ string                             |
| Write C++              | `Path.write_text(cpp)`                                      | Manual; `get_or_compile` does it automatically |
| Compile (custom)       | `Compiler(std, opt_level, extra_includes, ...)`             | See §3                                         |
| Compile per-file flags | `compiler.compile(f, out, extra_flags=[...])`               | Appended last → override                       |
| Cache hit              | `compiler.get_or_compile(cpp, name)`                        | SHA-256; skips if unchanged                    |
| Spawn subprocess       | `SwarmProcess(binary, num_nodes).start()`                   | Sends `--num-nodes=N` to binary                |
| Step                   | `swarm.step()`                                              | One simulation round                           |
| Pull state             | `swarm.get_state()` → `SwarmSnapshot`                       | Also updates heartbeat timestamps              |
| Push state             | `IpcBackend.subscribe_state_updates(cb)`                    | Wired to `_dispatch_update` in `start()`       |
| Global listener        | `swarm.add_listener(fn)` → int                              | Auto-creates `ListenerProxy`                   |
| Remove listener        | `swarm.remove_listener(id)`                                 |                                                |
| Per-node override      | `swarm.add_node_listener(nid, fn)` → int                    | Fires instead of global for that node          |
| Proxy mode             | `SwarmProcess(listener_mode="parallel")`                    | Sequential (default) or parallel               |
| Add random nodes       | `swarm.add_nodes_random(n, *, area, ...)` → List[int]       |                                                |
| Add explicit node      | `swarm.add_node_explicit(id, pos, ...)`                     | For physical devices                           |
| Add sequential         | `swarm.add_nodes_sequential(n, positions)`                  |                                                |
| Remove node            | `swarm.remove_node(id)`                                     | Clears heartbeat + per-node listener           |
| Liveness check         | `swarm.check_liveness(timeout)` → Dict[int,bool]            | Passive heartbeat                              |
| Heartbeat thread       | `swarm.start_heartbeat_monitor(interval, timeout, on_dead)` | Background                                     |
| Stop heartbeat         | `swarm.stop_heartbeat_monitor()`                            |                                                |
| Pause simulation       | stop calling `step()`                                       | Subprocess stays alive                         |
| Stop entirely          | `swarm.close()`                                             | SIGTERM → SIGKILL after 5 s                    |

---

## 11. Further examples

All examples in `examples/` follow the same pattern: an `@aggregate_function` class
(transpilable) plus a pure-Python `_demo_simulate()` that needs no C++ toolchain.

| File | Highlights |
| ---- | ---------- |
| `message_dispatch.py` | Full `spawn` + `sp_collection` spanning-tree routing (port of `message_dispatch.hpp`) |
| `spreading_collection.py` | `abf_distance`, `mp_collection`, `broadcast` (port of `spreading_collection.hpp`) |
| `worker_role_assignment.py` | **`match/case` → C++ `switch`** + `spawn` + `old` + `self_uid()` + `RoleCommunicationType`; 8 `WorkerRole` values, 24-node disaster swarm |

`worker_role_assignment.py` is the canonical example of the v1.4–v1.7 grammar features:
- **CALL-counter alignment**: all 7 CALL-based primitives are called before the `match/case`;
  each case branch contains only local expressions (no primitives).
- **Integer-literal case patterns**: bare names like `case RECEIVER:` are capture patterns
  in Python 3.10+ (always match); use `case 1:` with a `# RECEIVER` comment instead.
- **`self_uid()`** (v1.6): transpiles to `node.uid` in C++ without incrementing the CALL
  counter.  Safe anywhere — inside or outside `match/case` branches.
- **Role-specific tasks in step 7**: each case includes a task description and a local
  placeholder variable; implementations marked `# [Placeholder]` are exercise stubs.
- **`RoleCommunicationType`** (v1.7): ENDPOINT / RECEIVER / REPEATER enum associated with
  each `WorkerRole` via `ROLE_COMM_TYPE` dict.  Endpoint roles (2, 3, 5, 6, 7) inject
  sensor-reading messages; repeater roles (0, 4) relay without originating data.

Design notes and 7 evolution paths: `development_history/WORKER_ROLE_ASSIGNMENT.md`.
