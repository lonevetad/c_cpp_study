---
name: reference-fcpp-library
description: "FCPP C++14 aggregate programming library — all primitives, CALL macro, state/export_list, Python DSL rules, project layout; skill at <project>/.claude/commands/fcpp-library.md"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 30462d41-0a8b-4ed3-9933-02f384ad3e82
---

FCPP implements **Field Calculus** — an aggregate programming model. Each node runs
the same program, shares values with 1-hop neighbours each round, and distributed
algorithms emerge from these local interactions.

## Primary skill file
`<project>/.claude/commands/fcpp-library.md` — invoke with `/fcpp-library` for full reference.

## FCPP headers
```cpp
#include <fcpp/fcpp.hpp>                   // umbrella header
#include <lib/coordination/basics.hpp>     // nbr, old, spawn, count_hood
#include <lib/coordination/utils.hpp>      // min_hood, max_hood, fold_hood
#include <lib/coordination/spreading.hpp>  // bis_distance, abf_distance, broadcast
#include <lib/coordination/collection.hpp> // sp_collection, mp_collection
#include <lib/coordination/geometry.hpp>   // rectangle_walk, follow_target
```

## CALL macro pattern (critical)
Every FCPP aggregate primitive must be called in the **same order** at every node every round.
- `FUN void MAIN(ARGS) { CODE ... }` — aggregate function boilerplate
- `bis_distance(CALL, ...)` — CALL expands to `node, trace_t{trace, ++call_point}`
- `self_uid()` → `node.uid` — **not a CALL-counter primitive**; safe inside switch/if
- **Never** call any primitive inside a conditional; all primitives unconditional, branching after

## All primitives (Python DSL → C++)
| Python DSL                                    | C++                                           | Header       |
|-----------------------------------------------|-----------------------------------------------|--------------|
| `nbr(value)`                                  | `nbr(CALL, value)` → field<T>                | basics.hpp   |
| `old(init, lambda)`                           | `old(CALL, init, fn)` → T                    | basics.hpp   |
| `count_hood()`                                | `count_hood(CALL)` → int                     | basics.hpp   |
| `spawn(lambda, key)`                          | `spawn(CALL, fn, key)` → map<K,V>            | basics.hpp   |
| `min_hood(field)`                             | `min_hood(CALL, field)` → T                  | utils.hpp    |
| `max_hood(field)`                             | `max_hood(CALL, field)` → T                  | utils.hpp    |
| `fold_hood(fn, field, init)`                  | `fold_hood(CALL, fn, field, init)` → T       | utils.hpp    |
| `bis_distance(is_src, speed, comm)`           | `bis_distance(CALL, is_src, spd, com)` → dbl | spreading.hpp|
| `abf_distance(is_src)`                        | `abf_distance(CALL, is_src)` → double        | spreading.hpp|
| `broadcast(is_src, value)`                    | `broadcast(CALL, dist, value)` → T           | spreading.hpp|
| `sp_collection(dist, loc, null, fn)`          | `sp_collection(CALL, d, l, n, fn)` → T      | collection.hpp|
| `mp_collection(dist, loc, null, acc, div)`    | `mp_collection(CALL, ...)` → T               | collection.hpp|
| `rectangle_walk(min, max, spd, period)`       | `rectangle_walk(CALL, ...)` → void           | geometry.hpp  |
| `follow_target(pos, speed)`                   | `follow_target(CALL, pos, spd)` → void       | geometry.hpp  |
| `self_uid()`                                  | `node.uid` → device_t  (no CALL)             | —             |

## Spawn status codes (must match fcpp::status enum exactly)
```python
SPAWN_STATUS_BORDER     = 0   # fcpp::status::border — off routing path
SPAWN_STATUS_INTERNAL   = 1   # fcpp::status::internal — actively routing
SPAWN_STATUS_TERMINATED = 2   # fcpp::status::terminated_output — answer at destination
```
Import from: `fcpp_bridge.examples._example_utils`

## export_list rule (C++ compile error prevention)
If `nbr(CALL, X)` is called and `X`'s type is not in `main_t`'s `export_list`, the C++
binary won't compile. Fix: add the type to `export_list` in CMakeLists.  
See memory entry [[project-fcpp-export-list-rule]] for details.

## Python DSL rules (fcpp_bridge transpiler constraints)
1. **No `from __future__ import annotations`** — turns all annotations to strings; transpiler fails
2. **No `Tuple[float, ...]`** — Ellipsis in tuple args not handled; use `Tuple[float, float]`
3. **No `Any`** — no C++ mapping; use concrete types
4. **All primitives unconditional** — call before any if/match branching
5. **State dataclass fields** must use C++-compatible types from `typing`
6. `old(0, lambda prev: prev+1)` — two-arg form is preferred over one-arg

## fcpp_bridge key files
- `python_dsl/` — `@aggregate_function`, `Neighborhood`, primitive stubs
- `transpiler/transpiler_core.py` — Python AST → C++ source
- `python_dsl/types/aggregate_type.py` — Python type → C++ type inference
- `compiler/` — CMake/g++ invocation, SHA-256 cache
- `ipc/swarm_process.py` — launch binary, JSON IPC
- `examples/abstract_example.py` — Template Method base class
- `examples/_example_utils.py` — SPAWN_STATUS_*, neighbors_of, build_positions

## Exercises (FE-9/10/11) — implemented 2026-05-29
- `examples/ex_utils/tiles.py` — Sutherland-Hodgman tile grid + clipping
- `examples/scattered_database.py` — FE-9: distributed shard query via spawn
- `examples/area_discovery.py` — FE-10: nbr+fold_hood tile-centre sharing
- `examples/iteratively_area_discovery.py` — FE-11: 4-state machine, 2 scatter_databases, election

## Field Calculus primitives (theory)
- `nbr(e)` → neighbouring field: each device sees `e` from its 1-hop neighbours
- `old(e)` → temporal lift: value of `e` from the previous round
- `spawn(key, fn)` → distributed sub-program scoped to a device subset
- Composition yields self-healing distributed algorithms without explicit message passing
