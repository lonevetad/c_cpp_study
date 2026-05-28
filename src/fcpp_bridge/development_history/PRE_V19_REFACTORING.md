# fcpp_bridge — Pre-v1.9 Refactoring (v1.8.1 and v1.8.2)

Two focused changes to `worker_role_assignment.py` applied after v1.8 was stabilised
and before the v1.9 implementation phase begins.  They are independent of the v1.9
feature plan (`V1_9_PLAN.md`) but improve correctness and readability in the example
that v1.9 will most heavily modify.

---

## v1.8.1 — More REPEATER nodes + ROLE_COMM_TYPE bug fix

### Motivation

The original 24-node, `nid % 8` assignment gave each of the 8 roles exactly 3 nodes,
producing equal counts of REPEATER-type (6) and far fewer REPEATERs than ENDPOINTS (15).
This felt unrealistic: relay infrastructure typically outnumbers specialised sensors.

### Changes

| Item | Before | After |
|---|---|---|
| `DEVICES` | `24` (3 × 8 cycle) | `26` (2 × 13 cycle) |
| Role-assignment formula | `nid % 8` | `ROLE_CYCLE[nid % len(ROLE_CYCLE)]` |
| `ROLE_CYCLE` | — (not defined) | 13-slot tuple: 8 standard + 5 extra `WorkerRole.REPEATER` |
| ENDPOINT-type count | 15 | 10 |
| RECEIVER-type count | 3 | 2 |
| REPEATER-type count | 6 | 14 |

Constraint satisfaction: **REPEATER-type (14) > ENDPOINT-type (10) > RECEIVER-type (2)**.

### Bug fix — `ROLE_COMM_TYPE` dict

`{**frozenset({...})}` in a dict literal raises `TypeError: 'frozenset' object is not a
mapping` at import time — the example was unrunnable.  Fixed to use explicit dict
comprehensions:

```python
# Before (broken):
ROLE_COMM_TYPE = {
    **ENDPOINT_ROLES,          # TypeError — frozenset is not a mapping
    WorkerRole.RECEIVER: ...,
    **REPEATER_ROLES,
}

# After (correct):
ROLE_COMM_TYPE = {
    **{r: RoleCommunicationType.ENDPOINT  for r in ENDPOINT_ROLES},
    WorkerRole.RECEIVER: RoleCommunicationType.RECEIVER,
    **{r: RoleCommunicationType.REPEATER  for r in REPEATER_ROLES},
}
```

---

## v1.8.2 — Enum-value refactoring: eliminate magic integers

### Motivation

Using bare integer literals (e.g. `role == 1`, `case 0:`) to refer to enum members is
the "magic number" antipattern: the reader must consult the enum definition to decode the
meaning, and a typo silently uses the wrong value.  Python's `IntEnum.value` and
dotted-name match/case patterns provide the language-level tools to avoid this.

### Python-specific approach

| Context | Before | After |
|---|---|---|
| `ROLE_CYCLE` tuple entries | `0, 1, 2, 3, 4, …` | `WorkerRole.UNASSIGNED, WorkerRole.RECEIVER, …` |
| Boolean guards in `compute()` | `role == 1` | `role == WorkerRole.RECEIVER.value` |
| `match/case` labels | `case 0:` … `case _:` | `case WorkerRole.X.value:` for each role |
| Simulation `WorkerRole(x).name` | `WorkerRole(roles[nid]).name` | `roles[nid].name` (roles[nid] IS a WorkerRole) |
| `main()` display | `int(r)`, `int(ct)` | `r.value`, `ct.value` |

### Python 3.10+ match/case note

`case WorkerRole.X.value:` is a **dotted-name value pattern** (`a.b.c` chain).
Python 3.10+ always treats dotted names as value patterns (never capture patterns),
so Python evaluates the chain to the integer and compares it against the subject.
This supersedes the earlier advice in the docstring to use only integer literals.

### C++ transpilation (fixed in v1.8.4)

The DSL `compute()` function is processed by the Python AST visitor.
`WorkerRole.RECEIVER.value` and `case WorkerRole.X.value:` produce `Attribute` chains
in the AST.  Starting from v1.8.4, the visitor is initialised with the `compute`
function's `__globals__`, so it constant-folds any dotted chain that resolves to an
integer literal.  Both `case` labels and comparison guards now generate valid C++.

---

---

## v1.8.3 — Named constants for swarm-size tuning

### Motivation

`ROLE_CYCLE` originally used 5 explicit `WorkerRole.REPEATER` entries and
`DEVICES = 26` as a bare integer.  A reader wanting to resize the swarm or
adjust relay density had to count list entries manually and update two numbers
in sync.  Naming the knobs makes each intent explicit and keeps `DEVICES` derived.

### Changes

```python
# Before (v1.8.2):
ROLE_CYCLE = (
    WorkerRole.UNASSIGNED,  WorkerRole.RECEIVER, ...,
    WorkerRole.REPEATER, WorkerRole.REPEATER, WorkerRole.REPEATER,
    WorkerRole.REPEATER, WorkerRole.REPEATER,   # 5 extra, counted by eye
)
DEVICES = 26

# After (v1.8.3):
ADDITIONAL_REPEATERS_EACH_CYCLE = 5

ROLE_CYCLE = (
    WorkerRole.UNASSIGNED,  WorkerRole.RECEIVER, ...,
    *([WorkerRole.REPEATER] * ADDITIONAL_REPEATERS_EACH_CYCLE)
)

FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS = 2
DEVICES = len(ROLE_CYCLE) * FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS
# With 2 cycles: ENDPOINTS=10, RECEIVERS=2, REPEATER-type=14 (14 > 10 and 2 < 10).
```

### Tweaking guide

| Goal | Knob to change | Invariant to check |
|------|----------------|--------------------|
| Larger / smaller swarm | Increase / decrease `FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS` | `DEVICES` re-derives automatically |
| More relay coverage | Increase `ADDITIONAL_REPEATERS_EACH_CYCLE` | Keep `> 3` so `REPEATER-type > ENDPOINT-type` |
| Less relay coverage | Decrease `ADDITIONAL_REPEATERS_EACH_CYCLE` | Must remain `≥ 0`; at `0` one REPEATER per cycle still exists |

---

## Files changed

| File | Change |
|---|---|
| `examples/worker_role_assignment.py` | v1.8.1: ROLE_CYCLE; DEVICES; ROLE_COMM_TYPE fix; v1.8.2: enum `.value` in all comparisons, case labels, print output; `WorkerRole(x).name` → `x.name`; v1.8.3: `ADDITIONAL_REPEATERS_EACH_CYCLE`, `FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS`, derived `DEVICES` |
| `development_history/PRE_V19_REFACTORING.md` | This file (new, updated with v1.8.3) |
| `development_history/EXAMPLES_JOURNAL.md` | Updated worker_role_assignment notes |
| `README.md` | Added v1.8.1, v1.8.2, v1.8.3 rows |
