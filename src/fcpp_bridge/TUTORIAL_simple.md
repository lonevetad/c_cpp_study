# fcpp_bridge — Simple Tutorial

**Goal**: Build a 20-node swarm where node 3 is the *source* and node 18 is the
*destination*.  The aggregate program computes:

1. The BIS-distance from source to every node (including the destination).
2. The hop count from source to every node via `nbr` + `min_hood`.
3. The source ID delivered to every node (including the destination) via `broadcast`.

The tutorial walks through every stage of the pipeline: Python DSL → C++ → compile
→ run → consume updates via listeners.

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.10+ | `python --version` |
| `fcpp_bridge` package on `PYTHONPATH` | `export PYTHONPATH=/path/to/c_cpp_study/src` |
| FCPP C++ framework headers | Clone from `github.com/fcpp/fcpp`; set `FCPP_SRC` env var |
| `g++` ≥ 9 with C++14 support | `g++ --version` |
| (Optional) `lld` linker | Faster linking on Linux |

> **No C++ toolchain?**  Skip Steps 3–5 and run the pure-Python simulation at
> the end of this file instead.  It is algorithmically identical.

---

## Files you will write

```
my_project/
├── hop_channel.py     ← aggregate function + transpile + compile + run
└── run.py             ← entry-point that starts the full pipeline
```

---

## Step 1 — Define the aggregate function

Create `hop_channel.py`:

```python
# hop_channel.py
"""
Hop-channel example.

Topology: 20 nodes randomly placed in a 500 × 500 area.
Source:   node ID 3  (is_source = True)
Destination: node ID 18 (is_dest = True)

Algorithm per round (same order as C++ MAIN):
  1. bis_distance  — distance from source (BIS spanning-tree metric)
  2. nbr + min_hood — hop count from source
  3. broadcast     — source ID propagated from source to all nodes
"""

import math
from dataclasses import dataclass

from fcpp_bridge.python_dsl import aggregate_function, Neighborhood

# ── Constants ────────────────────────────────────────────────────────────────
NUM_NODES  = 20
SOURCE_ID  = 3
DEST_ID    = 18
COMM       = 100.0      # communication radius (same units as positions)
INF        = 999_999    # sentinel for "no path yet"


# ── Per-node state ────────────────────────────────────────────────────────────
@dataclass
class HopChannelState:
    """State carried by each node across rounds."""
    is_source:          bool  = False
    is_dest:            bool  = False
    dist:               float = math.inf   # BIS distance from source
    hops:               int   = INF        # hop count from source
    received_source_id: int   = -1         # source ID delivered via broadcast


# ── Aggregate function ────────────────────────────────────────────────────────
@aggregate_function
class HopChannelAggregate:
    """
    Aggregate program: BIS distance + hop count + broadcast from source.

    Primitive → C++ mapping:
        bis_distance(...)  → bis_distance(CALL, ...)   [spreading.hpp]
        nbr(...)           → nbr(CALL, ...)             [basics.hpp]
        min_hood(...)      → min_hood(CALL, ...)        [utils.hpp]
        broadcast(...)     → broadcast(CALL, ...)       [spreading.hpp]
    """

    def initial_state(self) -> HopChannelState:
        return HopChannelState()

    def compute(
        self,
        self_state: HopChannelState,
        neighbors: Neighborhood[HopChannelState],
    ) -> HopChannelState:
        is_src  = self_state.is_source
        is_dest = self_state.is_dest

        # ── 1. BIS distance from source ───────────────────────────────────
        # bis_distance(source_flag, metric, comm_range)
        # metric=1.0 → each hop contributes 1 unit (same as hop count in
        # uniform topologies; replace with a real distance metric for
        # geographic deployments).
        dist = bis_distance(is_src, 1.0, COMM)  # noqa: F821

        # ── 2. Hop count from source ──────────────────────────────────────
        # nbr(initial_value) shares the current hop count with neighbours.
        # min_hood picks the lowest count in the neighbourhood.
        # Source starts at 0; every other node = min(neighbours) + 1.
        hop_field = nbr(0 if is_src else INF)          # noqa: F821
        hops      = 0 if is_src else min_hood(hop_field) + 1  # noqa: F821

        # ── 3. Broadcast source ID toward destination ─────────────────────
        # broadcast(source_flag, value) propagates `value` from every node
        # where source_flag=True toward all other nodes along the spanning
        # tree built by bis_distance.
        # Result: every node (including the destination) receives SOURCE_ID.
        received_source_id = broadcast(is_src, SOURCE_ID)  # noqa: F821

        return HopChannelState(
            is_source=is_src,
            is_dest=is_dest,
            dist=dist,
            hops=hops,
            received_source_id=received_source_id,
        )
```

**Why `# noqa: F821`?**
The FCPP primitives (`bis_distance`, `nbr`, `min_hood`, `broadcast`) are *unbound
names* in Python—they are not imported.  The transpiler recognises them by name
from the `_FCPP_PRIMITIVES` dictionary and injects the `CALL` macro automatically.
Linters flag them as undefined; `# noqa: F821` silences that warning.

---

## Step 2 — Transpile to C++

The transpiler converts the `compute()` method into a C++ function body using
`PythonAstVisitor`:

```python
from fcpp_bridge.transpiler import Transpiler

t   = Transpiler(HopChannelAggregate)
cpp = t.generate()          # returns a complete C++ source string
print(cpp[:800])            # preview the first 800 characters
```

Running this outputs something like:

```cpp
// Auto-generated by fcpp_bridge Transpiler
#include "fcpp/lib/spreading.hpp"   // bis_distance, broadcast
#include "fcpp/lib/utils.hpp"       // min_hood
#include "fcpp/lib/basics.hpp"      // nbr
#include "ipc_server.hpp"           // runtime IPC header

FUN void hop_channel_compute(ARGS, HopChannelState& self_state) { CODE
    bool is_src  = self_state.is_source;
    bool is_dest = self_state.is_dest;

    auto dist = bis_distance(CALL, is_src, 1.0, COMM);

    auto hop_field = nbr(CALL, is_src ? 0 : INF);
    auto hops      = is_src ? 0 : min_hood(CALL, hop_field) + 1;

    auto received_source_id = broadcast(CALL, is_src, SOURCE_ID);

    self_state = HopChannelState{is_src, is_dest, dist, hops, received_source_id};
}
```

---

## Step 3 — Write C++ to file ("serialisation")

```python
from pathlib import Path

cpp_dir = Path("generated")
cpp_dir.mkdir(exist_ok=True)

cpp_file = cpp_dir / "hop_channel.cpp"
cpp_file.write_text(cpp)
print(f"C++ source written to: {cpp_file}")
```

The `Compiler.get_or_compile()` convenience helper does this automatically (and
adds SHA-256 caching so unchanged programs are never recompiled).

---

## Step 4 — Compile

```python
from fcpp_bridge.compiler import Compiler, CompilationError

compiler = Compiler(
    cache_dir=Path("build"),          # where compiled binaries live
    cpp_dir=Path("generated"),        # where C++ sources are written
    std="c++14",                      # C++ standard (fcpp requires ≥ C++14)
    opt_level="2",                    # -O2 optimisation
    extra_includes=[                  # path to FCPP headers
        "/path/to/fcpp/src",
    ],
)

try:
    binary = compiler.get_or_compile(cpp, "hop_channel")
    print(f"Compiled binary: {binary}")
except CompilationError as exc:
    print(f"Compilation failed: {exc}")
```

Equivalent **shell command** (what `Compiler.compile()` runs internally):

```bash
g++ -std=c++14 -Wall -Wextra -O2 \
    -I /path/to/fcpp/src \
    -I generated/runtime \
    generated/hop_channel.cpp \
    -o build/hop_channel
```

> **Cache behaviour**: `get_or_compile()` hashes the C++ source (SHA-256).  If the
> hash matches a cached binary, compilation is skipped.  Delete `build/` to force
> a fresh build.

---

## Step 5 — Execute the compiled C++ binary

`SwarmProcess` spawns the binary as a subprocess and connects via a Unix-domain
socket (default) or HTTP/gRPC backend:

```python
from fcpp_bridge.ipc import SwarmProcess

with SwarmProcess(binary, num_nodes=NUM_NODES) as swarm:
    # The binary is now running and listening for IPC commands.
    print("Swarm started")
    # ... (Step 6 sets up listeners before driving rounds)
```

The binary is launched as:

```bash
./build/hop_channel --num-nodes=20
```

It reads commands (e.g., `{"cmd": "step"}`) over the socket and responds with
`SwarmSnapshot` JSON payloads.

---

## Step 6 — Set up update listeners

Listeners are callables `(SwarmSnapshot) → None` registered on the swarm.
Each call to `swarm.step()` triggers one simulation round; the backend then
pushes (or you pull via `swarm.get_state()`) a `SwarmSnapshot`.

```python
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("hop_channel")


def on_update(snap):
    """Called after every simulation round."""
    for node in snap.nodes:
        data = node.state_data          # dict from JSON or native struct
        if data.get("is_dest"):
            log.info(
                "Round %d | destination node %d | "
                "dist=%.2f hops=%d source_id=%d",
                snap.round_number,
                node.node_id,
                data.get("dist", float("inf")),
                data.get("hops", -1),
                data.get("received_source_id", -1),
            )
```

Register and start:

```python
with SwarmProcess(binary, num_nodes=NUM_NODES) as swarm:
    swarm.add_listener(on_update)        # register global listener

    for round_num in range(10):
        swarm.step()                     # advance one round
        snap = swarm.get_state()         # pull current state
        on_update(snap)                  # or let the push subscription call it
```

---

## Step 7 — Consume updates

After 3–5 rounds the spanning tree converges.  The `on_update` callback logs
something like:

```
INFO  Round 3 | destination node 18 | dist=4.00 hops=4 source_id=3
INFO  Round 4 | destination node 18 | dist=4.00 hops=4 source_id=3
```

This tells you: node 18 is **4 hops away** from source node 3, the source ID
(`3`) was received via `broadcast`, and the BIS distance is **4.0** (4 hops ×
1.0 metric = 4.0 with a unitary metric).

---

## Complete `run.py`

```python
# run.py — full pipeline: transpile → compile → run → listen
import math
import logging
from pathlib import Path

from hop_channel import HopChannelAggregate, NUM_NODES, DEST_ID
from fcpp_bridge.transpiler import Transpiler
from fcpp_bridge.compiler import Compiler, CompilationError
from fcpp_bridge.ipc import SwarmProcess

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("run")

FCPP_SRC = "/path/to/fcpp/src"     # ← set this to your FCPP clone


def build() -> Path:
    """Transpile and compile the aggregate function."""
    cpp = Transpiler(HopChannelAggregate).generate()

    compiler = Compiler(
        cache_dir=Path("build"),
        cpp_dir=Path("generated"),
        std="c++14",
        opt_level="2",
        extra_includes=[FCPP_SRC],
    )
    return compiler.get_or_compile(cpp, "hop_channel")


def on_update(snap):
    for node in snap.nodes:
        d = node.state_data
        if d and d.get("is_dest"):
            log.info(
                "Round %d | dest=%d dist=%.2f hops=%d source=%d",
                snap.round_number, node.node_id,
                d.get("dist", math.inf), d.get("hops", -1),
                d.get("received_source_id", -1),
            )


def main():
    binary = build()
    with SwarmProcess(binary, num_nodes=NUM_NODES) as swarm:
        swarm.add_listener(on_update)
        for _ in range(20):
            swarm.step()


if __name__ == "__main__":
    main()
```

---

## Shell commands — everything at a glance

```bash
# 1. Set the Python path
export PYTHONPATH=/path/to/c_cpp_study/src

# 2. (Optional) verify DSL validation passes
python -c "
from hop_channel import HopChannelAggregate
from fcpp_bridge.python_dsl.validators import AggregateValidator
warnings = AggregateValidator.validate(HopChannelAggregate)
print('Validation OK, warnings:', warnings)
"

# 3. Run the full pipeline
python run.py

# 4. Run tests (if you add tests)
PYTHONPATH=src pytest my_project/tests/ -v
```

---

## Pure-Python fallback simulation

No C++ toolchain?  The pure-Python simulation below runs the same algorithm
without compiling anything.  It mirrors exactly how the FCPP examples in
`src/fcpp_bridge/examples/` work.

```python
# pure_sim.py — no g++ required
import math
import random
from hop_channel import (
    HopChannelState, HopChannelAggregate,
    NUM_NODES, SOURCE_ID, DEST_ID, COMM, INF,
)

random.seed(42)
SIDE = 500.0
NUM_ROUNDS = 15

positions = {i: (random.uniform(0, SIDE), random.uniform(0, SIDE)) for i in range(NUM_NODES)}
states    = {i: HopChannelState(is_source=(i == SOURCE_ID), is_dest=(i == DEST_ID))
             for i in range(NUM_NODES)}


def neighbours(nid):
    x, y = positions[nid]
    return [j for j in range(NUM_NODES)
            if j != nid and math.dist((x, y), positions[j]) <= COMM]


def step(states):
    """One simulation round — faithful pure-Python implementation."""
    new = {}
    for nid in range(NUM_NODES):
        s     = states[nid]
        nbrs  = [states[n] for n in neighbours(nid)]
        is_src  = s.is_source

        # BIS distance: source=0; others = min(neighbour.dist) + metric
        if is_src:
            dist = 0.0
        elif nbrs:
            dist = min((ns.dist for ns in nbrs if math.isfinite(ns.dist)), default=math.inf) + 1.0
        else:
            dist = math.inf

        # Hop count: source=0; others = min(neighbour.hops) + 1
        if is_src:
            hops = 0
        elif nbrs:
            min_nbr = min((ns.hops for ns in nbrs if ns.hops < INF), default=INF)
            hops = min_nbr + 1 if min_nbr < INF else INF
        else:
            hops = INF

        # Broadcast: propagate source ID toward all nodes
        if is_src:
            received_source_id = SOURCE_ID
        elif nbrs:
            candidates = [ns.received_source_id for ns in nbrs if ns.received_source_id != -1]
            received_source_id = candidates[0] if candidates else -1
        else:
            received_source_id = -1

        new[nid] = HopChannelState(is_src, s.is_dest, dist, hops, received_source_id)
    return new


for rnd in range(NUM_ROUNDS):
    states = step(states)
    dest   = states[DEST_ID]
    print(
        f"Round {rnd:2d} | dest={DEST_ID} "
        f"dist={dest.dist:.1f} hops={dest.hops} source_id={dest.received_source_id}"
    )
```

Run it:

```bash
python pure_sim.py
```

Expected output (topology is random; values stabilise after 3–5 rounds):

```
Round  0 | dest=18 dist=inf hops=999999 source_id=-1
Round  1 | dest=18 dist=inf hops=999999 source_id=-1
Round  2 | dest=18 dist=2.0  hops=2      source_id=3
Round  3 | dest=18 dist=2.0  hops=2      source_id=3
...
```

---

## Pipeline summary

```
hop_channel.py          (you write)
    ↓ Transpiler.generate()
generated/hop_channel.cpp
    ↓ Compiler.get_or_compile()
build/hop_channel           (executable)
    ↓ SwarmProcess.start()
subprocess (IPC via Unix socket)
    ↓ swarm.add_listener(on_update)
on_update(SwarmSnapshot)    (your callback — called each round)
    ↓
logging / metrics / UI
```
