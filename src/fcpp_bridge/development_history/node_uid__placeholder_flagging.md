# DSL vs. Real FCPP C++ API — Manual Review Targets

**Created:** 2026-05-28  
**Last updated:** 2026-05-28 (v1.9 Step A — `receiver_uid = broadcast(...)` added §1; `frozenset`→`set_t` §3.3 and `min_hood` tuple→`make_tuple` §3.5 resolved in transpiler)  
**Scope:** Everything in the Python DSL that simplifies, approximates, or silently
deviates from real FCPP C++ behavior.  Each item below is a target for manual inspection
before any generated C++ code is used in production or safety-critical contexts.

> **v1.6 update:** `self_uid()` has been added to the transpiler and DSL layer.
> `self_uid()` → `node.uid` in generated C++ (no CALL counter).  Items marked
> ✅ below are resolved; items marked ⚠️ remain outstanding.  See §1.4 for details.

---

## Table of Contents

1. [The `node.uid` Placeholder Problem](#1-the-nodeuid-placeholder-problem)
2. [The CALL-Counter Alignment Constraint](#2-the-call-counter-alignment-constraint)
3. [Other DSL Simplifications Away from Real C++ API](#3-other-dsl-simplifications-away-from-real-c-api)
4. [Quick Manual-Review Checklist](#4-quick-manual-review-checklist)

---

## 1. The `node.uid` Placeholder Problem

### What `node.uid` is in FCPP C++

In FCPP, every device in the network has a unique integer identifier accessible as
`node.uid` (type: `device_t`, typically `uint32_t`).  It is available inside the
`AGGREGATE_TEMPLATE(main)` function and any helper called from it.

`node.uid` is used in:

| C++ usage | Purpose |
|---|---|
| `set_t{node.uid}` | local value in `sp_collection` / `mp_collection` routing sets |
| `node.nbr_uid()` | UID of each neighbor (used to find spanning-tree parent) |
| `spawn` key | unique per-sender message identifier |
| `node.uid == source_id` | endpoint/source flag check at initialisation |
| `node.uid % N` | role assignment, partitioning, hashing |

### Why the Python DSL cannot express `node.uid` directly

Neither `initial_state()` nor `compute()` has any parameter that provides the local
node's UID.  The Python class is instantiated once and used as a template — there is
no `node` object on the Python side.

`nbr_uid()` IS a recognised primitive (`nbr_uid(CALL)` in C++) but it yields a *field*
of neighbor UIDs, not the local node's own UID.

### What the Python DSL does (v1.6 and later)

**v1.6** added `self_uid()` as a DSL primitive that transpiles to `node.uid` in C++.
In the Python execution layer `self_uid()` returns `0` (placeholder), but generated C++
is correct.  Examples updated to v1.6 use `self_uid()` in place of hard-coded `0`.

**Affected call sites (status as of v1.6):**

| Example | DSL expression | C++ target | Status |
|---|---|---|---|
| `message_dispatch.py` | `sp_collection(ds, frozenset({0}), ...)` | `sp_collection(CALL, ds, set_t{node.uid}, ...)` | ⚠️ still `0` |
| `message_dispatch.py` | `min_hood((nbr(ds), 0))` | `min_hood(CALL, make_tuple(…, node.nbr_uid()))` | ⚠️ still `0` |
| `message_dispatch.py` | spawn key `(from_id, to_id)` uses `0` | `(node.uid, target_uid)` | ⚠️ still `0` |
| `worker_role_assignment.py` | `sp_collection(d, frozenset({self_uid()}), ...)` | `sp_collection(CALL, d, set_t{node.uid}, ...)` | ✅ fixed v1.6 |
| `worker_role_assignment.py` | `min_hood((nbr_dists, self_uid()))` | `min_hood(CALL, {nbr_dists, node.uid})` | ✅ fixed v1.6 |
| `worker_role_assignment.py` | spawn key `(self_uid(), receiver_uid)` | `(node.uid, receiver_uid)` | ✅ both sender and receiver fixed (v1.9 Step A) |

### Consequences in generated C++

1. **`sp_collection` routing sets are wrong**: every node contributes `{0}` instead of
   its own UID.  All routing sets become `{0}` after the first round.  The routing
   logic (`sender ∈ below`) never fires correctly because the real sender UID is never
   in any `below` set.

2. **`spawn` processes are not unique per sender**: the key `(0, 0)` is the same for
   every endpoint node.  FCPP's spawn mechanism deduplicates by key, so only one
   message process can exist across the entire network at a time.  All endpoint nodes
   overwrite each other's messages.

3. **Spanning-tree tie-breaking is broken**: `min_hood((nbr_dists, 0))` picks the
   minimum distance correctly, but the UID component is always `0`.  In C++, the UID
   is used to break ties when two neighbors have equal distance.  With all UIDs as `0`,
   tie-breaking is undefined.

4. **Role assignment from `initial_state()` is impossible**: `initial_state()` returns
   a fixed default state; it has no access to `node.uid`.  In the demo simulation, roles
   are assigned externally (`role = nid % 8`) and injected into the initial state.  In
   generated C++, the initial state will always be the default (e.g., `role = 0 =
   UNASSIGNED`).  Role assignment must be done via tag-based initialisation in C++.

### Fix options / status

| Option | Effort | Status |
|---|---|---|
| Add `self_uid()` DSL primitive → `node.uid` in C++ | Medium | ✅ **Done in v1.6** — `python_dsl/primitives/self_uid.py` + `visit_Call` special case |
| Distribute receiver_uid via `broadcast` from RECEIVER | Low-Medium | ✅ **Done in v1.9 Step A** — `receiver_uid = broadcast(is_receiver, self_uid())` added as step 5 in `worker_role_assignment.py`; spawn key changed from `(self_uid(), 0)` to `(self_uid(), receiver_uid)` |
| Pass UID as part of initial state via FCPP tag dispatch | Medium-High | ⚠️ Outstanding — C++ side work required |
| Set role via C++ configuration header (not DSL) | Low | ⚠️ Outstanding — valid for fixed topologies |

---

## 2. The CALL-Counter Alignment Constraint

### What the CALL counter is

Inside `AGGREGATE_TEMPLATE(main)`, every FCPP aggregate primitive call is passed the
`CALL` macro.  `CALL` expands to an expression that includes an internal counter:

```cpp
// Conceptually (simplified):
#define CALL (node, ++call_counter)
```

The counter increments once per primitive call, in the order the calls appear in the
code.  FCPP uses this counter to index into the per-node communication buffers: `nbr()`
at counter value 3 reads the value that the *neighbor* sent in *its* counter-value-3
`nbr()` call.

### The alignment requirement

**All nodes must call every aggregate primitive in the same order and the same number
of times, every round.**

If node A's code path calls: `nbr(a)` [counter=1], `nbr(b)` [counter=2]  
And node B's code path calls: `nbr(b)` [counter=1], `nbr(a)` [counter=2]  
Then node A's counter-1 read returns node B's `b` (expected: B's `a`) — a silent
misread with no runtime error.

### What the Python DSL transpiler does and does NOT check

The transpiler converts Python statements to C++ statements one-to-one.  It **does
not** analyse whether aggregate primitives appear inside conditional branches.

This means the following patterns in `compute()` are **silently dangerous**:

```python
# WRONG — only SOME nodes call nbr(x):
if is_source:
    d = bis_distance(is_source, 1, 100)   # noqa: F821
    x = nbr(d)                             # noqa: F821

# WRONG — variable-iteration loop over a primitive:
for i in range(some_field):               # some_field differs per node
    total += nbr(something)               # noqa: F821

# WRONG — primitive inside match/case:
match role:
    case 2:
        scan = count_hood()               # noqa: F821  # only LIDAR nodes call this
```

All three patterns generate **valid C++ that compiles without errors** but produces
**incorrect results at runtime** due to CALL-counter desynchronisation.

### The safe pattern

All aggregate primitives must appear in the "flat" section of `compute()`, before any
branching that depends on per-node data:

```python
def compute(self, self_state, neighbors):
    # ── SAFE: all primitives called unconditionally ──────────────────────────
    d    = bis_distance(is_receiver, 1, 100)  # noqa: F821
    nd   = nbr(d)                              # noqa: F821
    nc   = count_hood()                        # noqa: F821
    rs   = sp_collection(d, frozenset({0}), frozenset(), lambda x, y: x | y)  # noqa
    msgs = spawn(lambda m: (...), new_msg)     # noqa: F821
    log  = old({}, lambda prev: ...)           # noqa: F821

    # ── SAFE: match/case contains only local expressions ─────────────────────
    match self_state.role:
        case 0:
            return MyState(x=d, y=0, z=0)
        case 1:
            return MyState(x=0.0, y=len(rs), z=len(log))
        ...
```

### Loops are only safe with a fixed, node-independent bound

```python
# SAFE — n is a constant, same at every node:
for i in range(10):
    total += nbr(something)   # noqa: F821

# DANGEROUS — n comes from per-node state:
for i in range(self_state.count):  # different per node → misalignment
    total += nbr(something)        # noqa: F821
```

The transpiler emits `for (int i = 0; i < n; ++i)` and cannot distinguish between
these two cases.

### Summary table

| Pattern | C++ validity | Runtime correctness |
|---|---|---|
| Primitives in flat section before any branch | ✅ valid | ✅ correct |
| Primitives inside `if` branch | ✅ valid | ❌ misaligned |
| Primitives inside `match/case` | ✅ valid | ❌ misaligned |
| Primitives in `for range(CONSTANT)` | ✅ valid | ✅ correct |
| Primitives in `for range(variable)` | ✅ valid | ❌ misaligned |
| Local-only computation inside branch | ✅ valid | ✅ correct |

---

## 3. Other DSL Simplifications Away from Real C++ API

### 3.1 `node.current_time()` — simulated time is unavailable

**C++ usage**: `node.current_time()` returns the current simulated time as a `double`
(seconds).  Used in `spawn` (delivery timestamp), message injection scheduling
(`if current_time() > 10 && current_time() < 50`), and time-decay computations.

**Python DSL**: unavailable.  Examples substitute `0` or `0.0`.  The demo simulations
use `round_num` directly as a time proxy.

**Review target**: any generated C++ that needs real time semantics (message injection
windows, timed decay, round-since conditions) will produce static `0` timestamps.

---

### 3.2 `node.next_real()` / `node.next_int()` — deterministic RNG is unavailable

**C++ usage**: FCPP provides `node.next_real()` (uniform [0,1]) and
`node.next_int()` for reproducible, per-node random numbers that are consistent across
simulation runs with the same seed.

**Python DSL**: Python-side `random` module is used in `initial_state()` or the demo
simulation, but not in the generated C++.  Any randomness in `compute()` that calls
`random` is not transpiled — it appears as a Python call that the transpiler will pass
through verbatim, producing invalid C++.

**Review target**: ensure no `random.uniform()`, `random.randint()` etc. appear inside
`compute()` in any example intended for transpilation.

---

### 3.3 `sp_collection` / `mp_collection` — `frozenset` is not a C++ type

✅ **Resolved in v1.9 Step A** — `PythonAstVisitor.visit_Call` now handles `frozenset`:
- `frozenset({x})` → `set_t{x}`
- `frozenset()` → `set_t{}`

**C++ usage**:
```cpp
set_t below = sp_collection(CALL, ds, set_t{node.uid}, set_t{},
    [](set_t x, set_t const& y){ x.insert(y.begin(),y.end()); return x; });
```
where `set_t = std::unordered_set<device_t>`.

**Python DSL** (examples updated to v1.6+ use `self_uid()` already):
```python
routing_set = sp_collection(
    dist_to_receiver,
    frozenset({self_uid()}),   # → set_t{node.uid} ✅
    frozenset(),               # → set_t{} ✅
    lambda x, y: x | y,       # → [=](auto x, auto y){ return (x | y); }
)
```

**Remaining review target**: the lambda `x | y` generates `(x | y)` in C++.  For
`set_t` this requires a `|` operator overload; the correct FCPP idiom is the
`insert(begin, end)` form shown above.  This lambda body is not auto-fixed.

---

### 3.4 `spawn` status integers vs. C++ `status` enum

**C++ usage**:
```cpp
status s = node.uid == m.to ? status::terminated_output :
           inpath            ? status::internal          :
                               status::border;
```

**Python DSL**:
```python
STATUS_BORDER     = 0
STATUS_INTERNAL   = 1
STATUS_TERMINATED = 2
```

The Python integers work correctly in the Python simulation.  In the generated C++,
the transpiler emits integer literals `0`, `1`, `2` rather than `status::border`,
`status::internal`, `status::terminated_output`.

**Review target**: the C++ `status` enum values must match these integers exactly.  If
FCPP changes the enum ordering, the routing logic silently inverts.  Replace integer
literals with the correct enum names in the generated C++.

---

### 3.5 `min_hood` with tuple — `make_tuple` is missing

✅ **Partially resolved in v1.9 Step A** — `PythonAstVisitor.visit_Call` now detects a
single `ast.Tuple` argument to `min_hood` / `max_hood` and emits `std::make_tuple(...)`.

**C++ usage**:
```cpp
device_t parent = get<1>(
    min_hood(CALL, make_tuple(nbr(CALL, ds), node.nbr_uid())));
```

**Python DSL** (after Step A transpiler fix):
```python
parent = min_hood((nbr_dists, self_uid()))   # noqa: F821
# now transpiles to: min_hood(CALL, std::make_tuple(nbr_dists, node.uid))  ✅
```

**Remaining manual post-step**: when the call-site uses a *component* of the tuple
result (e.g., extracting the UID for routing decisions), add `std::get<N>(parent)` in
the generated C++ by hand.  This cannot be automated without type inference.


---

### 3.6 Lambda capture semantics mismatch

**C++ output** (transpiler emits):
```cpp
[=](auto x, auto y) { return (x | y); }
```

The `[=]` captures all referenced variables **by value at the point the lambda is
defined**.

**Python semantics**: Python lambdas capture by reference (closure); mutations to
captured variables after the lambda definition are visible inside the lambda.

In practice this does not cause issues in FCPP because:
1. Lambdas are passed immediately to a primitive and called within the same round
2. No mutation of captured variables occurs after lambda definition in any existing example

**Review target**: if a future example captures a variable and mutates it before the
lambda is invoked, the C++ `[=]` copy and the Python reference closure will diverge.

---

### 3.7 `is_source` / `is_receiver` flags — cannot be set from `initial_state()`

**C++ pattern**:
```cpp
bool is_src = (node.uid == source_id);
```
This is computed fresh every round directly from `node.uid`.

**Python DSL**: `initial_state()` returns a fixed default.  In the examples, the flag
is set externally in the demo simulation:
```python
states[i] = WorkerState(role=(i % 8))   # demo sets role at startup
```

In generated C++, `initial_state()` returns the zero-valued default for every node
(e.g., `role = 0 = UNASSIGNED`).  The C++ binary will therefore need a separate
mechanism to inject per-device initial state — either via FCPP tag initialisation, a
config file, or command-line arguments.

---

### 3.8 Node position — implicit in FCPP, explicit in Python demos

**FCPP C++**: each node has a physical position managed by the simulation framework.
`rectangle_walk`, `follow_target`, and other geometry primitives modify this implicit
position.  The position is NOT part of the user state struct.

**Python DSL + demo**: the demo simulations maintain an explicit `positions` dict.
The aggregate class state does not include position.

This is correct behavior: geometry primitives in the generated C++ will operate on the
framework-managed position just as expected.  However, if any Python example explicitly
stores position in the state dataclass and the transpiler includes it in the C++ struct,
the position would be doubly tracked — once by the framework and once by user state.

**Review target**: ensure the state dataclass in any aggregate class does NOT include
explicit position fields (x, y, z).  Let FCPP manage position implicitly.

---

### 3.9 `for range(variable)` and `while` — loop bodies with primitives

The DSL guide explicitly notes that while loops are "rarely idiomatic" in aggregate
programs (§6.5) and that `for` only supports `range()` (§6.6).  Neither warns about
the CALL-counter hazard when the loop count varies per node (see §2 above).

The transpiler will translate `for i in range(self_state.some_count):` into:
```cpp
for (int i = 0; i < self_state.some_count; ++i) { ... }
```
with no warning.  If any aggregate primitive is called inside this loop and
`some_count` differs across nodes, the CALL counter desynchronises.

---

### 3.10 `old()` default value is used only on round 0

**C++ semantics**:
```cpp
auto r = old(CALL, default_value, [&](T prev) { return updated; });
```
`prev` equals `default_value` on round 0 and `updated` from round N on round N+1.

**Python DSL**: the same semantics hold, and the transpiler correctly emits this form.

**Review target**: not a bug, but reviewers should confirm that the default value is
the correct empty/zero state for round 0 (e.g., `{}` for a map, `0` for a counter).
A wrong default silently seeds the persistent state incorrectly.

---

## 4. Quick Manual-Review Checklist

Use this checklist when inspecting any generated `.cpp` file before compilation or
deployment:

- [ ] Replace every `frozenset({0})` → `set_t{node.uid}`; every `frozenset()` → `set_t{}`
- [ ] Replace spawn key placeholder `(0, 0)` → `(node.uid, actual_receiver_uid)`
- [ ] Replace `min_hood((nbr_field, 0))` → `min_hood(CALL, std::make_tuple(nbr_field, node.nbr_uid()))` and extract UID with `std::get<1>(...)`
- [ ] Replace `STATUS_BORDER = 0`, `STATUS_INTERNAL = 1`, `STATUS_TERMINATED = 2` integer literals → `status::border`, `status::internal`, `status::terminated_output`
- [ ] Verify no aggregate primitive (`nbr`, `old`, `spawn`, `bis_distance`, `sp_collection`, `fold_hood`, etc.) appears inside an `if`, `switch/case`, or variable-count loop body
- [ ] Verify `initial_state()` default values match what the C++ framework will use on round 0; add C++ tag-based initialisation for any per-device values (role, source flag, UID-dependent state)
- [ ] Verify state dataclass does NOT include x/y/z position fields (let FCPP manage position implicitly)
- [ ] Verify no Python `random.*` calls appear inside `compute()` — replace with `node.next_real()` / `node.next_int()` in C++
- [ ] Verify `node.current_time()` is substituted wherever delivery timestamps or time-window conditions were approximated with `0` or `round_num`
- [ ] Check all lambda captures: if any captured variable is mutated after lambda definition, the C++ `[=]` capture-by-value will diverge from Python reference semantics
