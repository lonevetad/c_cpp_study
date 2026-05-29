# FCPP Primitive Coverage Audit

**Date:** 2026-05-23  
**Scope:** `src/fcpp_py_porting/fcpp_clone_GITIGNORE_ME/` → `src/fcpp_bridge/`

---

## 1. C++ Source Scan

### What we looked for

All `.cpp` and `.hpp` files in the FCPP clone were scanned for:
- Functions accepting `node_t& node, trace_t call_point` (the FCPP aggregate function signature)
- Template parameters named `CALL`, `ARGS`, or `CODE` (FCPP macro conventions)
- Functions matching the target set from `provided_prompt.txt`

### Canonical source files

| Source file | Contents |
|-------------|----------|
| `fcpp/src/lib/coordination/basics.hpp` | `nbr`, `old`, `oldnbr`, `fold_hood`, `count_hood`, `spawn` |
| `fcpp/src/lib/coordination/utils.hpp` | `min_hood`, `max_hood`, `all_hood`, `any_hood`, `sum_hood`, `mean_hood`, `list_hood` |
| `fcpp/src/lib/coordination/spreading.hpp` | `abf_distance`, `bis_distance`, `broadcast`, `bis_ksource_broadcast` |
| `fcpp/src/lib/coordination/collection.hpp` | `gossip`, `gossip_min/max/mean`, `sp_collection`, `mp_collection`, `wmp_collection`, `list_idem_collection`, `list_arith_collection` |
| `fcpp/src/lib/coordination/geometry.hpp` | `follow_target`, `rectangle_walk` |
| `fcpp/src/lib/data/field.hpp` | `map_hood`, `mod_hood`, `field<T>`, `to_field<T>`, `to_local<T>` |

### All aggregate functions found

| Name | Signature pattern | Header |
|------|-------------------|--------|
| `nbr` | `nbr(node, cp, f0)` / `nbr(node, cp, f0, op)` / `nbr(node, cp, f0, f)` | basics.hpp |
| `old` | `old(node, cp, f0)` / `old(node, cp, f0, op)` / `old(node, cp, f0, f)` | basics.hpp |
| `oldnbr` | `oldnbr(node, cp, f0, op)` | basics.hpp |
| `fold_hood` | `fold_hood(node, cp, op, a)` / `fold_hood(node, cp, op, a, b)` | basics.hpp |
| `count_hood` | `count_hood(node, cp)` | basics.hpp |
| `spawn` | `spawn(node, cp, process, key_set, xs...)` (3 overloads) | basics.hpp |
| `min_hood` | `min_hood(node, cp, a)` / `min_hood(node, cp, a, b)` | utils.hpp |
| `max_hood` | `max_hood(node, cp, a)` / `max_hood(node, cp, a, b)` | utils.hpp |
| `all_hood` | `all_hood(node, cp, a)` / variant with self | utils.hpp |
| `any_hood` | `any_hood(node, cp, a)` / variant with self | utils.hpp |
| `sum_hood` | `sum_hood(node, cp, a)` / variant with self | utils.hpp |
| `mean_hood` | `mean_hood(node, cp, a)` / variant with self | utils.hpp |
| `list_hood` | `list_hood(node, cp, c, a, b)` (4 overloads) | utils.hpp |
| `abf_distance` | `abf_distance(node, cp, source)` / with metric | spreading.hpp |
| `bis_distance` | `bis_distance(node, cp, source, period, speed)` / with metric | spreading.hpp |
| `broadcast` | `broadcast(node, cp, distance, value)` / with source | spreading.hpp |
| `bis_ksource_broadcast` | `bis_ksource_broadcast(node, cp, source, value, k, period, speed)` | spreading.hpp |
| `gossip` | `gossip(node, cp, value, accumulate)` | collection.hpp |
| `gossip_min/max/mean` | `gossip_X(node, cp, value)` | collection.hpp |
| `sp_collection` | `sp_collection(node, cp, distance, value, null, accumulate)` | collection.hpp |
| `mp_collection` | `mp_collection(node, cp, distance, value, null, accumulate, divide)` | collection.hpp |
| `wmp_collection` | `wmp_collection(node, cp, distance, radius, value, accumulate, multiply)` | collection.hpp |
| `list_idem_collection` | `list_idem_collection(node, cp, distance, value, radius, speed, null, eps, accumulate)` | collection.hpp |
| `list_arith_collection` | similar | collection.hpp |
| `follow_target` | `follow_target(node, cp, target, max_v, period)` / with max_a | geometry.hpp |
| `rectangle_walk` | `rectangle_walk(node, cp, low, hi, max_v, period)` / with reach | geometry.hpp |
| `map_hood` / `mod_hood` | field-level operators | field.hpp |

---

## 2. Pre-refactoring Gap Analysis

The **15 target primitives** from `provided_prompt.txt` were checked against each bridge layer.

### Layer 1 — Python DSL (`python_dsl/primitives.py`)

| Primitive | Before | After |
|-----------|--------|-------|
| `nbr` | ✅ `Neighborhood` class | ✅ |
| `old` | ✅ `OldValue` class | ✅ |
| `spawn` | ✅ `Spawn` class | ✅ |
| `min_hood` | ✅ `MinHood` class | ✅ |
| `max_hood` | ✅ `MaxHood` class | ✅ |
| `count_hood` | ✅ `CountHood` class | ✅ |
| `fold_hood` | ✅ `FoldHood` class | ✅ |
| `broadcast` | ✅ `Broadcast` class | ✅ |
| `gossip` | ❌ missing | ✅ `Gossip` added |
| `sp_collection` | ❌ mixin stub, no class | ✅ `SpCollection` added |
| `mp_collection` | ❌ mixin stub, no class | ✅ `MpCollection` added |
| `wmp_collection` | ❌ mixin stub, no class | ✅ `WmpCollection` added |
| `bis_distance` | ❌ missing | ✅ `BisDistance` added |
| `abf_distance` | ❌ missing | ✅ `AbfDistance` added |
| `rectangle_walk` | ❌ missing | ✅ `RectangleWalk` added |
| `follow_target` | ❌ missing | ✅ `FollowTarget` added |

**8 new primitive classes added.**

### Layer 2 — C++ Transpiler (`transpiler/__init__.py`)

`PythonAstVisitor.visit_Call` previously mapped only Python builtins (`max`, `min`, `sum`, `len`). When a user wrote `min_hood(x)` in a compute method, the transpiler emitted `min_hood(x)` — missing the mandatory `CALL` first-argument that FCPP requires.

| Issue | Before | After |
|-------|--------|-------|
| FCPP primitive recognition | ❌ None — all passed through as-is | ✅ All 16 primitives inject `CALL` |
| `count_hood()` (no user args) | ❌ `count_hood()` | ✅ `count_hood(CALL)` |
| Multi-arg: `sp_collection(d,v,n,acc)` | ❌ `sp_collection(d,v,n,acc)` | ✅ `sp_collection(CALL,d,v,n,acc)` |
| Header tracking | ❌ Only `<fcpp/fcpp.hpp>` always | ✅ Per-primitive headers added automatically |
| `used_primitives` tracking | ❌ missing | ✅ `PythonAstVisitor.used_primitives` list |

### Layer 3 — Grammar

#### `AggregateProgram.g4` (ANTLR)

| Issue | Before | After |
|-------|--------|-------|
| `primitiveCall` rule | Only `primitive(expr)` or `FOLD_HOOD(expr,expr)` — hardcoded arities | ✅ `primitive LPAREN argList? RPAREN` — variable args |
| `primitive` rule | Only `NBR`, `OLD`, `MAX_HOOD`, `MIN_HOOD`, `COUNT_HOOD` | ✅ All 16 primitives |
| Missing lexer tokens | `SPAWN`, `BROADCAST`, `GOSSIP`, `SP_COLLECTION`, etc. absent | ✅ 10 new tokens added |

#### Python `AggregateLanguageParser` (`grammar/__init__.py`)

| Issue | Before | After |
|-------|--------|-------|
| `_tokenize` PRIMITIVE regex | Only 6 primitives | ✅ All 16 primitives |
| `_parse_call_expr` | Only 5 primitives, single-arg only | ✅ All 16 primitives, variable-arg (`argList` style) |
| `_ALL_PRIMITIVES` frozenset | Missing | ✅ Added as class attribute |

#### Mixin decorators (`python_dsl/decorators.py`)

| Mixin method | Before | After |
|--------------|--------|-------|
| `mixin_collection.sp_collection` | `return expr` (stub) | ✅ Returns `SpCollection(...)` |
| `mixin_collection.mp_collection` | `return expr` (stub) | ✅ Returns `MpCollection(...)` |
| `mixin_collection.wmp_collection` | `return expr` (stub) | ✅ Returns `WmpCollection(...)` |
| `mixin_geometry.follow_target` | missing | ✅ Returns `FollowTarget(...)` |
| `mixin_geometry.rectangle_walk` | missing | ✅ Returns `RectangleWalk(...)` |
| `mixin_geometry.bis_distance` | missing | ✅ Returns `BisDistance(...)` |
| `mixin_geometry.abf_distance` | missing | ✅ Returns `AbfDistance(...)` |
| `mixin_gossip.gossip` | missing | ✅ Returns `Gossip(...)` |
| `mixin_gossip.gossip_avg` | `return value` (stub) | ✅ Returns `Gossip(value, avg_lambda)` |

---

## 3. Files Changed

### Phase A (15 target primitives + gap closure)

| File | Change type | Description |
|------|-------------|-------------|
| `python_dsl/primitives.py` | Added | 8 new primitive classes |
| `python_dsl/__init__.py` | Updated | Export all 8 new classes |
| `python_dsl/decorators.py` | Updated | Mixin methods return proper primitive objects |
| `transpiler/__init__.py` | Updated | `_FCPP_PRIMITIVES` dict; `visit_Call` injects `CALL`; header tracking via `used_primitives` |
| `grammar/__init__.py` | Updated | PRIMITIVE regex + `_parse_call_expr` for all 16 primitives with variable-arg parsing |
| `grammar/AggregateProgram.g4` | Updated | 10 new lexer tokens; `primitiveCall` rule uses `argList?`; `primitive` rule lists all 16 |
| `tests/test_dsl.py` | Updated | +18 tests for new classes and mixin methods |
| `tests/test_transpiler.py` | Updated | +19 tests for `CALL` injection and header tracking |
| `tests/test_parser.py` | Updated | +14 tests for tokenization and multi-arg parsing |

### Phase B (all 64 FCPP coordination primitives)

| File | Change type | Description |
|------|-------------|-------------|
| `python_dsl/primitives.py` | Added | 48 new primitive classes (6 basics, 5 utils, 3 spreading, 5 collection, 10 geometry, 6 election, 13 time) |
| `python_dsl/__init__.py` | Updated | Export all 48 new classes; add `mixin_election`, `mixin_time` to `__all__` |
| `python_dsl/decorators.py` | Updated | Added `mixin_election` (6 methods), `mixin_time` (13 methods); extended `mixin_geometry` with 7 more methods |
| `transpiler/__init__.py` | Updated | `_FCPP_PRIMITIVES` expanded to 64 entries (all 7 coordination headers) |
| `grammar/__init__.py` | Updated | `_ALL_PRIMITIVES` frozenset at 64 entries; PRIMITIVE regex covers all 64 names |
| `grammar/AggregateProgram.g4` | Updated | ~50 new lexer tokens; `primitive` rule covers all 64 tokens |
| `tests/test_dsl.py` | Updated | +70 tests (Tests 11-18, one per header group + mixin tests) |
| `tests/test_transpiler.py` | Updated | +~40 tests (Tests 12-13: CALL injection + header mapping for all new primitives) |
| `tests/test_parser.py` | Updated | +~20 tests (Tests 12-13: tokenization by group; frozenset size assert == 64) |

---

## 4. Test Results

| State | Tests |
|-------|-------|
| Before refactoring | 217 (215 pass, 2 skip) |
| After Phase A | 268 pass, 0 fail |
| After Phase B | **379 pass, 0 fail** |
| Total new tests added | **+162** |

---

## 5. Primitive Coverage Summary

All 64 FCPP coordination library primitives are now fully represented in all three bridge layers.

### basics.hpp (11)
```
nbr  old  nbr_uid  oldnbr  align  align_inplace
mod_other  split  fold_hood  count_hood  spawn
```

### utils.hpp (7)
```
min_hood  max_hood  sum_hood  mean_hood
all_hood  any_hood  list_hood
```

### spreading.hpp (6)
```
abf_distance  abf_hops  bis_distance  flex_distance
broadcast  bis_ksource_broadcast
```

### collection.hpp (9)
```
gossip  gossip_min  gossip_max  gossip_mean
sp_collection  mp_collection  wmp_collection
list_idem_collection  list_arith_collection
```

### geometry.hpp (12)
```
follow_target  follow_path  follow_track
rectangle_walk  random_rectangle_target
neighbour_elastic_force  neighbour_gravitational_force
neighbour_charged_force  line_elastic_force
plane_elastic_force  point_elastic_force  point_gravitational_force
```

### election.hpp (6)
```
diameter_election  diameter_election_distance
color_election  color_election_distance
wave_election  wave_election_distance
```

### time.hpp (13)
```
constant  constant_after  counter  delay
round_since  time_since  timed_decay  exponential_filter
shared_clock  shared_decay  shared_filter  toggle  toggle_filter
```

**Excluded** (3): `spawn_deprecated` (deprecated), `color_election_internal` / `wave_election_internal` (internal implementation detail).

---

## 6. FCPP Primitive → Bridge Layer Mapping Reference

| Primitive | Python class | C++ header |
|-----------|-------------|------------|
| `nbr` | `Neighborhood` | `basics.hpp` |
| `old` | `OldValue` | `basics.hpp` |
| `nbr_uid` | `NbrUid` | `basics.hpp` |
| `oldnbr` | `OldNbr` | `basics.hpp` |
| `align` | `Align` | `basics.hpp` |
| `align_inplace` | `AlignInplace` | `basics.hpp` |
| `mod_other` | `ModOther` | `basics.hpp` |
| `split` | `Split` | `basics.hpp` |
| `fold_hood` | `FoldHood` | `basics.hpp` |
| `count_hood` | `CountHood` | `basics.hpp` |
| `spawn` | `Spawn` | `basics.hpp` |
| `min_hood` | `MinHood` | `utils.hpp` |
| `max_hood` | `MaxHood` | `utils.hpp` |
| `sum_hood` | `SumHood` | `utils.hpp` |
| `mean_hood` | `MeanHood` | `utils.hpp` |
| `all_hood` | `AllHood` | `utils.hpp` |
| `any_hood` | `AnyHood` | `utils.hpp` |
| `list_hood` | `ListHood` | `utils.hpp` |
| `abf_distance` | `AbfDistance` | `spreading.hpp` |
| `abf_hops` | `AbfHops` | `spreading.hpp` |
| `bis_distance` | `BisDistance` | `spreading.hpp` |
| `flex_distance` | `FlexDistance` | `spreading.hpp` |
| `broadcast` | `Broadcast` | `spreading.hpp` |
| `bis_ksource_broadcast` | `BisKsourceBroadcast` | `spreading.hpp` |
| `gossip` | `Gossip` | `collection.hpp` |
| `gossip_min` | `GossipMin` | `collection.hpp` |
| `gossip_max` | `GossipMax` | `collection.hpp` |
| `gossip_mean` | `GossipMean` | `collection.hpp` |
| `sp_collection` | `SpCollection` | `collection.hpp` |
| `mp_collection` | `MpCollection` | `collection.hpp` |
| `wmp_collection` | `WmpCollection` | `collection.hpp` |
| `list_idem_collection` | `ListIdemCollection` | `collection.hpp` |
| `list_arith_collection` | `ListArithCollection` | `collection.hpp` |
| `follow_target` | `FollowTarget` | `geometry.hpp` |
| `follow_path` | `FollowPath` | `geometry.hpp` |
| `follow_track` | `FollowTrack` | `geometry.hpp` |
| `rectangle_walk` | `RectangleWalk` | `geometry.hpp` |
| `random_rectangle_target` | `RandomRectangleTarget` | `geometry.hpp` |
| `neighbour_elastic_force` | `NeighbourElasticForce` | `geometry.hpp` |
| `neighbour_gravitational_force` | `NeighbourGravitationalForce` | `geometry.hpp` |
| `neighbour_charged_force` | `NeighbourChargedForce` | `geometry.hpp` |
| `line_elastic_force` | `LineElasticForce` | `geometry.hpp` |
| `plane_elastic_force` | `PlaneElasticForce` | `geometry.hpp` |
| `point_elastic_force` | `PointElasticForce` | `geometry.hpp` |
| `point_gravitational_force` | `PointGravitationalForce` | `geometry.hpp` |
| `diameter_election` | `DiameterElection` | `election.hpp` |
| `diameter_election_distance` | `DiameterElectionDistance` | `election.hpp` |
| `color_election` | `ColorElection` | `election.hpp` |
| `color_election_distance` | `ColorElectionDistance` | `election.hpp` |
| `wave_election` | `WaveElection` | `election.hpp` |
| `wave_election_distance` | `WaveElectionDistance` | `election.hpp` |
| `constant` | `Constant` | `time.hpp` |
| `constant_after` | `ConstantAfter` | `time.hpp` |
| `counter` | `Counter` | `time.hpp` |
| `delay` | `Delay` | `time.hpp` |
| `round_since` | `RoundSince` | `time.hpp` |
| `time_since` | `TimeSince` | `time.hpp` |
| `timed_decay` | `TimedDecay` | `time.hpp` |
| `exponential_filter` | `ExponentialFilter` | `time.hpp` |
| `shared_clock` | `SharedClock` | `time.hpp` |
| `shared_decay` | `SharedDecay` | `time.hpp` |
| `shared_filter` | `SharedFilter` | `time.hpp` |
| `toggle` | `Toggle` | `time.hpp` |
| `toggle_filter` | `ToggleFilter` | `time.hpp` |
