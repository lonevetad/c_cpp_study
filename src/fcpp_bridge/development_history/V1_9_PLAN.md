# fcpp_bridge v1.9 — Development Plan

**Created:** 2026-05-28  
**Context:** This document is the result of a gap-analysis session conducted before v1.9
implementation begins.  It covers gaps identified in the Known Limitations tables across
the codebase, together with answers to the reasoning questions posed in the session.

---

## Table of Contents

1. [Gap #1 — Receiver UID placeholder (broadcast solution)](#1-gap-1--receiver-uid-placeholder)
2. [Gap #2 — set_t{node.uid} transpilation](#2-gap-2--set_tnodeuid-transpilation)
3. [Gap #3 — min_hood with tuple → std::make_tuple](#3-gap-3--min_hood-with-tuple)
4. [Gap #4 — node_uid() as a companion to self_uid()](#4-gap-4--node_uid-companion)
5. [Gap #6 — ActivePingStrategy: missing C++ runtime support](#5-gap-6--activepingstrategy-c-runtime)
6. [Gap #7 — DeviceManager.accept_registrations(port)](#6-gap-7--devicemanageracceptregistrationsport)
7. [Gap #8 — PhysicalNode: auto-close on exception (RAII-style)](#7-gap-8--physicalnode-auto-close-on-exception)
8. [Gap #9 — Multi-swarm coordination UI (OutputChannel design)](#8-gap-9--multi-swarm-coordination-ui)
9. [v1.8 — Logging refactor (print → logger, validation helper)](#9-v18--logging-refactor)
10. [v1.9 Implementation Checklist](#10-v19-implementation-checklist)

---

## 1. Gap #1 — Receiver UID placeholder

### What is the problem?

In `worker_role_assignment.py`, the spawn key is `(self_uid(), 0)`.  The sender half
(`self_uid()`) was fixed in v1.6 — it now correctly transpiles to `node.uid`.  The
*receiver* half is still `0`, a hard-coded placeholder.  The consequence is that all
spawn keys share the same destination `0`, so the routing logic treats every message
as going to node 0, not to the actual nearest RECEIVER node.

### Why is receiver_uid needed?

The spawn lambda determines a node's routing status for each message:

```python
STATUS_TERMINATED if is_receiver else               # am I the destination?
STATUS_INTERNAL if (sender ∈ below or recv ∈ below) else   # am I on the path?
STATUS_BORDER                                         # I'm off-path
```

The `recv ∈ below` check requires each node to know the real UID of the destination
RECEIVER.  Without this, only the `sender ∈ below` branch fires, so the spanning tree
does not converge toward the RECEIVER — messages route randomly.

### Why `broadcast` and not `channel_broadcast`?

`broadcast(root_flag, value)` distributes a *value* from any root (where
`root_flag=True`) outward through a gradient, so every non-root node receives the
value of its nearest root.  RECEIVER nodes are the roots; all other nodes receive the
nearest RECEIVER's UID:

```python
# New step (before spawn):
receiver_uid = broadcast(is_receiver, self_uid())   # noqa: F821
# → every node learns the UID of its nearest RECEIVER
new_msg = (self_uid(), receiver_uid) if is_endpoint else None   # noqa: F821
```

`channel_broadcast` creates an *elliptical channel* between two fixed endpoints: a
source and a destination.  It requires knowing BOTH endpoints' UIDs *in advance*.  Here
we need the RECEIVER to advertise itself — the destination is dynamically discovered,
not known a priori.  `channel_broadcast` would be circular: you need the receiver UID
to define the channel, but the channel is what distributes the receiver UID.

`broadcast` is the right primitive because:
1. Any node where `root_flag=True` acts as the root automatically.
2. In a multi-receiver topology (multiple nodes with `is_receiver=True`), each
   non-receiver node naturally learns its *nearest* receiver's UID via the gradient.
3. No pre-knowledge of UIDs is needed.

### Actions required (v1.9)

1. Add `broadcast` as a new **step 5a** in `worker_role_assignment.py`:

   ```python
   # Step 5a: distribute receiver UID to all nodes via broadcast
   receiver_uid = broadcast(is_receiver, self_uid())   # noqa: F821
   # replaces the placeholder 0 in step 5b:
   new_msg = (self_uid(), receiver_uid) if is_endpoint else None   # noqa: F821
   ```

2. Update `CALL`-order documentation: `broadcast` is a new CALL-counted primitive call
   and must appear in the flat section before the `match/case`.

3. Update `WORKER_ROLE_ASSIGNMENT.md` — mark "receiver UID placeholder" as ✅ resolved.

4. Update `node_uid__placeholder_flagging.md` — update the `worker_role_assignment.py`
   row in the affected call-sites table.

5. No new test needed unless the demo simulation is updated to use the real receiver UID
   (the DSL layer still returns `0` from `broadcast` in Python, so the demo already
   uses real `nid` directly for correctness).

---

## 2. Gap #2 — set_t{node.uid} transpilation

### Is `set_t` the correct C++ type?

Yes. In FCPP's `basics.hpp`:

```cpp
using device_t = uint32_t;
using set_t    = std::unordered_set<device_t>;
```

`set_t` is the canonical type for routing sets.  `std::set<device_t>` would also
compile but would be slightly slower (ordered vs. unordered).  Use `set_t` for
idiomatic FCPP code.

### Can the transpiler produce `set_t{node.uid}`?

Yes, with a targeted fix.  The current transpiler emits `frozenset(...)` verbatim
because `frozenset` is not in `_FCPP_PRIMITIVES` and is not handled by `visit_Call`.

The fix is a new mapping in `visit_Call` inside `PythonAstVisitor`:

```python
if func_name == "frozenset":
    if args:
        return f"set_t{{{', '.join(args)}}}"   # frozenset({x}) → set_t{x}
    return "set_t{}"                             # frozenset()   → set_t{}
```

`frozenset({self_uid()})` desugars in the AST as `frozenset(Call(Name('set'), ...))`;
after visiting the inner expression `self_uid()` becomes `node.uid`, so the result is
`set_t{node.uid}` — correct.

### Actions required (v1.9)

1. Add `frozenset` handler in `PythonAstVisitor.visit_Call` (2 lines).
2. Add a transpiler test: `frozenset({self_uid()})` → `set_t{node.uid}`.
3. Add a transpiler test: `frozenset()` → `set_t{}`.
4. Update `node_uid__placeholder_flagging.md` §3.3 — mark `frozenset` transpilation as resolved.

---

## 3. Gap #3 — min_hood with tuple → std::make_tuple

### What is wrong today?

```python
parent = min_hood((nbr_dists, self_uid()))
# transpiles to:
parent = min_hood(CALL, (nbr_dists, node.uid));
```

`(x, y)` in C++ is a *comma expression* — it evaluates both operands and returns the
value of the last one.  This is not a tuple; it silently computes the wrong result.

The correct C++ is:

```cpp
auto tup    = min_hood(CALL, std::make_tuple(nbr_dists, node.uid));
device_t parent = std::get<1>(tup);
```

### What actions are needed?

Two complementary approaches, in order of complexity:

**Option A — Heuristic in `visit_Tuple` / `visit_Call` (recommended for v1.9)**

Detect a Tuple literal passed as the *sole* argument to `min_hood` or `max_hood` and
wrap it:

```python
# In visit_Call, before the general _FCPP_PRIMITIVES path:
if func_name in ("min_hood", "max_hood") and len(node.args) == 1:
    arg = node.args[0]
    if isinstance(arg, ast.Tuple):
        elems = [self.visit(e) for e in arg.elts]
        return f"{func_name}(CALL, std::make_tuple({', '.join(elems)}))"
```

This handles the exact pattern used in all current examples without changing the
general tuple-to-comma-expression default.

**Option B — Full `std::tuple` support (future)**

Replace the general Python tuple `(x, y, z)` transpilation with
`std::make_tuple(x, y, z)` everywhere.  This would also require updating subscripts
on tuple results to use `std::get<N>(...)`.  High impact; deferred to a later version.

### Actions required (v1.9)

1. Add heuristic `min_hood` / `max_hood` + tuple detection in `visit_Call`.
2. Return expression includes `std::make_tuple(...)` for the tuple elements.
3. Add `std::get<1>(...)` wrapping for the *callers* that extract the UID:
   — in `worker_role_assignment.py` the result is named `parent` but only the tuple
     component 1 (UID) is needed.  The transpiler cannot know this automatically;
     document as a manual review item.
4. Add tests for both `min_hood((x, y))` and `max_hood((x, y))`.
5. Update `node_uid__placeholder_flagging.md` §3.5 — mark as resolved for the
   `make_tuple` side; note that `std::get<N>` extraction remains a manual post-step.

---

## 4. Gap #4 — node_uid() as a companion to self_uid()

### Background

`self_uid()` (added in v1.6) transpiles to `node.uid` (local device UID).  The
question is: could a `node_uid()` function call serve the same purpose?

### Answer

`self_uid()` already fills this gap exactly.  A `node_uid()` alias would be redundant.
However, there is a *different* gap: `node.nbr_uid()` (neighbour UIDs in a field).
In `min_hood`, the real C++ usage is:

```cpp
min_hood(CALL, std::make_tuple(nbr(CALL, ds), node.nbr_uid()))
```

`node.nbr_uid()` produces a *field* of the UIDs of all neighbours (one per neighbour),
not the local UID.  There is currently no DSL counterpart.

### Actions required (v1.9 — companion primitive)

1. Add `NbrUid` primitive class in `python_dsl/primitives/nbr_uid.py` (already present
   as part of the 64 primitives: `nbr_uid` maps to `basics.hpp`).  Verify that
   `nbr_uid` in `_FCPP_PRIMITIVES` emits `nbr_uid(CALL)` correctly.
2. Confirm: in `worker_role_assignment.py` step 2, `self_uid()` is the correct
   tie-breaking key (local UID, not neighbour field); no change needed there.
3. Document distinction: `self_uid()` → `node.uid` (scalar); `nbr_uid()` → field of
   neighbour UIDs (used in more advanced patterns).

---

## 5. Gap #6 — ActivePingStrategy: missing C++ runtime support

### What is incomplete?

The Python `ActivePingStrategy` is fully implemented.  It sends
`{"cmd": "ping", "node_id": N}` via the IPC backend and expects
`{"status": "pong"}` in the response.

The **C++ binary** does not yet implement the ping handler.  The runtime templates in
`runtime/runtime_generator.py` handle `step` and `get_state` commands; there is no
`ping` branch.

### Actions required (v1.9)

1. **`runtime/runtime_generator.py`** — add a ping handler to the IPC server loop
   template.  The handler must:
   - Check for `{"cmd": "ping", "node_id": N}` in the incoming command.
   - Reply `{"status": "pong", "node_id": N}` immediately (no FCPP round is needed).
   - This is a pure IPC-layer concern; no FCPP round is executed.

   Approximate C++ skeleton (in the generated ipc_server.hpp):
   ```cpp
   } else if (cmd == "ping") {
       int nid = request["node_id"];
       response["status"] = "pong";
       response["node_id"] = nid;
   ```

2. **`ActivePingStrategy` docstring** — update to remove the "Requires C++ ping handler"
   warning once the runtime template ships the handler.

3. **New test** — `test_liveness_strategy.py`: mock the backend's `send_command` to
   return `{"status": "pong"}` and verify that `ActivePingStrategy.check()` returns
   `True` for the pinged node.  (This test already partially exists; extend it to cover
   the round-trip scenario with the new response format.)

---

## 6. Gap #7 — DeviceManager.accept_registrations(port)

### What is missing?

Currently Python *connects to* physical devices; it never *accepts* connections from
them.  A device that self-registers (e.g., a drone that powers on and sends a
registration packet) has no entry point.

### What is needed?

`DeviceManager.accept_registrations(port)` must:
1. Start a lightweight TCP/HTTP server on `port`.
2. When a device sends a registration payload (JSON: `{"name": str, "host": str,
   "port": int, "backend": str}`), create a `PhysicalNode` and register it via
   `add_physical(name, host, port, backend_type)`.
3. Fire optional `on_registered(name, node)` callbacks for each new registration.
4. Provide `stop_accepting_registrations()` to shut the server down.

### Design choices

- **HTTP (asyncio + `http.server`)** — zero external dependencies; fits the existing
  `HttpBackend` pattern.
- The registration server runs in a daemon thread (like the heartbeat monitor).
- The payload schema should be documented and versioned (add a `"version": "1.0"` field).

### Actions required (v1.9)

1. **`ipc/device_manager.py`**: add `accept_registrations(port, on_registered=None)`,
   `stop_accepting_registrations()`, and `_registration_server_loop()` (daemon thread).
2. **`tests/ipc/test_device_manager.py`**: add tests for registration flow using
   `urllib.request.urlopen` to simulate a device self-registering.
3. **`TUTORIAL_in_depth.md`**: add a §"Self-registering physical devices" subsection.
4. **`README.md`**: add `accept_registrations` to the DeviceManager feature bullet.

---

## 7. Gap #8 — PhysicalNode: auto-close on exception (RAII-style)

### What C++14 mechanism exists?

In C++, **RAII** (Resource Acquisition Is Initialization) ensures that a destructor
runs automatically when an object goes out of scope, even if an exception is thrown.
This guarantees that resources (sockets, file handles, memory) are always released.

In Python, the equivalent is:
- **Context manager** (`with` statement / `__enter__` / `__exit__`) — already
  implemented for `PhysicalNode`.
- **`try/finally`** — runs cleanup regardless of exceptions.
- **`contextlib.closing`** and **`contextlib.suppress`** — higher-level helpers.

The current gap: if `connect()` raises an exception partway through (e.g., the
`GrpcBackend` constructor fails), `_connected` remains `True` from a previous
successful connect, and `backend` may be in a partially initialised state.  Subsequent
calls (`is_connected`, `get_state()`) can behave incorrectly.

### Fix (v1.9)

Wrap the `connect()` body in `try/except` and reset state on failure:

```python
def connect(self) -> None:
    if self.backend is not None:
        self.backend.close()
        self.backend = None
    self._connected = False          # pessimistic reset before any allocation
    try:
        url = f"http://{self.host}:{self.port}"
        if self.backend_type == "http":
            self.backend = HttpBackend(url)
        elif self.backend_type == "grpc":
            self.backend = GrpcBackend(port=self.port)
        else:
            raise ValueError(...)
        self.backend.subscribe_state_updates(self._dispatch_update)
        self._connected = True       # only set True after full success
    except Exception:
        if self.backend is not None:
            try:
                self.backend.close()
            except Exception:
                pass
        self.backend = None
        raise
```

Similarly, wrap backend calls in `get_state()`, `step()`, and the reconnect loop with
`except Exception` → `self._connected = False`.

### Actions required (v1.9)

1. **`ipc/physical_node.py`**: refactor `connect()` as above.
2. **`ipc/_ipc_node_base.py`**: wrap `get_state()` and `send_command()` calls to set
   `_connected = False` on `ConnectionError` / `OSError`.
3. **`tests/ipc/test_physical_node.py`**: add test where backend constructor raises →
   verify `is_connected` is `False` and `backend` is `None` after the exception.

---

## 8. Gap #9 — Multi-swarm coordination UI (OutputChannel design)

### User specification (answered 2026-05-28)

> "Allow flexible, configurable and multiple-channel output: one or more of those
> options could be provided (if necessary, a proxy will forward the data received to
> the registered output channels; the forwarding might be sequential-and-synchronous
> or parallel-and-asynchronous depending on a constructor-level parameter) and the
> backend accepts an output channel (or the 'proxy' previously mentioned: define a
> super-class by applying either Prototype Programming and/or Object Oriented
> Programming paradigms), defaulting to a plain but configurable logging system."

### Design

The design mirrors the existing `ListenerProxy` pattern (which dispatches `SwarmSnapshot`
updates to multiple listeners), applied now to fleet-wide state output from
`DeviceManager`.

#### Class hierarchy

```
OutputChannel (ABC)         — abstract base; Prototype pattern (clone())
├── LoggingOutputChannel    — default; writes to logger (configurable level/format)
├── FileOutputChannel       — writes JSON/CSV lines to a file or stream
├── CallbackOutputChannel   — wraps a Callable[[str, Any], None] (name, state)
└── ProxyOutputChannel      — fan-out to N channels; sequential or parallel
```

All classes implement `Prototype.clone()` for configuration duplication.

#### API

```python
class OutputChannel(ABC):
    def send(self, name: str, payload: Any) -> None: ...
    def close(self) -> None: ...
    def clone(self) -> "OutputChannel": ...   # Prototype pattern

class ProxyOutputChannel(OutputChannel):
    def __init__(self, mode: str = "sequential"): ...   # "sequential"|"parallel"
    def add_channel(self, ch: OutputChannel) -> int: ...   # returns channel ID
    def remove_channel(self, channel_id: int) -> None: ...
```

#### Integration

`DeviceManager` accepts an optional `output_channel=` constructor kwarg.  If `None`
(default), a `LoggingOutputChannel` is created automatically.  Methods that currently
`print(...)` (e.g. `start_all`, `connect_all`, `close_all`, `step_all`) route their
status messages through `output_channel.send(name, payload)` instead.

```python
class DeviceManager:
    def __init__(self, output_channel: Optional[OutputChannel] = None):
        self._output = output_channel or LoggingOutputChannel()
        ...

    def start_all(self) -> None:
        for name, device in self._devices.items():
            try:
                device.start()
                self._output.send(name, {"event": "started"})
            except Exception as exc:
                self._output.send(name, {"event": "start_failed", "error": str(exc)})
```

#### Where to add the new files

```
ipc/output_channel.py           OutputChannel ABC + clone() mixin
ipc/logging_output_channel.py   LoggingOutputChannel(level, fmt)
ipc/file_output_channel.py      FileOutputChannel(path_or_stream, format="json")
ipc/callback_output_channel.py  CallbackOutputChannel(fn)
ipc/proxy_output_channel.py     ProxyOutputChannel(mode="sequential")
```

`ipc/__init__.py` re-exports all five.

### Actions required (v1.9)

1. Add the five output-channel files listed above.
2. Refactor `DeviceManager.__init__` to accept `output_channel=` and route all status
   prints through it.
3. Add 10–15 tests in `tests/ipc/test_output_channel.py`.
4. Update `README.md` feature table.
5. Update `TUTORIAL_in_depth.md` with a "Multi-swarm output channels" section.

---

## 9. v1.8 — Logging refactor

This is an **implementation milestone** (not planning):

### 9.1 print() → get_logger() in library code

All `print()` calls in the library core (not in examples or CLI scripts) are replaced
with the existing `log.py` infrastructure:

| File | Level mapping |
|---|---|
| `compiler/compiler_core.py` | Cache hit → `DEBUG`; compile start/success → `INFO`; failure → `ERROR` |
| `ipc/swarm_process.py` | Start/connected/closed → `INFO` |
| `ipc/physical_node.py` | Connected/disconnected/reconnect-fail → `INFO` / `WARNING` |
| `ipc/device_manager.py` | start_all errors → `WARNING`; step_all errors → `WARNING` |
| `runtime/runtime_generator.py` | Generated headers → `INFO` |
| `visualization/text_dashboard.py` | Dashboard output remains `print` (it IS the output by design) |
| `grammar/generate_antlr.py` | CLI tool; `print` appropriate (not library code) |

### 9.2 Validation warning helper

Every example repeats this pattern:
```python
warnings = AggregateValidator.validate(MyClass)
print(f"    OK — {len(warnings)} warning(s)")
for w in warnings:
    print(f"       {w}")
```

Refactored to a single utility function, placed in the new
`examples/_example_utils.py` module:

```python
def report_validation(cls, logger=None, indent="    "):
    """Validate cls, print/log results, return warnings list.
    Raises on validation failure."""
    from fcpp_bridge.python_dsl.validators import AggregateValidator
    warnings = AggregateValidator.validate(cls)
    msg = f"{indent}OK — {len(warnings)} warning(s)"
    if logger:
        logger.info(msg)
        for w in warnings:
            logger.warning(f"{indent}  {w}")
    else:
        print(msg)
        for w in warnings:
            print(f"{indent}  {w}")
    return warnings
```

All example `main()` functions then call `report_validation(MyClass)`.

---

## 10. v1.9 Implementation Checklist

### Transpiler (python_ast_visitor.py)

- [ ] Add `frozenset` → `set_t{...}` in `visit_Call`
- [ ] Add `min_hood`/`max_hood` + Tuple → `std::make_tuple(...)` in `visit_Call`
- [ ] Tests: `test_frozenset_to_set_t`, `test_min_hood_tuple_make_tuple`

### worker_role_assignment.py

- [ ] Add step 5a: `receiver_uid = broadcast(is_receiver, self_uid())`
- [ ] Change spawn key: `new_msg = (self_uid(), receiver_uid) if is_endpoint else None`
- [ ] Update algorithm table comment (step count becomes 8)

### IPC layer

- [ ] `PhysicalNode.connect()` — pessimistic `_connected` reset + exception cleanup
- [ ] `DeviceManager` — `accept_registrations(port)` + `stop_accepting_registrations()`
- [ ] `OutputChannel` ABC + 4 implementations + `ProxyOutputChannel`
- [ ] `DeviceManager.__init__` — `output_channel=` kwarg

### Runtime templates

- [ ] `runtime_generator.py` — add `ping` handler in generated C++ IPC server loop

### Tests

- [ ] `test_python_ast_visitor.py` — frozenset, min_hood tuple
- [ ] `test_liveness_strategy.py` — ActivePingStrategy full pong round-trip
- [ ] `test_physical_node.py` — auto-close on connect exception
- [ ] `test_device_manager.py` — accept_registrations flow
- [ ] `test_output_channel.py` — new file, 10–15 tests

### Documentation

- [ ] `node_uid__placeholder_flagging.md` — update §1, §3.3, §3.5
- [ ] `WORKER_ROLE_ASSIGNMENT.md` — mark receiver UID gap as resolved in v1.9
- [ ] `TUTORIAL_in_depth.md` — add multi-swarm output channels section
- [ ] `README.md` — v1.9 changelog section

---

## Estimated test delta (v1.9)

| Component | New tests |
|---|---|
| Transpiler (frozenset, min_hood tuple) | +6 |
| ActivePingStrategy C++ round-trip | +3 |
| PhysicalNode exception safety | +4 |
| DeviceManager.accept_registrations | +5 |
| OutputChannel + ProxyOutputChannel | +15 |
| **Total** | **+33** |

Projected total: **611 + 33 = 644 tests**.
