# AbstractExample Toolchain Bridge — Design Rationale

**Added:** 2026-05-28 (v1.9 Step E)

---

## Motivation

After the v2.0 AbstractExample refactor (2026-05-28), every example file contained
two classes:

1. **`@aggregate_function` class** — the algorithm specification; uses DSL primitives
   (`bis_distance`, `broadcast`, `spawn`, etc.) that do not exist as Python functions.
   Its purpose was transpilation to C++.
2. **`AbstractExample` subclass** — a **pure-Python re-implementation** of the same
   algorithm using regular Python math, bypassing the entire toolchain.

This defeated the purpose of `fcpp_bridge` for developers reading the examples.  The
`@aggregate_function` class looked like it was the algorithm, but it was never actually
*executed* — the pure-Python implementation in the subclass was what ran.

**Step E** fixes this by rewriting `AbstractExample.run()` to invoke the full pipeline:

```
validate(@aggregate_function class)
  → transpile → C++ source
  → compile   → binary  (SHA-256 cached)
  → SwarmProcess.start()
  → add nodes with initial_positions()
  → for each round: step() → _on_snapshot() → write log lines
  → on_round_complete(round_num, snapshot)
  → swarm.close()
  → on_simulation_end()
```

---

## Interface diff: old (v2.0) → new (v1.9/Step E)

### Added abstract methods

| Method | Signature | Notes |
|---|---|---|
| `aggregate_class` | `@property → Type` | The `@aggregate_function` class to transpile and run |

### Removed abstract methods

| Removed | Reason |
|---|---|
| `round_step(round_num, positions, states)` | Algorithm runs in C++; Python no longer re-implements it |
| `initial_states(positions)` | C++ binary owns initial state; Python no longer seeds it |

### Added optional properties (with defaults)

```python
@property
def build_dir(self) -> Path:
    return Path(__file__).parent / ".fcpp_build"

@property
def cpp_dir(self) -> Path:
    return Path(__file__).parent / ".fcpp_cpp"
```

### Updated hook signature

| Hook | v2.0 signature | v1.9 signature |
|---|---|---|
| `on_round_complete` | `(round_num, positions, states) → None` | `(round_num, snapshot: Optional[SwarmSnapshot]) → None` |

`log_header` and `log_line` now receive `state_data: Any` from
`NodeState.state_data` (a dict/JSON value from the C++ binary) instead of a
Python `@dataclass` instance.  The method signatures are identical — only the
runtime type of `state_data` changes.

---

## SwarmProcess.latest_snapshot()

Added alongside Step E:

```python
def latest_snapshot(self) -> Optional[SwarmSnapshot]:
    """Return the snapshot from the most recent update, or None before the first step."""
    return self._latest_snapshot
```

`_latest_snapshot` is populated by overriding `_dispatch_update()` in `SwarmProcess`:

```python
def _dispatch_update(self, snapshot: SwarmSnapshot) -> None:
    self._latest_snapshot = snapshot
    super()._dispatch_update(snapshot)
```

`run()` calls `swarm.latest_snapshot()` after each `step()` and passes the result
to `on_round_complete`.  With a synchronous backend, the snapshot is guaranteed to
reflect the round just completed.

---

## Step F dependency

Step E provides the new `AbstractExample` interface.  Step F migrates the seven
concrete example subclasses to use it (removing `round_step`, `initial_states`, and
their pure-Python helpers).  Until Step F is complete, the existing subclasses are
*broken* — they still override the removed abstract methods, which are no longer in
the base class.  Step F must follow immediately.
