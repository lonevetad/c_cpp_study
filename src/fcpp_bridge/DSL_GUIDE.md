# Python DSL Guide — Writing FCPP Aggregate Functions

This guide explains how to write aggregate programs using the `fcpp_bridge` Python DSL.
The DSL lets you express Field Calculus algorithms in Python; the transpiler converts
them to C++ FCPP code automatically.

---

## Table of Contents

1. [Core Concepts](#1-core-concepts)
2. [Writing an Aggregate Function](#2-writing-an-aggregate-function)
3. [State Types](#3-state-types)
4. [FCPP Primitives Reference](#4-fcpp-primitives-reference)
5. [Mixins](#5-mixins)
6. [C++-Alike Grammar](#6-c-alike-grammar)
7. [Lambda Expressions](#7-lambda-expressions)
8. [Transpilation Pipeline](#8-transpilation-pipeline)
9. [Limitations](#9-limitations)
10. [Complete Examples](#10-complete-examples)

---

## 1. Core Concepts

In FCPP (Field Calculus C++), **every node in the network runs the same program**.
Each round, a node sees:

- its own state from the previous round (`self_state`)
- the states of its immediate radio neighbors (`neighbors`)

It produces a new state, which is stored and broadcast to neighbors next round.
The DSL captures exactly this pattern: you write `initial_state()` (what the state
is before round 0) and `compute()` (how to update state each round).

The transpiler converts your Python class into a C++ `AGGREGATE_TEMPLATE` function
that calls FCPP primitives with the `CALL` macro.

---

## 2. Writing an Aggregate Function

### Minimal skeleton

```python
from fcpp_bridge.python_dsl import aggregate_function, Neighborhood

@aggregate_function
class MyAggregate:
    def initial_state(self) -> float:
        return 0.0

    def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
        return self_state + 1.0
```

### Rules

| Rule | Detail |
|------|--------|
| Decorate with `@aggregate_function` | Required; validates the class structure |
| `initial_state(self)` | Must have a return type annotation and return a literal value |
| `compute(self, self_state, neighbors)` | Must accept exactly these two parameters (any names OK) |
| State type must be consistent | Return type of `initial_state` must match `compute` |
| FCPP primitives are bare names | Do not import them; the transpiler recognises them by name |

### Parameter name aliases

The transpiler accepts several alternative names for the parameters:

| Meaning | Accepted Python names |
|---------|----------------------|
| current node state | `self_state`, `state`, `s` |
| neighbor states | `neighbors`, `nbrs`, `neighborhood` |

---

## 3. State Types

The state type is inferred from the return type annotation on `initial_state`.

### Primitive types

| Python annotation | C++ type |
|------------------|----------|
| `float` | `double` |
| `int` | `int` |
| `bool` | `bool` |
| `str` | `std::string` |

### Generic container types

| Python annotation | C++ type |
|------------------|----------|
| `list[float]` | `std::vector<double>` |
| `list[int]` | `std::vector<int>` |
| `tuple[float, int]` | `std::tuple<double, int>` |
| `dict[str, float]` | `std::map<std::string, double>` |

### Struct types (dataclasses)

For complex states, use a `@dataclass`:

```python
from dataclasses import dataclass
from fcpp_bridge.python_dsl import aggregate_function, Neighborhood

@dataclass
class NodeState:
    distance: float
    hops: int
    parent_id: int

@aggregate_function
class DistanceAggregate:
    def initial_state(self) -> NodeState:
        return NodeState(distance=float('inf'), hops=999, parent_id=-1)

    def compute(self, self_state: NodeState, neighbors: Neighborhood[NodeState]) -> NodeState:
        # ...
        return NodeState(distance=dist, hops=h, parent_id=pid)
```

The transpiler generates a C++ `struct NodeState { double distance; int hops; int parent_id; };`.

---

## 4. FCPP Primitives Reference

Primitives are written as bare function calls in `compute()`.
The transpiler wraps them with `CALL` automatically.

### Neighbourhood & temporal

| Python DSL | C++ output | Description |
|------------|-----------|-------------|
| `nbr(value)` | `nbr(CALL, value)` | Field of neighbor values this round |
| `old(value)` | `old(CALL, value)` | Value from the previous round |
| `nbr_uid()` | `nbr_uid(CALL)` | Unique ID of each neighbor |
| `oldnbr(x, op)` | `oldnbr(CALL, x, op)` | Combination of old and nbr |
| `self_uid()` | `node.uid` | **This** device's unique identifier (no CALL counter — safe inside branches) |

### Hood reductions

| Python DSL | C++ output | Description |
|------------|-----------|-------------|
| `fold_hood(init, fn)` | `fold_hood(CALL, init, fn)` | Reduce neighborhood with binary function |
| `min_hood(field)` | `min_hood(CALL, field)` | Minimum over neighborhood |
| `max_hood(field)` | `max_hood(CALL, field)` | Maximum over neighborhood |
| `sum_hood(field)` | `sum_hood(CALL, field)` | Sum over neighborhood |
| `mean_hood(field)` | `mean_hood(CALL, field)` | Mean over neighborhood |
| `count_hood()` | `count_hood(CALL)` | Number of neighbors |
| `all_hood(pred)` | `all_hood(CALL, pred)` | True if all neighbors satisfy predicate |
| `any_hood(pred)` | `any_hood(CALL, pred)` | True if any neighbor satisfies predicate |
| `list_hood(comp, field)` | `list_hood(CALL, comp, field)` | Sorted list of neighbor values |

### Spreading

| Python DSL | Description |
|------------|-------------|
| `bis_distance(src_flag, speed, range)` | Bidirectional shortest path distance |
| `abf_distance(src_flag)` | ABF distance gradient |
| `abf_hops(src_flag)` | ABF hop-count gradient |
| `flex_distance(src, epsilon, range, dist, factor)` | Flexible gradient |
| `broadcast(src_flag, value)` | Propagate value from source |
| `bis_ksource_broadcast(src, v, k, p, sp)` | K-source broadcast |

### Collection

| Python DSL | Description |
|------------|-------------|
| `gossip(init, acc)` | Gossip protocol (total aggregate) |
| `gossip_min(v)` | Network-wide minimum via gossip |
| `gossip_max(v)` | Network-wide maximum via gossip |
| `gossip_mean(v)` | Network-wide mean via gossip |
| `sp_collection(d, v, n, acc)` | Single-path collection |
| `mp_collection(d, v, n, acc, div)` | Multi-path collection |
| `wmp_collection(d, r, v, acc, mul)` | Weighted multi-path collection |
| `list_idem_collection(...)` | Idempotent list collection |
| `list_arith_collection(...)` | Arithmetic list collection |

### Geometry & movement

| Python DSL | Description |
|------------|-------------|
| `follow_target(target, speed, pos)` | Move toward target position |
| `follow_path(path, speed, time)` | Follow a predefined path |
| `follow_track(track)` | Follow a track |
| `rectangle_walk(lo, hi, speed, pos)` | Random walk in a rectangle |
| `random_rectangle_target(lo, hi)` | Random target within rectangle |
| `neighbour_elastic_force(len, stiff)` | Spring force toward neighbors |
| `neighbour_gravitational_force(g, m)` | Gravity toward neighbors |
| `neighbour_charged_force(k, q)` | Coulomb repulsion from neighbors |

### Election

| Python DSL | Description |
|------------|-------------|
| `diameter_election(v, dist)` | Leader election by diameter |
| `color_election(v)` | Probabilistic leader election |
| `wave_election(v)` | Wave-based leader election |
| `diameter_election_distance(v, dist)` | Diameter election with distance |
| `color_election_distance(v)` | Color election with distance |
| `wave_election_distance(v)` | Wave election with distance |

### Time & filtering

| Python DSL | Description |
|------------|-------------|
| `constant(v)` | Value that never changes |
| `constant_after(v, t)` | Constant after time `t` |
| `counter()` | Increment by 1 each round |
| `delay(v, n)` | Delay value by `n` rounds |
| `round_since(cond)` | Rounds since condition was true |
| `time_since(cond)` | Milliseconds since condition was true |
| `timed_decay(v, n, dt)` | Decay value over time |
| `exponential_filter(v, factor)` | Exponential moving average |
| `shared_clock()` | Network-synchronized clock |
| `shared_decay(v, factor)` | Network-wide decaying value |
| `shared_filter(v, factor)` | Network-wide exponential filter |
| `toggle(cond)` | Boolean toggle on condition edge |
| `toggle_filter(cond, factor)` | Filtered toggle |

### Other

| Python DSL | Description |
|------------|-------------|
| `align(x)` | Align field with neighbor UIDs |
| `align_inplace(x)` | In-place alignment |
| `mod_other(x)` | Modify other's value |
| `split(key, fn)` | Partition network by key |
| `spawn(fn, keys)` | Spawn sub-processes for keys |

---

## 5. Mixins

Mixins are decorators that add pre-built distributed algorithm methods to your class.
Stack multiple mixins by applying several decorators.

```python
from fcpp_bridge.python_dsl import (
    aggregate_function, mixin_gossip, mixin_broadcast,
    mixin_election, mixin_collection, mixin_geometry, mixin_time,
    Neighborhood,
)

@aggregate_function
@mixin_gossip
@mixin_broadcast
class MyAggregate:
    ...
```

| Mixin | Added methods | Purpose |
|-------|--------------|---------|
| `@mixin_gossip` | gossip helpers | Distributed aggregation |
| `@mixin_broadcast` | broadcast helpers | Value dissemination from a source |
| `@mixin_collection` | collection helpers | Many-to-one data collection |
| `@mixin_election` | election helpers | Distributed leader election |
| `@mixin_geometry` | geometry helpers | Spatial movement and forces |
| `@mixin_time` | time helpers | Temporal patterns and filtering |

---

## 6. C++-Alike Grammar

The `compute()` method supports the following Python constructs that map directly
to C++ control-flow and assignment statements.  The transpiler converts them
statement-by-statement, so you can write idiomatic Python that reads naturally and
generates valid C++.

### 6.1 Variable assignment

```python
def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
    is_src = (self_state == 0.0)           # auto is_src = (self_state == 0.0);
    dist = bis_distance(is_src, 1.0, 50.0) # auto dist = bis_distance(CALL, is_src, 1.0, 50.0);
    return dist
```

First assignment to a name generates `auto name = expr;`.
Subsequent assignments to the same name generate `name = expr;` (no `auto`).

Augmented assignments (`+=`, `-=`, `*=`, `/=`, `%=`) translate directly:

```python
total += weight   # total += weight;
```

### 6.2 Conditional — if / elif / else

```python
def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
    if not neighbors:
        return self_state                  # early-return guard

    min_val = min_hood(nbr(self_state))
    if min_val < self_state:
        return min_val                     # improved state
    elif min_val == self_state:
        return self_state * 0.99           # slight decay
    else:
        return self_state
```

Generated C++:

```cpp
if ((!neighbors)) {
    return self_state;
}
auto min_val = min_hood(CALL, nbr(CALL, self_state));
if ((min_val < self_state)) {
    return min_val;
} else if ((min_val == self_state)) {
    return (self_state * 0.99);
} else {
    return self_state;
}
```

### 6.3 Ternary expression

Python's inline conditional maps to the C++ ternary operator:

```python
hops = 0 if is_src else min_hood(nbr_hops) + 1
# → auto hops = (is_src ? 0 : min_hood(CALL, nbr_hops) + 1);
```

### 6.4 Boolean and logical operators

| Python | C++ |
|--------|-----|
| `a and b` | `(a && b)` |
| `a or b` | `(a \|\| b)` |
| `not x` | `(!x)` |

```python
if is_src and dist < threshold:
    # → if (((is_src && (dist < threshold)))) {
```

### 6.5 While loop

```python
def compute(self, self_state: int, neighbors: Neighborhood[int]) -> int:
    count = 0
    i = 0
    while i < 5:
        count += 1
        i += 1
    return count
```

Generated C++:

```cpp
auto count = 0;
auto i = 0;
while ((i < 5)) {
    count += 1;
    i += 1;
}
return count;
```

**Note:** While loops are rarely idiomatic in aggregate programs (FCPP is round-based,
not time-stepped within a single round), but they are useful for local, non-aggregate
computations within the `compute()` body.

### 6.6 For loop (range-based)

The transpiler supports `for i in range(...)` with 1, 2, or 3 arguments:

```python
for i in range(n):          # for (int i = 0; i < n; ++i)
for i in range(2, 8):       # for (int i = 2; i < 8; ++i)
for i in range(0, 20, 2):   # for (int i = 0; i < 20; i += 2)
```

Example:

```python
def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
    total = 0.0
    for i in range(10):
        total += self_state * 0.1
    return total
```

Only `range()`-based for loops are supported.  Iterating over collections
(e.g., `for x in values:`) is not transpiled.

### 6.7 Switch — Python `match/case` (Python 3.10+)

Python's `match`/`case` statement maps to a C++ `switch`.
The subject must be an integer-compatible expression.

```python
def compute(self, self_state: int, neighbors: Neighborhood[int]) -> int:
    match self_state:
        case 0:
            return counter()
        case 1:
            return broadcast(True, 42)
        case _:
            return self_state
```

Generated C++:

```cpp
switch (self_state) {
case 0:
    return counter(CALL);
    break;
case 1:
    return broadcast(CALL, True, 42);
    break;
default:
    return self_state;
    break;
}
```

**IntEnum constant-folding (v1.8.4):** The transpiler resolves dotted chains like
`WorkerRole.RECEIVER.value` to integer literals automatically, so `IntEnum` member
values can be used directly in case patterns and comparisons:

```python
from enum import IntEnum

class Mode(IntEnum):
    IDLE = 0
    ACTIVE = 1

def compute(...):
    match self_state:
        case Mode.IDLE.value:     # → case 0:
            ...
        case Mode.ACTIVE.value:   # → case 1:
            ...
```

**Guard clauses (v2.0):** `case X if condition:` wraps the case body in an
`if` block.  The `break` still follows unconditionally, so a non-matching guard
exits the switch rather than falling through:

```python
match role:
    case Role.SENDER.value if dist < threshold:
        inject_message()
    case Role.RECEIVER.value:
        collect_message()
    case _:
        relay()
```

Generated C++:

```cpp
switch (role) {
case 1:
    if ((dist < threshold)) {
        inject_message();
    }
    break;
case 3:
    collect_message();
    break;
default:
    relay();
    break;
}
```

**Guard expressions must not contain aggregate primitives.**  All `nbr`, `old`,
`bis_distance`, etc. calls must appear *before* the `match` statement; guards
may reference their results via local variables.

**OR patterns (v2.0):** `case A | B | C:` maps to multiple C++ case labels
sharing the same body (C++ fallthrough labels, valid in C++14):

```python
match comm_type:
    case RoleCommunicationType.ENDPOINT.value | RoleCommunicationType.REPEATER.value:
        relay = True
    case RoleCommunicationType.RECEIVER.value:
        relay = False
```

Generated C++:

```cpp
switch (comm_type) {
case 0:
case 2:
    auto relay = true;
    break;
case 1:
    auto relay = false;
    break;
default: break;
}
```

OR patterns and guard clauses can be combined: `case A | B if cond:` wraps the
shared body in an `if` block.

**Restrictions:**
- Case patterns must resolve to integer/float literals (or be integer literals directly).
  String or non-numeric enum values cannot be used as C++ case labels.
- Sequence patterns (`case (x, y):`), class patterns (`case Cls(x=a):`), and
  capture patterns (`case name:`) have no C++ switch equivalent — use `if/elif/else`.
- Enum folding requires the enum class to be in the module globals of the
  `compute()` function (typically satisfied by defining it at module level).

### 6.8 `break` and `continue`

```python
while running:
    if done:
        break      # → break;
    if skip:
        continue   # → continue;
```

### Summary table

| Python construct | C++ equivalent | Notes |
|-----------------|---------------|-------|
| `x = expr` | `auto x = expr;` | `auto` on first declaration |
| `x = expr` (re-assign) | `x = expr;` | No `auto` after first use |
| `x += y` | `x += y;` | Also `-=`, `*=`, `/=`, `%=` |
| `return expr` | `return expr;` | |
| `if cond: ...` | `if (cond) { ... }` | |
| `elif cond: ...` | `else if (cond) { ... }` | |
| `else: ...` | `else { ... }` | |
| `a if c else b` | `(c ? a : b)` | Inline ternary |
| `a and b` | `(a && b)` | |
| `a or b` | `(a \|\| b)` | |
| `not x` | `(!x)` | |
| `while cond: ...` | `while (cond) { ... }` | |
| `for i in range(n): ...` | `for (int i=0; i<n; ++i) { ... }` | |
| `match x: case v: ...` | `switch (x) { case v: ... }` | Python 3.10+ |
| `case v if cond: ...` | `case v: if (cond) { ... }` | guard clause (v2.0) |
| `case A \| B: ...` | `case A: case B: ...` | OR pattern, C++ fallthrough (v2.0) |
| `break` | `break;` | |
| `continue` | `continue;` | |

---

## 7. Lambda Expressions

Lambdas are used as arguments to primitives that accept binary functions
(e.g., `fold_hood`, `gossip`, `split`).

```python
# Python lambda
total = fold_hood(0, lambda acc, v: acc + v)

# Generated C++ lambda
auto total = fold_hood(CALL, 0, [=](auto acc, auto v) { return (acc + v); });
```

Multi-argument lambdas and comparisons work too:

```python
fold_hood(float('inf'), lambda a, b: a if a < b else b)
# → fold_hood(CALL, inf, [=](auto a, auto b) { return ((a < b) ? a : b); })
```

---

## 8. Transpilation Pipeline

When you call `Transpiler(MyAggregate).generate()`, this happens:

```
Python class
    │
    ▼ inspect.getsource()
Python source code
    │
    ▼ ast.parse()
Python AST
    │
    ▼ PythonAstVisitor.transpile_statements()
C++ body statements
    │
    ▼ CppCodeBuilder.build()
Complete C++ program
    ┌──────────────────────────────────────────┐
    │ #include <fcpp/fcpp.hpp>                 │
    │ #include <lib/coordination/...>          │
    │                                          │
    │ struct MyState { ... };        (if used) │
    │                                          │
    │ MyState compute_next_state(              │
    │     const MyState& self_state,           │
    │     const std::vector<MyState>& nbrs) {  │
    │     /* transpiled body */                │
    │ }                                        │
    │                                          │
    │ AGGREGATE_TEMPLATE(main) : void { ... }  │
    │ int main(...) { ... }                    │
    └──────────────────────────────────────────┘
```

The `AGGREGATE_TEMPLATE(main)` wrapper uses FCPP's `old`/`nbr`/`fold_hood`
to maintain state across rounds and collect neighbor states.

### Header injection

Each FCPP primitive you use in `compute()` causes its C++ header to be included
automatically.  For example, using `min_hood` adds
`#include <lib/coordination/utils.hpp>`.

### Parameter remapping

| Python name | C++ name |
|-------------|---------|
| `self_state` (or `state`, `s`) | `self_state` |
| `neighbors` (or `nbrs`, `neighborhood`) | `neighbor_states` |

---

## 9. Limitations

| Limitation | Workaround |
|-----------|------------|
| `for` only supports `range()` | Use a `while` loop for other iterations |
| `match/case` with non-integer-valued constants | `IntEnum.value` chains are constant-folded automatically; use `if/elif/else` for string dispatch |
| Sequence/class/capture patterns in `match/case` | Use `if/elif/else`; no C++ switch equivalent for structural matching |
| Variable declared in both `if` and `else` bodies may cause C++ scope errors | Declare the variable before the `if` block |
| No type inference for local variables (all emit `auto`) | Correct in most cases; C++ deduces the type |
| Attribute calls on arbitrary objects (`obj.method()`) pass through verbatim | Ensure the C++ object has the expected method |
| `for x in collection:` is not supported | Use index-based `for i in range(len(...)):` |
| `ActivePingStrategy` requires a C++ ping responder on physical nodes | Implement the ping endpoint on device firmware |
| `self_uid()` returns `0` in Python (placeholder) | Use the real `nid` in demo simulations; generated C++ uses `node.uid` correctly |
| FCPP primitives inside `match/case` guards or bodies desync CALL counter | Place all primitives before the `match/case`; only local expressions inside cases and guards |

---

## 10. Complete Examples

### Running examples

Every example in `examples/` is an `AbstractExample` subclass.  Calling
`example.run(num_rounds)` runs the full toolchain automatically:

1. `AggregateValidator.validate(self.aggregate_class)` — checks DSL constraints
2. `Transpiler(self.aggregate_class).generate()` — produces C++ source
3. `Compiler.get_or_compile(cpp_code, name)` — compiles (SHA-256 cached)
4. `SwarmProcess.start()` — spawns the compiled binary
5. Rounds loop: `step()` → `_on_snapshot()` writes log lines → `on_round_complete()`
6. `swarm.close()` then `on_simulation_end()`

Subclasses must implement: `aggregate_class`, `log_prefix`, `initial_positions()`,
`log_header()`, `log_line()`.

Optional hooks: `on_simulation_start()`, `on_simulation_end()`,
`on_round_complete(round_num, snapshot: SwarmSnapshot)`.

### Example A — Hop-count distance from a source

```python
from dataclasses import dataclass
from fcpp_bridge.python_dsl import aggregate_function, Neighborhood

@dataclass
class HopState:
    hops: int
    source_id: int

@aggregate_function
class HopDistance:
    def initial_state(self) -> HopState:
        return HopState(hops=999, source_id=-1)

    def compute(self, self_state: HopState, neighbors: Neighborhood[HopState]) -> HopState:
        is_src = (self_state.source_id == 0)

        if is_src:
            return HopState(hops=0, source_id=0)

        nbr_hops = nbr(self_state.hops)      # noqa: F821
        best = min_hood(nbr_hops) + 1        # noqa: F821

        if best < self_state.hops:
            return HopState(hops=best, source_id=0)

        return self_state
```

### Example B — Network-wide average with gossip

```python
from fcpp_bridge.python_dsl import aggregate_function, mixin_gossip, Neighborhood

@aggregate_function
@mixin_gossip
class NetworkAverage:
    def initial_state(self) -> float:
        return 0.0

    def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
        if not neighbors:          # noqa: F821
            return self_state

        best_val = max(self_state, gossip_max(self_state))  # noqa: F821
        return best_val
```

### Example C — Mode-based behavior (switch)

```python
from fcpp_bridge.python_dsl import aggregate_function, Neighborhood

@aggregate_function
class ModeAggregate:
    def initial_state(self) -> int:
        return 0

    def compute(self, self_state: int, neighbors: Neighborhood[int]) -> int:
        match self_state:
            case 0:
                return counter()              # noqa: F821
            case 1:
                return broadcast(True, 99)    # noqa: F821
            case 2:
                return min_hood(nbr(0))       # noqa: F821
            case _:
                return 0
```

### Example D — Iterative local computation

```python
from fcpp_bridge.python_dsl import aggregate_function, Neighborhood

@aggregate_function
class IterativeAggregate:
    def initial_state(self) -> float:
        return 1.0

    def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
        # Compute 10-step local decay
        val = self_state
        for i in range(10):
            val = val * 0.9

        # Combine with neighborhood minimum
        nbr_val = nbr(self_state)             # noqa: F821
        network_min = min_hood(nbr_val)       # noqa: F821

        return val if val < network_min else network_min
```
