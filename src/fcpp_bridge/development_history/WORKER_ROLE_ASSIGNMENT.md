# Worker Role Assignment — Example Design & Evolution Notes

## Overview

`examples/worker_role_assignment.py` is an original (non-ported) FCPP Bridge example
that showcases DSL features introduced across v1.4 and v1.6:

| Feature | DSL construct | C++ output |
| ------- | ------------- | ---------- |
| Per-role behavioral dispatch | `match/case` | `switch` |
| Periodic sensor reporting via spawn | `spawn` + `old` | `spawn(CALL, …)` + `old(CALL, …)` |
| Device's own unique identifier | `self_uid()` | `node.uid` (no CALL counter) |
| Communication role classification | `RoleCommunicationType` enum | Python-only (endpoint / receiver / repeater) |

It also demonstrates `bis_distance`, `sp_collection`, `nbr`, `min_hood`, and
`count_hood` — the full spanning-tree routing stack used in `message_dispatch.py`.

---

## Scenario

A heterogeneous swarm operates in a disaster-response setting.
Swarm size is controlled by two constants in the example source:

| Constant | Default | Effect |
| -------- | ------- | ------ |
| `FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS` | `2` | Number of full ROLE_CYCLE repetitions; `DEVICES = len(ROLE_CYCLE) * FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS` |
| `ADDITIONAL_REPEATERS_EACH_CYCLE` | `5` | Extra `WorkerRole.REPEATER` nodes appended to every cycle; tunes relay density |

`ROLE_CYCLE` is a 13-slot tuple (8 standard roles + `ADDITIONAL_REPEATERS_EACH_CYCLE`
extra `REPEATER` entries) used to assign roles via
`ROLE_CYCLE[node_id % len(ROLE_CYCLE)]`.  With the default values `DEVICES = 26`
(2 × 13) and the role counts are:

| Metric | Formula | Default value |
| ------ | ------- | ------------- |
| ENDPOINT-type nodes | `FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS × 5` | 10 |
| RECEIVER-type nodes | `FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS × 1` | 2 |
| REPEATER-type nodes | `FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS × (2 + ADDITIONAL_REPEATERS_EACH_CYCLE)` | 14 |

Invariants satisfied: `REPEATER-type (14) > ENDPOINT-type (10) > RECEIVER-type (2)`.
To guarantee the first invariant holds, `ADDITIONAL_REPEATERS_EACH_CYCLE` must be
greater than 3.

Each node is assigned one of eight *WorkerRole* values:

| Integer | Role name | RoleCommunicationType |
| ------- | --------- | --------------------- |
| 0 | UNASSIGNED | repeater (passive relay candidate; no active sensing) |
| 1 | RECEIVER | receiver |
| 2 | LIDAR | endpoint |
| 3 | INFRARED_SENSOR | endpoint |
| 4 | REPEATER | repeater |
| 5 | TORCHLIGHT_MICROPHONE | endpoint |
| 6 | RUBBLES_REMOVER | endpoint |
| 7 | FLYING_OVERSEER | endpoint |

### RoleCommunicationType

Each `WorkerRole` is associated with a `RoleCommunicationType` that describes its
role in the data-gathering communication flow:

| Type | Integer | Description |
| ---- | ------- | ----------- |
| `ENDPOINT` | 0 | Gathers sensor data from the environment and sends it to RECEIVER |
| `RECEIVER` | 1 | Accumulates and stores reports received from endpoints |
| `REPEATER` | 2 | Relays data between nodes not in direct communication (transitively) |

Role ↔ RoleCommunicationType mapping:
- ENDPOINT roles (2, 3, 5, 6, 7): LIDAR, INFRARED_SENSOR, TORCHLIGHT_MICROPHONE, RUBBLES_REMOVER, FLYING_OVERSEER
- RECEIVER role (1): RECEIVER
- REPEATER roles (0, 4): UNASSIGNED (passive), REPEATER (active)

The `REPEATER` type is analogous to repeater nodes in channel-like algorithms
(`channel_broadcast`, `chain_decaying`, `spreading_collection`) and to intermediary
nodes in IPv4/IPv6 routing: they forward packets without originating them.

Every `MSG_INTERVAL` rounds (default: 10), endpoint nodes (roles 2, 3, 5, 6, 7)
inject a sensor-reading message toward the nearest RECEIVER via spawn.  The demo
simulation uses a random floating-point value to simulate the sensor reading.
RECEIVER nodes accumulate all delivered messages and report a `received_count`
in their state.  Repeater roles (0, 4) do not inject sensor data.

---

## Algorithm (8 steps, all nodes, every round)

All eight steps run at **every** node because FCPP aligns aggregate-primitive
calls via an internal `CALL` counter.  Skipping a primitive on a subset of nodes
would desynchronise the counter and produce incorrect C++ behavior.

| Step | Primitive | Purpose |
| ---- | --------- | ------- |
| 1 | `bis_distance(is_receiver, 1, 100)` | Distance gradient rooted at RECEIVER (WorkerRole.RECEIVER) |
| 2 | `nbr(dist)` + `min_hood((nbr_dists, self_uid()))` | Spanning-tree parent; `self_uid()` as tie-breaker |
| 3 | `count_hood()` | Local neighbor count (coverage metric) |
| 4 | `sp_collection(dist, {self_uid()}, {}, union)` | Routing subtree per node |
| 5 | `broadcast(is_receiver, self_uid())` | Distribute nearest RECEIVER's UID to all nodes |
| 6 | `spawn(lambda, (self_uid(), receiver_uid))` | Route endpoint messages to RECEIVER |
| 7 | `old({}, lambda prev: …)` | Persist received-message map |
| 8 | `match role: case 0: … case _:` | Role-specific task + state assembly |

The `match/case` in step 7 contains **only local expressions** (no primitive
calls) and is therefore safe to use as a per-role customization point.

> **`self_uid()` note:** `self_uid()` does not increment the CALL counter — it
> is a direct field access (`node.uid` in C++), not a coordination primitive.
> It may therefore be called freely inside match/case branches or if/else arms.

---

## DSL Features Demonstrated

### self_uid() → node.uid

```python
# Step 2: tie-breaking by device UID
parent = min_hood((nbr_dists, self_uid()))          # noqa: F821

# Step 4: routing subtree keyed by device UID
routing_set = sp_collection(
    dist_to_receiver,
    frozenset({self_uid()}),   # {this device's UID}   # noqa: F821
    frozenset(),
    lambda x, y: x | y,
)

# Step 5: broadcast nearest RECEIVER's UID to all nodes
receiver_uid = broadcast(is_receiver, self_uid())    # noqa: F821

# Step 6: spawn key — sender UID + discovered receiver UID
new_msg = (self_uid(), receiver_uid) if is_endpoint else None   # noqa: F821
```

Generated C++ (after transpilation):

```cpp
auto parent      = min_hood(CALL, std::make_tuple(nbr(CALL, dist_to_receiver), node.uid));
auto routing_set = sp_collection(CALL, dist_to_receiver,
                      set_t{node.uid}, set_t{}, [=](auto x, auto y) { return (x | y); });
device_t receiver_uid = broadcast(CALL, is_receiver, node.uid);
auto new_msg     = is_endpoint ? std::make_optional(std::make_tuple(node.uid, receiver_uid))
                               : std::nullopt;
```

`self_uid()` does **not** increment the CALL counter (it is a direct node-field
access, not a coordination primitive), so it is safe to use anywhere — including
inside `match/case` branches.

### match/case → C++ switch

```python
match role:
    case WorkerRole.UNASSIGNED.value:   # 0
        # [Placeholder] Await role assignment; passively track position.
        passive_dist = dist_to_receiver
        return WorkerState(role=role, dist_to_receiver=passive_dist,
            routing_set_size=0, received_count=0, active_procs=0)
    case WorkerRole.RECEIVER.value:     # 1
        # Accumulate all delivered endpoint reports.
        messages_received = len(received_log)
        return WorkerState(role=role, dist_to_receiver=0.0,
            routing_set_size=len(routing_set),
            received_count=messages_received, active_procs=len(active_messages))
    case WorkerRole.LIDAR.value:        # 2
        # Endpoint: depth/distance sensor.
        # [Placeholder] Capture depth-map frame; inject compressed scan.
        scan_coverage = neighbor_count
        return WorkerState(role=role, dist_to_receiver=dist_to_receiver,
            routing_set_size=scan_coverage, received_count=0,
            active_procs=len(active_messages))
    …
    case WorkerRole.REPEATER.value:     # 4
        # Repeater: signal amplifier and network range extender.
        # Acts as intermediary between endpoints (or other repeaters) not in
        # direct communication; relays data frames transitively.
        # [Placeholder] Forward data frames; log relay throughput.
        relay_coverage = neighbor_count
        return WorkerState(role=role, dist_to_receiver=dist_to_receiver,
            routing_set_size=relay_coverage, received_count=0,
            active_procs=len(active_messages))
    …
    case WorkerRole.RUBBLES_REMOVER.value:  # 6
        # Endpoint: physical debris-clearing robot.
        # Gathers environmental data and injects a clearing-status report
        # into the spawn stream toward RECEIVER.
        # [Placeholder] Sample debris sensor; encode clearing status.
        debris_coverage = len(routing_set)
        return WorkerState(role=role, dist_to_receiver=dist_to_receiver,
            routing_set_size=debris_coverage, received_count=0,
            active_procs=len(active_messages))
    …
    case WorkerRole.FLYING_OVERSEER.value:  # 7
        # Endpoint: aerial survey drone.
        # [Placeholder] Transmit aerial survey frame; update coverage map.
        survey_footprint = len(routing_set)
        return WorkerState(…)
```

The transpiler converts this directly to a C++ `switch` block with `case N:` /
`default:` labels and `break` after each arm.

The `routing_set_size` field is *repurposed* per role:
- LIDAR (2), REPEATER (4) → `neighbor_count` (scan/relay coverage)
- UNASSIGNED (0)          → `0` (passive repeater; no active metric)
- all others              → `len(routing_set)` (subtree size)

This illustrates how a single state field can carry different semantics per role
without expanding the dataclass.

Each case branch also includes a comment marking the real-world task the role
*would* perform (or a placeholder variable where no real implementation is
provided — this is an exercise example, not a production system).

### broadcast + spawn + old (message routing)

```python
# Step 5: RECEIVER nodes broadcast their own UID outward
receiver_uid = broadcast(is_receiver, self_uid())    # noqa: F821

# Step 6: endpoint nodes inject a message keyed by (sender_uid, receiver_uid)
new_msg = (self_uid(), receiver_uid) if is_endpoint else None

active_messages = spawn(
    lambda msg: (
        0,                             # payload placeholder
        STATUS_TERMINATED if is_receiver                        # 2
        else STATUS_INTERNAL if (msg[0] in routing_set
                                  or msg[1] in routing_set)    # 1
        else STATUS_BORDER,                                     # 0
    ),
    new_msg,
)
received_log = old({}, lambda prev: {**prev, **active_messages})
```

Endpoint nodes (roles 2, 3, 5, 6, 7) inject `(self_uid(), receiver_uid)` as the
spawn key each round.  `self_uid()` provides the real device UID in C++ (`node.uid`),
making each sender's messages unique.  `receiver_uid` is the nearest RECEIVER's UID
discovered via `broadcast` in step 5 — no longer a hardcoded `0` placeholder.
Repeater nodes (roles 0, 4) do not inject messages.

The spawn lambda returns the routing status integer:

| Value | Constant | Meaning |
| ----- | -------- | ------- |
| 2 | `STATUS_TERMINATED` | This node IS the RECEIVER; message arrived |
| 1 | `STATUS_INTERNAL` | This node's routing subtree contains sender or receiver |
| 0 | `STATUS_BORDER` | This node is off-path; process does not execute here |

`old` merges newly delivered messages into the persistent map so `received_count`
never decreases.

---

## Design Decisions

### Why FCPP primitives are all before the switch

In FCPP, the `CALL` macro is an implicit sequence counter.  If `nbr()` or `spawn()`
appeared inside one `case` branch but not others, nodes taking different branches
would increment the counter at different points → misaligned neighbor-field reads
and undefined behavior.

The DSL guide (§6.7) documents this restriction: the `match/case` section should
contain only local, non-aggregate computation.

### Enum-value dotted-name patterns in case labels (v1.8.2)

Python 3.10+ `match/case` distinguishes:
- **Capture patterns** — `case NAME:` binds any value to a new local `NAME`
- **Value patterns** — `case a.b.c:` (any dotted name) evaluates the chain and
  matches the resulting value; never creates a new binding

Bare module-level names like `case RECEIVER:` are capture patterns and always
match — making the switch useless.  A three-part dotted chain like
`case WorkerRole.RECEIVER.value:` is always interpreted as a **value pattern**,
so Python evaluates `WorkerRole.RECEIVER.value` to the integer `1` and matches
against it.  This is the approach used in the example: no magic integer literals,
and the enum class itself is the source of truth.

> **Transpiler support (v1.8.4):** The AST visitor resolves `WorkerRole.X.value`
> chains to integer literals by constant-folding them against the compute function's
> `__globals__`.  Both `case` labels and comparison guards now generate valid C++.

### Role assignment via ROLE_CYCLE (v1.8.1)

`initial_state()` cannot access `node.uid` (the C++ device identifier).  To
assign roles deterministically, the demo simulation populates `roles[nid]` from
`ROLE_CYCLE[nid % len(ROLE_CYCLE)]` externally before the first round.

`ROLE_CYCLE` is a tuple of `WorkerRole` members with two tuning knobs:

| Constant | Type | Effect on the network |
| -------- | ---- | --------------------- |
| `ADDITIONAL_REPEATERS_EACH_CYCLE` | `int` | Extra `WorkerRole.REPEATER` slots appended to each cycle.  Increase for denser relay coverage; keep `> 3` to ensure `REPEATER-type > ENDPOINT-type`. |
| `FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS` | `int` | Number of full `ROLE_CYCLE` repetitions; `DEVICES = len(ROLE_CYCLE) * this`.  Scale up for larger swarms. |

Formulas for derived counts (per-default `ADDITIONAL_REPEATERS_EACH_CYCLE = 5`,
`FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS = 2`):

```
len(ROLE_CYCLE)  = 8 + ADDITIONAL_REPEATERS_EACH_CYCLE       = 13
DEVICES          = len(ROLE_CYCLE) × FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS  = 26
ENDPOINT-type    = FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS × 5   = 10
RECEIVER-type    = FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS × 1   = 2
REPEATER-type    = FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS × (2 + ADDITIONAL_REPEATERS_EACH_CYCLE)  = 14
```

In a real deployment, role assignment could be done via:
1. **Pre-configuration** — write the role into the device's initial memory
2. **Dynamic election** — see [Evolution 2](#evolution-2-dynamic-role-election)

### self_uid() instead of hard-coded 0

Prior to v1.6 the spawn key was `(0, 0)` — a hard-coded placeholder for
`(node.uid, receiver_uid)`.  v1.6 introduces `self_uid()` which transpiles
to `node.uid` in C++, fixing the sender half.  The receiver UID (`0`) is
still a placeholder; distributing it to all nodes requires a `broadcast`
from RECEIVER nodes and is tracked as a known limitation.

The demo simulation has always used the real `nid` directly (it does not call
`compute()`) so the log files are correct regardless of the DSL-layer placeholder.

---

## Known Limitations

| Limitation | Impact | Workaround / Status |
| ---------- | ------ | ------------------- |
| Sender UID was `0` placeholder | ~~All endpoints shared the same spawn key~~ | **Fixed in v1.6** — `self_uid()` → `node.uid` |
| Receiver UID is still `0` placeholder | Spawn key `(node.uid, 0)` is unique per sender but destination is approximate | Distribute real receiver UID via `broadcast` from RECEIVER nodes |
| `sp_collection` uses `frozenset` in Python | Generated C++ needs `std::unordered_set<device_t>` | Replace `frozenset({self_uid()})` with correct C++ type post-generation |
| Role is static after initialization | No in-flight role changes supported | Dynamic assignment requires evolution 2 or pre-configuration |
| Single-interval message injection per endpoint | All 10 endpoints send in the same round; congestion not modeled (default config) | Use staggered intervals or priority queues |

---

## Possible Evolutions

### Evolution 1: Full node.uid routing (sender half done in v1.6)

**v1.6 status:** `self_uid()` has been added to the transpiler.  The spawn key
is now `(self_uid(), 0)` → `(node.uid, 0)` in C++, so each sender's messages
are already unique.

The remaining work is replacing the receiver UID placeholder (`0`):

```python
# Current (v1.6): sender UID is real, receiver UID is placeholder
new_msg = (self_uid(), 0) if is_endpoint else None

# Target: both UIDs are real
# Requires broadcasting receiver_uid from RECEIVER to all nodes first:
#   receiver_uid = broadcast(is_receiver, self_uid())  # Step N (new primitive call)
#   new_msg = (self_uid(), receiver_uid) if is_endpoint else None
```

With both UIDs real, each message is guaranteed unique and the routing
statistics in the logs become fully accurate.

### Evolution 2: Dynamic role election

Instead of static `nid % 8` assignment, use FCPP election primitives:

```python
# Leader election decides who becomes RECEIVER
leader_uid = wave_election(self_state.some_metric)
# Remaining nodes run a second election for other roles
```

The `wave_election` / `color_election` primitives in `election.hpp` provide
distributed consensus without a central coordinator.  This is the correct
approach for a real swarm where nodes have no prior knowledge of each other's IDs.

### Evolution 3: Hierarchical reporting

Add an intermediate relay tier between endpoints and RECEIVER:

```
LIDAR → REPEATER → RECEIVER
INFRARED → RUBBLES_REMOVER → RECEIVER
```

Each relay tier would have its own gradient (`bis_distance` from relay roots) and
a dedicated `spawn` process.  This models real-world mesh topologies where direct
endpoint-to-base connectivity is unlikely.

### Evolution 4: Role-aware routing priority

Allow messages from FLYING_OVERSEER (aerial drone, role 7) to pre-empt lower-priority
messages in congested routing sets.  One approach: use separate spawn processes per
priority level, or add a priority field to the message key tuple `(sender, priority, time)`.

### Evolution 5: Message TTL / expiry

Add a time-to-live counter to each spawn key so messages that fail to reach the
RECEIVER are cleaned up after `MAX_TTL` rounds:

```python
active_messages = spawn(
    lambda msg: (
        0,
        STATUS_TERMINATED if is_receiver or msg[2] <= 0  # TTL expired
        else STATUS_INTERNAL if (msg[0] in routing_set)
        else STATUS_BORDER,
    ),
    (0, 0, MAX_TTL) if is_endpoint else None,
)
```

TTL prevents message accumulation in partitioned networks and is a standard
pattern in real FCPP deployments.

### Evolution 6: Multi-receiver redundancy

The current RECEIVER role is handled by a single node per ID-class.  For
fault-tolerance, extend the algorithm to allow any RECEIVER node to accept
messages from any endpoint:

- `is_receiver` is already defined as `role == WorkerRole.RECEIVER.value` (any node with that role)
- With default constants there are `FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS` RECEIVER nodes (2 by default — one per cycle)
- The `old()` log could be merged across all RECEIVERs via `gossip_max`

### Evolution 7: Visualization integration

Attach a `TextDashboard` or `SwarmVisualizer` to monitor role distribution
and message delivery rate in real time:

```python
from fcpp_bridge.metrics import MetricsCollector
from fcpp_bridge.visualization import create_visualizer

collector = MetricsCollector()
viz = create_visualizer(collector=collector)
viz.start()

# Feed each round's aggregated state as a SwarmSnapshot
```

The `routing_set_size` field (which carries `neighbor_count` for LIDAR/REPEATER
and `subtree_size` for others) makes a useful secondary metric for visualizing
network coverage and routing health.

---

## Files Added / Modified

### v1.5 (initial)

| File | Description |
| ---- | ----------- |
| `examples/worker_role_assignment.py` | Example: 24-node swarm, 8 roles, spawn routing, match/case switch |
| `development_history/WORKER_ROLE_ASSIGNMENT.md` | This file |

### v1.6 (self_uid + enum comments + step 7 task refactor)

| File | Change |
| ---- | ------ |
| `python_dsl/primitives/self_uid.py` | New — `SelfUid` primitive class |
| `python_dsl/primitives/__init__.py` | Added `SelfUid` export |
| `python_dsl/__init__.py` | Added `SelfUid` to top-level exports |
| `transpiler/python_ast_visitor.py` | Added `self_uid()` → `node.uid` mapping (no CALL) |
| `tests/transpiler/test_python_ast_visitor.py` | Added `test_ast_visitor_self_uid` |
| `examples/worker_role_assignment.py` | Use `self_uid()`, enum value comments, step 7 role tasks |
| `development_history/WORKER_ROLE_ASSIGNMENT.md` | This file — v1.6 documentation updates |

### v1.7 (RoleCommunicationType + RIPETITOR→REPEATER + RUBBLES_REMOVER→endpoint)

| File | Change |
| ---- | ------ |
| `examples/worker_role_assignment.py` | Renamed `RIPETITOR` → `REPEATER`; added `RoleCommunicationType` enum + `ROLE_COMM_TYPE` mapping; moved `RUBBLES_REMOVER` from relay to endpoint; updated `ENDPOINT_ROLES`, replaced `RELAY_ROLES` with `REPEATER_ROLES`; updated `is_endpoint`, step 7 cases, demo sensor readings |
| `development_history/WORKER_ROLE_ASSIGNMENT.md` | This file — v1.7 documentation updates |
| `development_history/EXAMPLES_JOURNAL.md` | Updated worker_role_assignment.py status and notes |
| `README.md` | Updated role list in v1.5 changelog section |

### v1.8 (logging refactor + _example_utils helper)

| File | Change |
| ---- | ------ |
| `examples/worker_role_assignment.py` | Import `report_validation`/`report_transpilation` from `_example_utils`; replaced the repeated `try/except + for w in warnings` boilerplate in `main()` with those helpers |
| `examples/_example_utils.py` | **New** — shared `report_validation(cls)` and `report_transpilation(cls)` utilities |
| `development_history/V1_9_PLAN.md` | **New** — full gap-analysis document for v1.9 |
| `README.md` | Added v1.8 changelog section |

### v1.8.1 (ROLE_CYCLE + ROLE_COMM_TYPE bug fix)

| File | Change |
| ---- | ------ |
| `examples/worker_role_assignment.py` | Added `ROLE_CYCLE` 13-slot tuple; `DEVICES = 26`; role assignment via `ROLE_CYCLE[nid % len(ROLE_CYCLE)]`; fixed `ROLE_COMM_TYPE` frozenset-unpack `TypeError` with dict comprehensions |
| `development_history/PRE_V19_REFACTORING.md` | **New** — documents v1.8.1 and v1.8.2 changes |
| `development_history/EXAMPLES_JOURNAL.md` | Updated worker_role_assignment.py notes |
| `README.md` | Added v1.8.1 changelog row |

### v1.8.2 (enum-value refactoring: no magic integers)

| File | Change |
| ---- | ------ |
| `examples/worker_role_assignment.py` | `ROLE_CYCLE` uses `WorkerRole.X` members; guards use `.value`; `case N:` → `case WorkerRole.X.value:`; `WorkerRole(x).name` → `x.name`; `int(r)` → `r.value` in main() |
| `development_history/PRE_V19_REFACTORING.md` | v1.8.2 section added |
| `development_history/EXAMPLES_JOURNAL.md` | v1.8.2 notes added |
| `README.md` | Added v1.8.2 changelog row |

### v1.8.3 (named constants for swarm-size tuning)

| File | Change |
| ---- | ------ |
| `examples/worker_role_assignment.py` | Extracted `ADDITIONAL_REPEATERS_EACH_CYCLE = 5` and `FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS = 2`; `ROLE_CYCLE` uses `*([WorkerRole.REPEATER] * ADDITIONAL_REPEATERS_EACH_CYCLE)`; `DEVICES` derived as `len(ROLE_CYCLE) * FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS` |
| `development_history/WORKER_ROLE_ASSIGNMENT.md` | Scenario section rewritten with constant formulas; design decision section updated; case label examples updated |

### v1.8.4 (enum constant-folding in transpiler)

| File | Change |
| ---- | ------ |
| `transpiler/python_ast_visitor.py` | `PythonAstVisitor.__init__` accepts optional `constants` dict; new `_resolve_dotted_chain()` helper; `visit_Attribute` constant-folds int/float resolutions to literals |
| `transpiler/transpiler_core.py` | `_transpile_method_body` passes `method.__globals__` as `constants` to the visitor |
| `tests/transpiler/test_python_ast_visitor.py` | 5 new tests: attribute fold, member fold, no-fold fallback, compare fold, match/case fold |
| `DSL_GUIDE.md` | §6.7 and §9 updated; `match/case` enum limitation removed |
| `development_history/WORKER_ROLE_ASSIGNMENT.md` | Transpiler caveat replaced with "fixed in v1.8.4" note |

### v1.9 (planned — receiver UID fix + transpiler improvements)

Tracked in `development_history/V1_9_PLAN.md`.  Key change for this example:

- **Receiver UID placeholder resolved**: add `receiver_uid = broadcast(is_receiver, self_uid())`
  as new step 5a; change spawn key from `(self_uid(), 0)` to `(self_uid(), receiver_uid)`.
- Algorithm step count increases to 8; CALL-order table must be updated accordingly.
