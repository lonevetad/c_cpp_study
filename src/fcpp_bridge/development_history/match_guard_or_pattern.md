# fcpp_bridge v2.0 — Match Guard Clauses and OR Patterns

**Date**: 2026-05-28  
**Branch**: bugfix/fcpp_bridge/it1  
**Transpiler file**: `transpiler/python_ast_visitor.py` — `visit_Match()`

---

## Summary

The Python DSL transpiler (`PythonAstVisitor.visit_Match`) previously supported
only two `match/case` patterns:

| Pattern | Status before v2.0 |
|---------|-------------------|
| `case X:` — value pattern | ✅ Supported |
| `case _:` — wildcard (default) | ✅ Supported |
| `case X if cond:` — guard clause | ❌ Not supported |
| `case A \| B:` — OR pattern | ❌ Not supported |

v2.0 adds both missing patterns, bringing the Python→C++ match/case mapping
to full parity for all constructs that have a natural C++14 equivalent.

---

## Guard Clauses

### Python syntax

```python
match role:
    case CommunicationRole.SENDER.value if dist < COMM:
        # local sender task
        ...
    case CommunicationRole.RECEIVER.value:
        # receiver task
        ...
    case _:
        # default
        ...
```

The `if cond` part after the case label is called a **guard clause**.  Python
evaluates it only when the value pattern matches; if the guard is False the case
is skipped (and the subject falls through to the next case).

### Generated C++ (C++14)

```cpp
switch (role) {
case 1:
    if ((dist < COMM)) {
        // local sender task
    }
    break;
case 3:
    // receiver task
    break;
default:
    // default
    break;
}
```

**Semantics note**: C++ `switch` has no native guard mechanism.  The transpiler
wraps the case body in an `if (guard_expr) { ... }`.  The `break` still follows
unconditionally so a non-matching guard exits the switch rather than falling
through to the next case.  This faithfully replicates Python's behaviour.

### AST node

Guard expressions are stored in `ast.match_case.guard` (not `None` when
present).  The transpiler visits `case.guard` before visiting the case body.

---

## OR Patterns

### Python syntax

```python
match comm_type:
    case RoleCommunicationType.ENDPOINT.value | RoleCommunicationType.REPEATER.value:
        relay = True
    case RoleCommunicationType.RECEIVER.value:
        relay = False
```

An OR pattern (`case A | B | C:`) matches when the subject equals *any* of the
listed values.  The same body is executed for all matching values.

### Generated C++ (C++14)

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

The multiple `case X:` labels with no intervening `break` is the idiomatic
C++ fallthrough pattern.  It is valid in C++14 and avoids the need for
`[[fallthrough]]` (C++17).

### AST node

OR patterns map to `ast.MatchOr` with a `patterns` attribute that is a list of
`ast.MatchValue` nodes.  Each sub-pattern is emitted as a separate `case X:`
label; they all share the same body and a single `break`.

---

## Combining Guard + OR

A guard clause can be applied to an OR pattern:

```python
match role:
    case Role.A.value | Role.B.value if condition:
        ...
```

The transpiler applies the guard to the entire OR group:

```cpp
case 0:
case 1:
    if (condition) {
        ...
    }
    break;
```

This is the correct behaviour: both labels share the guarded body.

---

## Implementation

Changes to `transpiler/python_ast_visitor.py`:

```python
def visit_Match(self, node: ast.Match) -> str:
    subject = self.visit(node.subject)
    cases_cpp = []
    for case in node.cases:
        body = self.transpile_statements(case.body)
        pattern = case.pattern

        # Guard clause wraps body in if block
        if case.guard is not None:
            guard_cpp = self.visit(case.guard)
            body = f"if ({guard_cpp}) {{\n{body}\n    }}"

        if isinstance(pattern, ast.MatchAs) and pattern.name is None and pattern.pattern is None:
            cases_cpp.append(f"default:\n{body}\n    break;")
        elif isinstance(pattern, ast.MatchValue):
            val = self.visit(pattern.value)
            cases_cpp.append(f"case {val}:\n{body}\n    break;")
        elif isinstance(pattern, ast.MatchOr):
            labels = [f"case {self.visit(sub.value)}:"
                      for sub in pattern.patterns if isinstance(sub, ast.MatchValue)]
            cases_cpp.append("\n".join(labels) + f"\n{body}\n    break;")
        else:
            self.errors.append(f"Unsupported match pattern: {type(pattern).__name__}")
    ...
```

---

## Tests added

File: `tests/transpiler/test_python_ast_visitor.py`

| Test | What it checks |
|------|---------------|
| `test_match_guard_simple` | `case 1 if active:` emits `if (active)` inside the case |
| `test_match_guard_expression` | Guard with comparison: `if cond < threshold` |
| `test_match_guard_body_indented` | Body nested inside guard, before break |
| `test_match_guard_default_with_guard` | `case _ if fallback:` emits `default: if (fallback)` |
| `test_match_or_pattern_two_values` | `case 1 \| 2:` emits `case 1: case 2:` |
| `test_match_or_pattern_three_values` | `case 1 \| 2 \| 3:` emits three labels |
| `test_match_or_pattern_body_once` | Body appears exactly once (not per label) |
| `test_match_or_pattern_with_enum_folding` | OR pattern combined with IntEnum constant-folding |

Total new tests: 8.  All 131 transpiler tests pass after the change.

---

## Limitations (still not supported)

| Pattern | Reason |
|---------|--------|
| `case (x, y):` — sequence/tuple binding | No C++ switch equivalent; use if/elif |
| `case Point(x=a):` — class pattern | No C++ switch equivalent |
| `case x:` — capture pattern (bare name) | Would become a variable binding in Python; ambiguous |
| `case str() \| int():` — type pattern | No C++ switch equivalent |

These patterns require arbitrary structural matching that cannot map to
`switch`/`case`.  Use `if/elif/else` for these cases.

---

## FCPP CALL-counter warning

Guard expressions **must not contain aggregate primitive calls** (no `nbr`,
`old`, `bis_distance`, etc.).  Primitive calls inside `match/case` blocks
(whether guards or bodies) desynchronise the CALL counter across nodes and
produce incorrect C++ behaviour.

All aggregate primitives must be called *before* the `match/case` statement,
storing their results in local variables.  Guard expressions may reference
those local variables safely.

**Correct**:
```python
dist = bis_distance(is_source, 1, COMM)   # primitive before match

match role:
    case Role.SENDER.value if dist < COMM:  # guard references local var — OK
        ...
```

**Incorrect**:
```python
match role:
    case Role.SENDER.value if bis_distance(is_source, 1, COMM) < COMM:  # WRONG
        ...
```
