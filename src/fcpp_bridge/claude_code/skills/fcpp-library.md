# FCPP Library Reference

You are working with the **FCPP** C++14 aggregate programming library, used in this project
via the `fcpp_bridge` Python-to-C++ transpiler.

FCPP implements **Field Calculus** — a theoretical model for aggregate programming where
groups of networked devices execute the same algorithm locally; each device (node) shares
values with 1-hop neighbours each round, and distributed computations emerge from these
interactions.

---

## Architecture Overview

```
Python DSL (fcpp_bridge)
    @aggregate_function class → compute(self_state, neighbors) → new_state
        ↓ AggregateValidator.validate()
        ↓ Transpiler.generate()
C++ source (auto-generated)
        ↓ Compiler (g++ -std=c++14, CMake cache)
C++ binary (FCPP runtime)
        ↓ SwarmProcess (IPC: JSON over stdin/stdout)
Python simulation loop
```

---

## C++ File Structure

```cpp
#include <fcpp/fcpp.hpp>              // main FCPP umbrella header
#include <lib/coordination/basics.hpp>    // nbr, old, spawn, count_hood
#include <lib/coordination/utils.hpp>     // min_hood, max_hood, fold_hood
#include <lib/coordination/spreading.hpp> // bis_distance, abf_distance, broadcast
#include <lib/coordination/collection.hpp>// sp_collection, mp_collection, wmp_collection
#include <lib/coordination/geometry.hpp>  // rectangle_walk, follow_target

// State struct (auto-generated from Python @dataclass)
struct MyState {
    bool   is_source;
    double dist;
    int    count;
};

// Aggregate main — called every round at every node
FUN void MAIN(ARGS) { CODE
    // ... primitive calls with CALL ...
}
```

---

## The CALL / ARGS / CODE Pattern

**Critical rule**: every FCPP aggregate primitive increments an internal CALL counter.
All nodes must call primitives in the **same order** every round, or the C++ execution
diverges. This is why the Python transpiler places all aggregate primitive calls
unconditionally before any branching.

```cpp
// FUN: marks an aggregate function
// ARGS: expands to (node_t& node, trace_t trace, ...)
// CODE: expands to  trace_t call_point = 0;
// CALL: expands to  node, trace_t{trace, ++call_point}
// CALLn: expands to node, trace_t{trace, n}  (explicit counter)

FUN double compute_dist(ARGS, bool is_source) { CODE
    return bis_distance(CALL, is_source, 1.0, 100.0);
}

FUN void MAIN(ARGS) { CODE
    // Step 1: always called
    double d = bis_distance(CALL, self_uid() == 0, 1.0, 100.0);
    // Step 2: always called
    auto nbr_d = nbr(CALL, d);
    // Step 3: always called (result ignored if not needed)
    auto min_d = min_hood(CALL, nbr_d);
    // THEN: branching / state assembly (no primitives inside if/switch)
    bool is_near = (d < 50.0);
}
```

---

## All FCPP Aggregate Primitives

### `nbr` — share value with 1-hop neighbours
```cpp
// C++: nbr(CALL, value)  → field<T>  (map of neighbour values)
// Python DSL: nbr_field = nbr(value)
auto nbr_dist = nbr(CALL, my_dist);   // each neighbour's distance
```

### `old` — temporal accumulation (previous round's value)
```cpp
// C++: old(CALL, init, update_fn)  → T
// Python DSL: result = old(init, lambda prev: new_value)
auto age = old(CALL, 0, [](int prev){ return prev + 1; });

// One-argument form: old(CALL, value) → value from previous round
auto prev_dist = old(CALL, my_dist);
```

### `count_hood` — count 1-hop neighbours
```cpp
// C++: count_hood(CALL)  → int
// Python DSL: n = count_hood()
int neighbor_count = count_hood(CALL);
```

### `min_hood` / `max_hood` — extremum over neighbourhood
```cpp
// C++: min_hood(CALL, field)  → T
// Python DSL: m = min_hood(field)
auto nearest = min_hood(CALL, nbr(CALL, my_dist));
auto farthest = max_hood(CALL, nbr(CALL, my_dist));

// Tie-breaking with tuple (lexicographic comparison):
// Python: min_hood((nbr_dist, self_uid()))
auto parent = min_hood(CALL, make_tuple(nbr(CALL, dist), node.uid));
```

### `fold_hood` — custom fold over neighbourhood
```cpp
// C++: fold_hood(CALL, fn, field, identity)  → T
// Python DSL: result = fold_hood(lambda a,b: ..., field, identity)
auto uid_set = fold_hood(CALL,
    [](auto a, auto b){ return a | b; },   // C++14 generic lambda
    nbr(CALL, std::set<device_t>{node.uid}),
    std::set<device_t>{});
```

### `spawn` — distributed sub-programs (key/value processes)
```cpp
// C++: spawn(CALL, process_fn, new_key_opt)  → map<Key, Value>
// Python DSL:
//   active = spawn(lambda key: (payload, status), new_key_or_None)
// status: STATUS_BORDER=0, STATUS_INTERNAL=1, STATUS_TERMINATED=2

// The process_fn is a C++14 generic lambda:
auto active = spawn(CALL,
    [&](auto key) {    // key is the process identifier
        auto value = compute_payload(key);
        auto status = determine_status(key);  // 0/1/2
        return std::make_pair(value, status);
    },
    new_key    // std::optional<Key> (nullopt = don't start new process)
);
// Returns std::map<Key, Value> for all INTERNAL/TERMINATED processes at this node.
```

### `bis_distance` — Bellman-Ford distance gradient (spreading)
```cpp
// C++: bis_distance(CALL, is_source, speed, comm)  → double
// Python DSL: d = bis_distance(is_source, speed, comm)
double dist = bis_distance(CALL, is_source_node, 1.0, COMM_RADIUS);
// dist == 0.0 at source; increases by hop distance away
```

### `abf_distance` — Adaptive Bellman-Ford distance
```cpp
// C++: abf_distance(CALL, is_source)  → double
// Python DSL: d = abf_distance(is_source)
double dist = abf_distance(CALL, is_source_node);
```

### `broadcast` — disseminate source's value to entire network
```cpp
// C++: broadcast(CALL, gradient_dist, source_value)  → T
// Python DSL: v = broadcast(is_source, value)  -- NOTE: Python DSL takes bool
// In C++: first arg is the BIS distance from source (used as gradient)
double diam = broadcast(CALL, dist_from_source, source_computed_diameter);
```

### `sp_collection` — spanning-tree aggregation toward source
```cpp
// C++: sp_collection(CALL, dist, local_val, null_val, accumulator)  → T
// Python DSL: result = sp_collection(dist, local_val, null_val, lambda a,b: ...)
auto subtree_uids = sp_collection(CALL,
    dist_to_root,
    std::set<device_t>{node.uid},  // local contribution
    std::set<device_t>{},          // null/identity value
    [](auto a, auto b){ return a | b; }
);
```

### `mp_collection` — multi-path aggregation
```cpp
// C++: mp_collection(CALL, dist, local, null, acc, divider)  → T
// Python DSL: result = mp_collection(dist, local, null, lambda a,b:..., lambda x,n:...)
double diameter = mp_collection(CALL,
    dist_from_source,
    dist_from_source,        // local value = own distance
    0.0,                     // null
    [](double a, double b){ return std::max(a, b); },
    [](double x, int n){ return x; }  // divider (no averaging here)
);
```

### `rectangle_walk` — random walk inside a box
```cpp
// C++: rectangle_walk(CALL, min_vec, max_vec, speed, period)
// Python DSL: rectangle_walk((x0,y0,z0), (x1,y1,z1), speed, period)
rectangle_walk(CALL,
    make_vec(0, 0, 0),
    make_vec(SIDE, SIDE, HEIGHT),
    SPEED,
    1   // movement period (rounds)
);
```

### `follow_target` — move toward a target position
```cpp
// C++: follow_target(CALL, target_pos, max_speed)
// Python DSL: follow_target(target_pos, max_speed)
follow_target(CALL, target_position, MAX_SPEED);
// Updates node.position each round; movement is smooth (limited by max_speed)
```

### `self_uid()` — node's unique identifier
```cpp
// C++: node.uid  (NOT a CALL-counter primitive — safe inside switch/if)
// Python DSL: self_uid()  → 0 (placeholder; transpiles to node.uid)
device_t my_id = node.uid;
```

---

## State Struct and `export_list`

The state struct is auto-generated. In hand-written C++, the key requirement is:
every field used by `nbr` must be in the **export_list**.

```cpp
// Python @dataclass → C++ struct
struct WorkerState {
    int   role;
    double dist_to_receiver;
    int   routing_set_size;
    int   received_count;
    int   active_procs;
};

// If any field is shared via nbr(), it must be exported:
// The C++ main setup registers which fields are shared.
// In fcpp_bridge, the transpiler handles this automatically.
```

**Common error**: if you call `nbr(CALL, some_field)` but `some_field`'s type is not
in the `export_list` of the component's type list, the C++ code won't compile.
Fix: add the missing type to `main_t`'s `export_list` in the CMakeLists.

---

## fcpp_bridge Python DSL Rules

### 1. All primitives called unconditionally
```python
# CORRECT: all primitives before branching
def compute(self, self_state, neighbors):
    dist   = bis_distance(is_src, 1.0, COMM)   # noqa: F821
    nbr_d  = nbr(dist)                         # noqa: F821
    parent = min_hood((nbr_d, self_uid()))      # noqa: F821
    # ... only pure Python branching below ...
    if is_src:
        return State(dist=0.0, ...)
    return State(dist=dist, ...)

# WRONG: primitive inside if
def compute(self, self_state, neighbors):
    if some_condition:
        dist = bis_distance(...)   # CALL counter misaligns!
```

### 2. No `from __future__ import annotations`
The transpiler resolves type annotations at import time.
With `from __future__ import annotations`, all annotations become strings → transpilation fails.

### 3. State dataclass type annotations must be C++-compatible
```python
# OK: transpiler can map these
local_db: Dict[int, Tuple[float, float]]  # → std::map<int, std::tuple<double,double>>
answer:   Optional[Tuple[float, float]]   # → std::optional<std::tuple<double,double>>
count:    int                             # → int

# FAIL: Ellipsis in Tuple
data: Tuple[float, ...]   # → transpiler cannot infer (use Tuple[float, float] for 2D)
data: Dict[str, Any]      # → Any has no C++ mapping
```

### 4. `old` two-argument form (preferred)
```python
# Explicit initial value + update function:
ticks = old(0, lambda prev: prev + 1 if exploring else 0)  # noqa: F821
log   = old({}, lambda prev: {**prev, **new_entries})       # noqa: F821
```

### 5. `spawn` status codes
```python
from fcpp_bridge.examples._example_utils import (
    SPAWN_STATUS_BORDER,     # 0 — fcpp::status::border
    SPAWN_STATUS_INTERNAL,   # 1 — fcpp::status::internal
    SPAWN_STATUS_TERMINATED, # 2 — fcpp::status::terminated_output
)
```

---

## fcpp_bridge Project Structure

```
src/fcpp_bridge/
├── python_dsl/          # @aggregate_function, Neighborhood, primitives
├── transpiler/          # Python AST → C++ source
├── compiler/            # CMake/g++ invocation, SHA-256 cache
├── ipc/                 # SwarmProcess, DeviceManager, PhysicalNode
│   ├── swarm_process.py      # launch binary, send/receive JSON over stdin/stdout
│   ├── device_manager.py     # add/remove nodes by ID
│   ├── liveness_strategy.py  # passive heartbeat / active ping-pong
│   └── physical_node.py      # per-node state and listener
├── examples/
│   ├── abstract_example.py   # Template Method base (validate→transpile→compile→run)
│   ├── _example_utils.py     # SPAWN_STATUS_*, neighbors_of, build_positions
│   ├── ex_utils/             # position.py, storage.py, tiles.py
│   ├── scattered_database.py # FE-9
│   ├── area_discovery.py     # FE-10
│   ├── iteratively_area_discovery.py  # FE-11
│   └── *.py                  # other examples (spreading_collection, worker_role, …)
└── tests/
```

---

## Running Examples

```bash
cd /home/cronomatita/Desktop/prog/cpp/c_cpp_study

# One-time setup — after this, no PYTHONPATH prefix ever needed:
pip install -e .

# Run examples:
python -m fcpp_bridge.examples.spreading_collection
python -m fcpp_bridge.examples.scattered_database

# Validate + transpile only (no C++ toolchain required):
python -c "
from fcpp_bridge.examples._example_utils import report_validation, report_transpilation
from fcpp_bridge.examples.scattered_database import ScatteredDBAggregate
report_validation(ScatteredDBAggregate)
report_transpilation(ScatteredDBAggregate)
"

# Run tests:
src/expr_eval_py/expr_eval_py_env/bin/pytest src/fcpp_bridge/tests/ -q

# No-install alternative (prefix every command):
PYTHONPATH=src python -m fcpp_bridge.examples.spreading_collection
PYTHONPATH=src src/expr_eval_py/expr_eval_py_env/bin/pytest src/fcpp_bridge/tests/ -q
```

---

## AbstractExample Pattern

```python
from fcpp_bridge.examples.abstract_example import AbstractExample
from fcpp_bridge.python_dsl import aggregate_function, Neighborhood
from dataclasses import dataclass
from pathlib import Path

@dataclass
class MyState:
    value: float = 0.0

@aggregate_function
class MyAggregate:
    def initial_state(self) -> MyState:
        return MyState()
    def compute(self, self_state: MyState, neighbors: Neighborhood[MyState]) -> MyState:
        d = bis_distance(self_uid() == 0, 1.0, 100.0)  # noqa: F821
        return MyState(value=d)

class MyExample(AbstractExample):
    @property
    def aggregate_class(self): return MyAggregate
    @property
    def log_prefix(self) -> str: return "my_example"
    @property
    def log_dir(self): return Path(__file__).parent / "logs"
    @property
    def build_dir(self): return Path(__file__).parent / ".fcpp_build"
    @property
    def cpp_dir(self): return Path(__file__).parent / ".fcpp_cpp"
    def initial_positions(self): return {i: (i*50.0, 0.0) for i in range(10)}
    def log_header(self, nid, sd): return f"# node {nid}\n# round,value\n"
    def log_line(self, r, nid, sd):
        d = sd if isinstance(sd, dict) else vars(sd)
        return f"{r},{d.get('value', 0.0):.4f}\n"

if __name__ == "__main__":
    MyExample().run(50)
```

---

## Field Calculus Theory (Brief)

- **Field**: a mapping from every device in the network to a value (of any type).
- **nbr(e)**: creates a "neighbouring field" — each device sees *e* evaluated at its 1-hop neighbours.
- **old(e)**: temporal lift — the value of *e* from the previous round.
- **spawn(key, fn)**: creates/maintains distributed sub-programs scoped to a subset of devices.
- Composition of these primitives yields self-healing, resilient distributed algorithms (e.g., distance gradients, spanning trees, data aggregation) without explicit message passing.
