# Claude Context — `src/t_map_struct_memory/` std::map Suite

> **Last updated:** 2026-04-01
> **Conversation scope:** creation of a complete `std::map` test suite in C++17
> **Status:** all tasks completed; no pending work

---

## File Inventory (8 files)

| File | Role | Lines | Created |
|---|---|---|---|
| `simple_struct.h` | Defines `Point` — copyable value-type struct (`int32_t x, y`) | ~20 | Round 1 |
| `simple_class.h` | Defines `Person` — non-copyable heap-allocated class (`string name_, int32_t age_`) | ~40 | Round 1 |
| `map_printer.h` | `display()` overload family + `print_map<K,V>()` template | ~70 | Round 1 |
| `test_map.cpp` | 8 example functions (1a–4b) + `main()` writing to `test_map_output.txt` | ~700 | Round 1 |
| `summary.md` | Markdown summaries of the 4 files above + 8 examples | ~230 | Round 2 |
| `simple_struct2.h` | Defines `Point2` — non-copyable heap-allocated struct (same fields as `Point`) | ~55 | Round 3 |
| `test_map2.cpp` | Copy of `test_map.cpp` + 2 new examples (5a, 5b) for `Point2*`; writes to `test_map2_output.txt` | ~950 | Round 3 |
| `summary2.md` | Extends `summary.md` with `Point2`/`simple_struct2.h` coverage + 10 example summaries | ~260 | Round 3 |

---

## Architecture & Design Decisions

### Type matrix (5 value types x 2 key types = 10 examples)

| Key \ Value | `int32_t` | `string*` | `Point` (value) | `Person*` | `Point2*` |
|---|---|---|---|---|---|
| `int32_t` | 1a | 2a | 3a | 4a | 5a |
| `std::string` | 1b | 2b | 3b | 4b | 5b |

### Ownership categories

- **RAII-safe (ex 1, 3):** values stored inline in map nodes; map destructor handles everything.
- **Manual ownership (ex 2, 4, 5):** values are raw pointers; map destructor frees nodes only. Each example shows: save pointer -> erase iterator -> delete pointee, plus a cleanup loop at scope end.

### Key design choices

1. **`display(const Point2*)` placement:** defined at file scope in `test_map2.cpp`, NOT in `map_printer.h`. Reason: `map_printer.h` is shared with `test_map.cpp` which knows nothing about `Point2`. Two-phase ADL lookup finds the overload at `print_map<K, Point2*>` instantiation time because both `Point2` and the overload are in the global namespace.

2. **Non-copyable types (`Person`, `Point2`):** copy ctor/assign `= delete`; move ctor/assign `= default`. Enforces explicit pointer-based ownership semantics in maps.

3. **`test_map2.cpp` is a superset of `test_map.cpp`:** all 8 original example functions are byte-identical. Only additions: `#include "simple_struct2.h"`, the `display(const Point2*)` overload, `ex5a_int_to_point2()`, `ex5b_str_to_point2()`, and an updated `main()`.

4. **Overload resolution strategy:** concrete (non-template) `display()` overloads always beat the `template<typename T> display(const T&)` fallback per C++ overload resolution rules. No explicit specialization needed.

5. **Structured bindings (`auto& [k, v]`):** used throughout for range-for over maps and for iterating arrays of `std::pair`/`std::tuple` used as insertion data.

6. **`std::tuple` for 3-field data:** Person examples use `std::tuple<KeyType, std::string, int32_t>` for (key, name, age) rows, destructured with `auto& [k, name, age]`.

---

## Build & Run

```bash
# Build commands (to be run from src/t_map_struct_memory/):
g++ -std=c++17 -Wall -Wextra -o test_map  test_map.cpp
g++ -std=c++17 -Wall -Wextra -o test_map2 test_map2.cpp

# Run from src/t_map_struct_memory/ so output files land in the same folder:
./test_map    # produces test_map_output.txt
./test_map2   # produces test_map2_output.txt
```

All `#include` directives use either standard library headers (`<...>`) or local same-directory headers (`"..."`), so both build commands work correctly when run from within `src/t_map_struct_memory/`. No `-I` flags or path adjustments are needed.
Code was reviewed manually for correctness (includes, overload resolution, memory management) but was **not compiled** due to missing toolchain in PATH.

---

## Conversation Rounds

| Round | User request | Deliverables |
|---|---|---|
| 1 | Create `test_map.cpp` with std::map examples covering 4 value types x 2 key types, with memory explanations and JSON-like output | `simple_struct.h`, `simple_class.h`, `map_printer.h`, `test_map.cpp` |
| 2 | Export summaries to `summary.md` | `summary.md` |
| 3 | Answer: would a heap-allocated struct behave like `Person*`? (YES) Then create `Point2`, extend tests, write `summary2.md` | `simple_struct2.h`, `test_map2.cpp`, `summary2.md` |
| 4 | Conversation summary (text only) | Inline text response |
| 5 | Create this context recovery file | `claude_context.md` |

---

## Central Conceptual Takeaway

The `struct`/`class` keyword distinction in C++ is purely syntactic (default access specifier). What determines how a type must be managed inside a `std::map` is solely whether values are stored **by value** (RAII, automatic cleanup) or **by pointer** (manual `delete` required). `Point2*` (struct) and `Person*` (class) require identical map code patterns — the only difference is the number of heap allocations per entry (2 for `Point2*` with no string member; up to 4 for `Person*` with `name_` string).
