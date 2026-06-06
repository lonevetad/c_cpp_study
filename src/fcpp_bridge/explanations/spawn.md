# `spawn` — Reference Manual

## Quick Reference

**C++ signature** (defined in `fcpp/src/lib/coordination/basics.hpp`):

```cpp
spawn(node, call_point, process, key_set, xs...)
  -> std::unordered_map<K, R>
```

- `key_set` — a set of values of type `K` (the "keys")
- `process` — a callable `(K, xs...) -> tuple<R, B>` where `R` is the result and `B` is a status
- `xs...` — extra arguments forwarded to every `process` call

**Python DSL (fcpp_bridge):**

```python
results = spawn(lambda key: (payload, status_code), key_or_option)
# returns dict[K, R] — only output-flagged entries
```

Status codes in the Python DSL (from `fcpp_bridge.examples._example_utils`):

```python
SPAWN_STATUS_BORDER     = 0   # fcpp::status::border
SPAWN_STATUS_INTERNAL   = 1   # fcpp::status::internal
SPAWN_STATUS_TERMINATED = 2   # fcpp::status::terminated_output
```

**Status codes (full table):**

| Code | Propagation | In returned map |
|---|---|---|
| `border` | Not propagated | `bool`/`field<bool>` only |
| `internal` | Propagated to neighbours | `bool`/`field<bool>` only |
| `terminated` | Sends kill signal | `bool`/`field<bool>` only |
| `border_output` | Not propagated | ✓ |
| `internal_output` / `output` | Propagated | ✓ |
| `terminated_output` | Sends kill signal | ✓ |

With `bool`/`field<bool>`: `true` = `internal_output`, `false` = `border_output`.

**FUN_EXPORT:**

```cpp
using my_spawn_t = export_list<spawn_t<K, B>, /* exports of process body */>;
```

**Critical facts:**
- Key is **immutable** for the process lifetime; evolving state → `old`/`nbr` inside the body, or a second spawn
- `bool` status → **ALL** processed keys in returned map; `status` → only `*_output` keys
- Result appears on the node that returned `*_output`, **not** necessarily the injector
- Termination is a **wave** (1 hop/round from T toward I); border nodes stop naturally, not via the wave
- `message_dispatch.hpp` is **one-way only** — NOT a request-reply model
- Discarding the return value is safe — `unordered_map` destructor, no heap leak

---

## 1. Process Identity — Keys

### What a key is

A key is the **identity of one independent aggregate process instance**. `spawn` lets many logically distinct sub-computations
run concurrently on the same network, each identified by its key. You can think of keys the same way you would think of process
IDs in an OS: each key owns its own trace slot, so the `old`/`nbr` state inside `process` is completely isolated per
key — different keys never read each other's exports.

This isolation is enforced at the trace level:

```cpp
internal::trace_key trace_process(node.stack_trace, common::hash_to<trace_t>(k));
```

Each key `k` pushes a distinct hash onto the trace stack before running `process(k, ...)`, so the FCPP runtime treats each
`(call_point, key)` pair as a separate history.

### Key type requirements

`spawn` stores its active-key bookkeeping in an `std::unordered_set<K>` (or `std::unordered_map<K, status>`), so a valid key type
`K` must provide:

1. **Equality** — `operator==`
2. **Hash** — `std::hash<K>` specialisation (or `fcpp::common::hash<K>`)
3. **Serialisation** — a `serialize(S&)` method (both const and non-const) so the key set can be exchanged in FCPP messages

### Injecting keys via `common::option`

A node originates a new process instance only when it has something to inject. The idiomatic pattern is `common::option<K>` (FCPP's optional), which is empty most rounds and filled only when the node decides to start a process:

```cpp
common::option<K> key;
if (condition_to_originate)
    key.emplace(/* construct key */);

spawn(CALL, [&](K const& k) { ... }, key);
```

`common::option<K>` satisfies the `key_set` requirement because FCPP treats it as a 0-or-1 element set: when empty no new process is started; when filled exactly one key is injected this round.

---

### Style 1 — `device_t` key (`es_01.hpp`)

The simplest case: the key **is** the originating node's UID. The process body receives it back as `k` and uses it to rebuild the gradient.

```cpp
common::option<device_t> key;
if (isSpecial)
    key.emplace(node.uid);          // this node originates a wave keyed by its own UID

std::unordered_map<device_t, unit> res = spawn(CALL,
    [&](device_t const& k) {
        // k == UID of the special node that started this wave
        status s = abf_distance(CALL, node.uid == k) < MAX_RANGE
                   ? status::internal_output : status::external;
        return make_tuple(unit{}, s);
    }, key);

// FUN_EXPORT
spawn_t<device_t, status>
```

---

### Style 2 — Custom struct key (`message_dispatch.hpp`)

When the key must carry richer identity, define a struct with the three required pieces.
`message_dispatch.hpp` routes point-to-point messages; the key is the message itself:

```cpp
struct message {
    device_t from;
    device_t to;
    times_t  time;

    bool operator==(message const& m) const { return from==m.from && to==m.to && time==m.time; }

    size_t hash() const {
        constexpr size_t offs = sizeof(size_t)*CHAR_BIT/3;
        return (size_t(time) << (2*offs)) | (size_t(from) << offs) | size_t(to);
    }

    template <typename S> S& serialize(S& s)       { return s & from & to & time; }
    template <typename S> S& serialize(S& s) const { return s << from << to << time; }
};

namespace std {
    template <> struct hash<message> {
        size_t operator()(message const& m) const { return m.hash(); }
    };
}
```

The process body uses all three fields to make routing decisions:

```cpp
map_t r = spawn(CALL, [&](message const& m) {
    bool inpath = below.count(m.from) + below.count(m.to) > 0;
    status s = node.uid == m.to ? status::terminated_output :
               inpath            ? status::internal          : status::border;
    return make_tuple(node.current_time(), s);
}, current_message);   // common::option<message>

// FUN_EXPORT
spawn_t<message, status>
```

The key uniquely identifies "the message from `from` to `to` created at `time`", so separate concurrent deliveries never collide.

---

### Style 3 — `fcpp::tuple` key (compound identity, zero boilerplate)

When no named fields are needed, `fcpp::tuple<...>` gives compound keys immediately.
`fcpp::common::hash` already handles any tuple of hashable types, and `fcpp::tuple` already implements `serialize`,
so **no struct definition, no `std::hash` specialisation is needed**:

```cpp
// Key = (requester UID, target UID)
// Identifies "the query started by node A asking for data about node B"
using query_key_t = fcpp::tuple<device_t, device_t>;

common::option<query_key_t> key;
if (wants_to_query)
    key.emplace(make_tuple(node.uid, target_node));

auto results = spawn(CALL, [&](query_key_t const& k) {
    device_t requester = get<0>(k);
    device_t target    = get<1>(k);
    bool found = (node.uid == target);
    status s   = found                          ? status::terminated_output :
                 on_path_to(requester, target)   ? status::internal          : status::border;
    return make_tuple(node.position(), s);
}, key);

// FUN_EXPORT
spawn_t<query_key_t, status>
```

---

### When to use each style

| Style | Use when |
|---|---|
| `device_t` | one process per originating node; identity is just the UID |
| Custom struct | key has several semantically distinct fields; named members improve readability |
| `fcpp::tuple<...>` | compound identity, no need for named fields; fastest to write |

---

### Minimum required interface for a custom key type

```cpp
bool operator==(K const&) const;                     // equality
size_t hash() const;                                  // internal hash helper
template <typename S> S& serialize(S& s);             // deserialise (input)
template <typename S> S& serialize(S& s) const;       // serialise   (output)

// plus one of:
namespace std { template<> struct hash<K> { size_t operator()(K const&) const; }; }
// or: fcpp::common::hash<K> specialisation
```

---

## 2. Round Execution, Propagation, and Termination

### Step-by-step round

```
Round N on a given node:

1. Collect keys
   own key_set  ∪  keys propagated by all neighbours
         ↓
   full set "ky" of keys this node will run

2. For each key k in ky:
       (result, status) = process(k, xs...)

3. Based on status:
   ┌──────────────────────────────────────────────────────┐
   │ internal        → propagate k to neighbours          │
   │ border          → do NOT propagate k                 │
   │ terminated      → send termination signal, then stop │
   │ *_output suffix → also include result in return map  │
   └──────────────────────────────────────────────────────┘

4. Export propagated keys to neighbours via nbr_context

5. Return unordered_map<K, R>  (only output-flagged keys)
```

### The three status flavours

| `B` type      | Meaning                                                     | Typical use               |
| ------------- | ----------------------------------------------------------- | ------------------------- |
| `bool`        | `true` = `internal_output`, `false` = `border_output`       | simple yes/no propagation |
| `field<bool>` | per-neighbour propagation flag                              | asymmetric spreading      |
| `status`      | full control: `internal`, `border`, `terminated`, `+output` | fine-grained lifecycle    |

```
terminated        — process ending; propagate termination signal to neighbours
border            — part of the process, but do not expand to new neighbours
internal          — part of the process; propagate to neighbours
*_output suffix   — same as above, but also include this node's result in the return map
output            — synonym for internal_output
```

### Wave propagation — mental model

Imagine a query propagating through the network, initiated by one or more nodes:

```cpp
spawn(CALL,
    [&](device_t initiator, ...) -> tuple<double, status> {
        // this body runs independently for EACH key = initiator
        double my_result = ...;
        bool still_alive = ...;
        return {my_result, still_alive ? status::internal_output
                                       : status::terminated};
    },
    my_initiated_queries   // keys this node is starting this round
);
```

- Node 3 adds key `7` to `my_initiated_queries` — it starts a sub-computation with ID 7.
- Node 3's neighbours see key `7` in its exports next round and also run `process(7, ...)`.
- The wave spreads as long as nodes return `internal`; it stops when they return `terminated`.
- Results for key `7` appear in the returned map only on nodes that returned an `_output` status.

Each key is a completely independent wave with its own `old`/`nbr` history — that isolation is the entire point of keys.

### Termination propagation in depth

No, the process **does not stop instantly** across the network when one node returns `terminated` (or `terminated_output`). Termination is a wave that propagates hop-by-hop from the terminating node back toward the injector. Internal nodes continue running the process body for approximately `distance_to_terminator` additional rounds; border nodes stop naturally when their internal neighbours stop propagating the key — the explicit `terminated` signal never enters the border fringe.

#### The mechanics (status overload)

The `status` overload in `basics.hpp` splits neighbour exports into two sets each round:

```cpp
for (auto const& m : fcpp::details::get_vals(ctx.nbr({})))
    for (auto const& k : m) {
        if (k.second == status::terminated)
            kn.insert(k.first);   // "kill" set
        else
            ky.insert(k.first);   // "run" set
    }
```

- **`ky`** — keys this node will (potentially) run: own `key_set` + any key a neighbour exported as non-`terminated`.
- **`kn`** — keys to suppress: any key a neighbour exported as exactly `status::terminated`.

The run loop then is:

```cpp
for (K const& k : ky)
    if (kn.count(k) == 0) {
        // run the process body normally
    } else {
        km.emplace(k, status::terminated);  // skip body, forward termination
    }
```

Two rules follow directly:

1. **A node skips the body and forwards `terminated` only when K is in BOTH `ky` and `kn`.**
   If `terminated` arrives from a neighbour but K is not in `ky` (no non-terminated neighbour, not self-injecting), the node drops K entirely. The signal does not cascade further from that point.

2. **Border nodes never forward `terminated`.**
   A border node's export is empty for K (returning `border` means K is not added to `km`). Neighbours beyond the border never have K in their `ky` from that direction, so they never enter the `terminated`-forwarding path.

#### Round-by-round trace for `I → A → B → T`, with D (border) hanging off B

Assume T's process body always returns `terminated_output`; B, A, I return `internal`.

| Round | T | B | A | I | D (border) |
|---|---|---|---|---|---|
| R   | **terminates** → exports `{K:terminated}` | runs → exports `{K:internal}` | runs → exports `{K:internal}` | runs → exports `{K:internal}` | runs → no export |
| R+1 | sees B's `internal` → ky={K} → runs → exports `{K:terminated}` | sees T's `terminated`+A's `internal` → kn+ky={K} → **skips** → exports `{K:terminated}` | sees B's `internal` → runs → exports `{K:internal}` | sees A's `internal` → runs → exports `{K:internal}` | sees B's `internal` → runs → no export |
| R+2 | sees B's `terminated` → kn={K}, ky={} → **stops** | sees A's `internal`+T's `terminated` → skips → exports `{K:terminated}` | sees B's `terminated`+I's `internal` → kn+ky={K} → **skips** → exports `{K:terminated}` | sees A's `internal` → runs → exports `{K:internal}` | sees B's `terminated` → kn={K}, ky={} → **stops** |
| R+3 | — | sees A's `terminated`, T stopped → ky={} → stops quietly | — | sees A's `terminated`+own key_set → kn+ky={K} → **skips** → exports `{K:terminated}` | — |

Full quiescence at round R + `distance(T, I)` = R + 3.

#### Key observations

**Internal nodes run for `distance_to_T` additional rounds.**
The termination wave travels from T toward the injector at 1 hop per round. A node at distance *d* from T continues executing the process body for *d* more rounds after T terminates.

**The terminating node T continues running until its own neighbours stop.**
T exported `terminated` in round R. Its neighbour B exported `terminated` in R+1. T received B's export in R+2 → T's `ky` became empty → T stopped. T ran for only 1 extra round after round R. In general, T stops ~1 round after its nearest `internal` neighbour stops.

**Border nodes stop when their `ky` empties, not when `terminated` arrives.**
D (border, off B) ran in rounds R and R+1. In R+2 it saw B's `{K: terminated}` → K went to `kn` only, not `ky`. Since D had no other source of K in `ky`, the loop simply skipped K and D stopped without forwarding `terminated`. The termination wave does not cross the border fringe.

**Total extra rounds is bounded by the network diameter.**
Full quiescence takes at most `diameter(graph)` additional rounds (the worst-case distance from T to I).

#### `bool`/`field<bool>` overloads — no explicit termination

These overloads have no `terminated` signal. A node returning `b = false` simply does not propagate K:

```cpp
tie(rm[k], b) = process(k, xs...);
if (b) km.insert(k);              // b = false → k not propagated
```

The wave contracts naturally: once no neighbour propagates K and the node itself does not inject K, K disappears from `ky` and the process stops. There is no explicit kill wave — the process fades out hop by hop, also over ~diameter rounds.

#### Practical implications

- **Stale output rounds**: after `terminated_output` is returned, the result map may still contain entries on intermediate nodes for a few more rounds (nodes that returned `internal_output` on the path, before the wave arrived). Any accumulation logic (`old` outside `spawn`) must tolerate duplicate or trailing results.
- **Re-injection prevents termination**: if the injecting node keeps K in its `key_set` every round, the process can never fully quiesce — K stays in `ky` at the injector. Use `common::option<K>` and inject K only once (guard with `old`).
- **Termination is per-key**: a `terminated` export for key K1 has no effect on key K2. Multiple concurrent processes with different keys are entirely independent.

---

## 3. Working with the Returned Map

`spawn` returns `std::unordered_map<K, R, common::hash<K>>`.
`R` is the first element of the `tuple<R, B>` that `process` returns.

### What ends up in the map — and why it differs by status type

This is a source of subtle bugs: the three overloads behave differently.

| Status type `B` | Keys in the returned map |
|---|---|
| `bool` | **Every key that ran** on this node — regardless of `true`/`false`; the bool only controls propagation |
| `field<bool>` | Same as `bool`: every key that passed the "neighbour has it" gate and ran |
| `status` | **Only keys that returned `*_output`** (`internal_output`, `border_output`, `terminated_output`, `output`) |

With `bool` status the implementation is (from `basics.hpp`):
```cpp
tie(rm[k], b) = process(k, xs...);   // rm[k] always written
if (b) km.insert(k);                  // b only affects propagation
```

With `status` the guard is explicit:
```cpp
if ((char)s >= 4)                     // only output-flagged entries
    rm.emplace(k, std::move(r));
```

So with `status`, a node may participate in a process (routing, forwarding) and still contribute **nothing** to the map — only nodes that explicitly signal `*_output` appear.

---

### Who sees the result?

A key point: the result appears in the map of whichever node returns `*_output` — **not necessarily the node that injected the key**.
Typical patterns:

- In `es_01.hpp` (simple `bool` status) the originating special node sees `res` populated with all its reachable peers, because every key that ran is in the map.
- In `message_dispatch.hpp` (`status`) the **destination** node is the one that returns `terminated_output` and therefore has the entry in `r`. The sender sees nothing in `r` for its own message (it returns `internal` or `border`).

---

### Typical use patterns

#### 1. Detect whether this node has a result for a specific key

```cpp
auto results = spawn(CALL, process, key);
if (results.count(target_key) > 0) {
    // this node is an output node for target_key this round
}
```

#### 2. Read result values (iterate or random-access)

```cpp
// iterate all output entries
for (auto const& [k, v] : results) {
    node.storage(tags::received{}) += v;   // accumulate delivery times, scores, etc.
}

// direct access (only safe after a count() check with 'status'; always valid with 'bool')
times_t delivery_time = results.at(my_key);
```

#### 3. Count processes active on this node

With `bool` status `results.size()` equals the number of process instances that ran on this node this round — useful as a load or spread metric:

```cpp
// es_01.hpp pattern: special node counts peers in range
if (isSpecial) {
    node.storage(special_in_range{}) = (int)res.size() - 1; // subtract self
}
```

#### 4. Persist results across rounds with `old`

When results arrive sporadically (one delivery per process termination), accumulate them:

```cpp
// message_dispatch.hpp pattern
map_t r = spawn(CALL, [&](message const& m){ ... }, current_message);

r = old(CALL, map_t{}, [&](map_t prev) {
    for (auto const& [msg, t] : r) {
        if (prev.count(msg))
            node.storage(repeat_count{}) += 1;  // already delivered
        else {
            node.storage(delivery_count{}) += 1;
            prev[msg] = t;
        }
    }
    return prev;
});
```

The `old` here is keyed on the same call point but lives **outside** `spawn` — it accumulates the per-round snapshots into a persistent delivery ledger.

---

### Safely discarding the return value

Yes, the return value can be discarded with no memory leak.

`std::unordered_map<K, R>` is a value type with a proper destructor. When `spawn` is called without capturing its result:

```cpp
spawn(CALL, process, key_set);   // map constructed, then immediately destroyed — fine
```

the temporary map is destroyed at the semicolon. No heap leak.

Do this whenever the side effects inside `process` are all you need (updating node storage inside the lambda body, setting flags, etc.) and the per-round result values are not required outside `process`.

---

## 4. Protocols — Implementing Request-Reply

### The problem

A **querier** node wants to ask a **data owner** node for some data identified by a key.
The query must propagate to the owner; the owner's reply must propagate back to the querier.
This is a round-trip.

### Why `message_dispatch.hpp` is not a model for this

`message_dispatch.hpp` is **one-way delivery only**.
The spanning tree creates a path from sender to receiver; the destination returns `terminated_output` and the delivery timestamp ends up only in the destination's map — the sender never sees a reply.
It is fire-and-forget, not request-reply.

### Important: the key is immutable per process instance

A `spawn` key is fixed for the entire lifetime of that process instance. You cannot change it between rounds.
State that must evolve across rounds must be tracked via `old`/`nbr` **inside the process body** (each process instance has its own isolated trace slot for those calls). Alternatively, data can be encoded inside the key of a *second* spawn (see Option A below).

---

### Option A — Two spawns (explicit request-reply)

**Spawn 1 — query** (querier → target):

```cpp
using query_key_t = fcpp::tuple<device_t, device_t>;  // (querier_id, target_id)

common::option<query_key_t> query;
if (should_ask && !already_started)
    query.emplace(make_tuple(node.uid, target_id));

auto q_res = spawn(CALL, [&](query_key_t const& k) {
    auto [querier, target] = k;
    real_t d = abf_distance(CALL, node.uid == querier);  // gradient from querier outward
    status s = node.uid == target ? status::terminated_output
             : d < INF            ? status::internal
                                  : status::border;
    return make_tuple(unit{}, s);
}, query);
// Target sees q_res.count(my_key) > 0 — it knows the query arrived
// and has both querier_id and target_id available from the key
```

**Spawn 2 — reply**, data carried **inside the key** (target → querier):

```cpp
using reply_key_t = fcpp::tuple<device_t, vec<2>>;  // (querier_id, snapshot_data)

// Target injects the reply key ONCE when it detects the query
bool reply_started = old(CALL, false, [&](bool prev){ return prev || q_res.count(my_key) > 0; });
common::option<reply_key_t> reply;
if (q_res.count(my_key) > 0 && !reply_started)
    reply.emplace(make_tuple(querier_id, node.position()));  // data snapshot now

auto r_res = spawn(CALL, [&](reply_key_t const& k) {
    auto [querier, data] = k;      // data is in the key — every relay node has it
    real_t d = abf_distance(CALL, node.uid == querier);
    status s = node.uid == querier ? status::terminated_output
             : d < INF             ? status::internal_output  // relay and expose data
                                   : status::border;
    return make_tuple(data, s);    // forward the snapshot unchanged
}, reply);

// Querier reads its answer from r_res
if (r_res.count(my_reply_key) > 0)
    received_data = r_res.at(my_reply_key);
```

Because the data is part of the reply key it is automatically available on every relay node — no `nbr`-based propagation is needed inside the body. The data is a **snapshot** of the target's value at the moment it injected the reply key. Use `old` to prevent the target from re-injecting the reply every round.

---

### Option B — Single spawn, data propagated via `nbr` inside the body

Key = `(querier, target)` — fixed. The process handles both the outbound search and the inbound data return internally:

```cpp
spawn(CALL, [&](query_key_t const& k) {
    auto [querier, target] = k;

    // Outbound routing: gradient from querier
    real_t d_from_querier = abf_distance(CALL, node.uid == querier);

    // Inbound data: target holds the value; others collect it inward via fold_hood
    vec<2> local = (node.uid == target) ? node.position() : vec<2>{};
    real_t d_from_target = abf_distance(CALL, node.uid == target);
    auto [best_data, best_d] = fold_hood(CALL,
        [](auto acc, auto val){ return get<1>(val) < get<1>(acc) ? val : acc; },
        make_tuple(local, d_from_target));
    bool data_known = (node.uid == target) || (best_d < INF);

    status s = (node.uid == querier && data_known) ? status::terminated_output
             : (d_from_querier < THRESHOLD)        ? status::internal
                                                   : status::border;
    return make_tuple(data_known ? get<0>(best_data) : vec<2>{}, s);
}, key);
```

The process naturally transitions from "searching" to "returning" without any external coordination. The querier terminates the process once the data reaches it. Because the data travels via `nbr`, it reflects the **live** value of the target each round (not a snapshot).

---

### Comparison

| | Two spawns | Single spawn |
|---|---|---|
| Clarity | Explicit phases, easier to reason about | Compact, single aggregate process |
| Data delivery | Data in reply key — no `nbr` in body | `nbr`/`fold_hood` inside body |
| FUN_EXPORT | Two `spawn_t<…>` entries | One `spawn_t` + inner `abf_distance_t` + `fold_hood` exports |
| Coordination | Target uses `old` to inject reply once | None — phase transition is internal to the process |
| Latency | 2 wave propagations (query + reply) | 1 wave out + data flows back within same process |
| Data freshness | Snapshot at query-arrival time | Live value each round |

**Recommendation:** for a clear UDP-like "ask and get a snapshot back" protocol, **two spawns** is the cleaner design — the reply key carries the data, making spawn 2's body trivially simple. The single-spawn variant is more FCPP-idiomatic if you want the data to stay live (the querier always sees the current value of the target, not just a snapshot), but the nested exports make `FUN_EXPORT` non-trivial.

---

## 5. Reference

### FUN_EXPORT

```cpp
// K = key type, B = status type (bool, field<bool>, or status)
using my_spawn_t = export_list<spawn_t<K, B>, /* exports of process body */>;
```

`spawn_t<K, B>` covers the key-propagation bookkeeping; you still need to add the export types of whatever `process` does internally (its own `old`/`nbr` calls).
