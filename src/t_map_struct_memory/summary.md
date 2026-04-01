# `std::map` Test Suite — Summary

> **Standard:** C++17  
> **Output:** `test_map_output.txt` (written to the working directory at run time)  
> **Build:** `g++ -std=c++17 -Wall -Wextra -o test_map test_map.cpp`  
> _(run the executable from `TESTS/` so the output file lands in the same folder)_

---

## File Summaries

### `simple_struct.h`

Defines `Point`, a plain aggregate struct with two `int32_t` members (`x`, `y`).

- **Storage model:** value type — no dynamic allocation of its own.  
  When held in a `std::map`, the `Point` object sits **inline inside the
  tree node** that `std::allocator` places on the heap. There is no extra
  pointer or secondary heap block.
- **Destructor:** compiler-generated and trivial — zero cost at erasure time.
- **Interface:** `to_string()` returns a human-readable `"{ x: N, y: M }"` string.
- **Dependencies:** `<cstdint>`, `<sstream>`, `<string>`

---

### `simple_class.h`

Defines `Person`, a minimal class with a `std::string name_` and an `int32_t age_`.

- **Storage model:** always heap-allocated via `new Person(...)` and stored in maps
  as a raw `Person*`. The map node holds the pointer (8 B); the `Person` object
  itself lives in a separately `new`-allocated block. `name_` may additionally
  allocate its own heap buffer when the name length exceeds the SSO threshold
  (~15 chars on most implementations).
- **Ownership:** intentionally **non-copyable** (copy constructor and copy-assignment
  are `= delete`). Only raw-pointer and move semantics are supported, which
  mirrors the explicit ownership model demonstrated in the examples.
- **Destructor:** compiler-generated default — calls `~std::string()` on `name_`
  and releases the `age_` storage.
- **Interface:** `name()`, `age()` accessors and `to_string()` returning
  `"{ name: "…", age: N }"`.
- **Dependencies:** `<cstdint>`, `<sstream>`, `<string>`, `<utility>`

---

### `map_printer.h`

Provides the `display()` overload family and the `print_map<K,V>()` function
template. Includes both `simple_struct.h` and `simple_class.h`.

#### `display()` overloads

| Overload signature | Output format |
|---|---|
| `display(const T&)` _(template fallback)_ | `operator<<` stringification |
| `display(int32_t)` | plain decimal, no quotes |
| `display(const std::string&)` | `"value"` — double-quoted |
| `display(const std::string*)` | `"value"` or `null` if pointer is null |
| `display(const Point&)` | delegates to `Point::to_string()` |
| `display(const Person*)` | delegates to `Person::to_string()` or `null` |

C++ overload resolution **always prefers the non-template overload** over a
template instantiation when both are equally good matches, so the concrete
overloads above take priority without any explicit specialisation syntax.

#### `print_map<K,V>(map, ostream)`

Iterates the map in sorted-key order and writes a 4-space-indented, JSON-like
object to the given stream:

```
{
    key1: value1,
    key2: value2
}
```

String keys and values are automatically quoted; numeric and composite types
use their respective `display()` representation. A trailing comma is suppressed
on the last entry.

- **Dependencies:** `<cstdint>`, `<map>`, `<ostream>`, `<sstream>`, `<string>`,
  `"simple_class.h"`, `"simple_struct.h"`

---

### `test_map.cpp`

The test driver. Contains eight static example functions and a `main()` that
opens `test_map_output.txt`, calls each example in order, and closes the file.

Each example function follows the same structure:

1. **Memory model block** — explains the exact stack/heap layout for that
   key+value type combination, including RAII guarantees and manual-cleanup
   obligations.
2. **Insertions** — logs every `[ADD]` line (key, value, heap address for
   pointer types), then prints the full map state via `print_map`.
3. **Removals** — logs every `[REMOVE]` line with a step-by-step breakdown
   of iterator erasure vs. `delete` for pointer types, then prints the
   updated map state.
4. **Final cleanup note** — for pointer-value maps: iterates remaining entries,
   `delete`s each pointee, and confirms that the map destructor then safely
   frees all remaining nodes.

- **Dependencies:** `<cstdint>`, `<fstream>`, `<iostream>`, `<map>`, `<string>`,
  `<tuple>`, `<utility>`, `"map_printer.h"`

---

## Overall Test Summary

The suite exercises `std::map` across **4 value types × 2 key types = 8 examples**,
covering two orthogonal axes:

| Axis | Choices |
|---|---|
| **Key type** | `int32_t` (numeric order) · `std::string` (lexicographic order) |
| **Value type** | `int32_t` · `std::string*` (heap) · `Point` (struct by value) · `Person*` (heap) |

The central theme is **memory ownership**. The examples are grouped into two
memory-management categories:

- **RAII-safe (Examples 1 and 3):** values of type `int32_t` and `Point` are
  stored inline inside the map nodes. The map destructor releases all memory
  automatically with no programmer intervention.
- **Manual ownership required (Examples 2 and 4):** values are raw pointers to
  objects allocated with `new`. The map destructor frees the tree nodes but
  **does not follow pointers**. Each example shows the correct two-step removal
  pattern (erase iterator → delete pointee) and performs an explicit cleanup
  loop before the map leaves scope to prevent memory leaks.

---

## Individual Example Summaries

### Example 1a — `std::map<int32_t, int32_t>`

- **Key/Value:** both integral, 4 B each, stored inline in every tree node.
- **Heap allocations per entry:** 1 (the node itself).
- **Cleanup:** fully automatic (RAII). `std::map` destructor frees all nodes.
- **Insertions:** `{3,300}`, `{1,100}`, `{5,500}`, `{2,200}`, `{4,400}` — 5 entries.
- **Removals:** keys `5` and `2` erased; 3 entries remain when scope ends.

---

### Example 1b — `std::map<std::string, int32_t>`

- **Key/Value:** string key (may internally heap-allocate for SSO overflow),
  `int32_t` value inline.
- **Heap allocations per entry:** 1 node + 0 or 1 key-buffer (SSO-dependent).
- **Cleanup:** fully automatic — `~std::string()` frees key buffers; destructor
  frees nodes.
- **Key ordering:** lexicographic (`alpha` < `beta` < `delta` < `echo` < `gamma`).
- **Insertions:** 5 entries (`delta`, `alpha`, `echo`, `beta`, `gamma`).
- **Removals:** keys `"echo"` and `"alpha"` erased; 3 entries remain.

---

### Example 2a — `std::map<int32_t, std::string*>`

- **Key/Value:** `int32_t` key inline; value is a **heap-allocated** `std::string*`.
- **Heap allocations per entry:** 2 — one node, one `std::string` object.
- **Cleanup:** **manual**. The map destructor does not `delete` value pointers.
  Removal pattern: save the pointer → erase the iterator → `delete` the pointer.
  Remaining pointers are deleted in an explicit loop at end of scope.
- **Insertions:** keys `10`, `30`, `20`, `40`, `50` with string values.
- **Removals:** keys `30` and `10`; remaining 3 strings deleted before scope ends.

---

### Example 2b — `std::map<std::string, std::string*>`

- **Key/Value:** `std::string` key (SSO-dependent heap); value is a
  **heap-allocated** `std::string*`.
- **Heap allocations per entry:** up to 3 — node, key buffer (SSO overflow),
  value `std::string` object.
- **Cleanup:** **manual** for value pointers; keys and nodes freed automatically.
- **Insertions:** 5 entries (`color`, `shape`, `weight`, `size`, `speed`).
- **Removals:** keys `"shape"` and `"color"`; remaining 3 strings deleted explicitly.

---

### Example 3a — `std::map<int32_t, Point>`

- **Key/Value:** `int32_t` key and `Point` struct, both inline in the node.
- **Heap allocations per entry:** 1 (the node; `Point`'s 8 B live inside it).
- **Cleanup:** fully automatic — `~Point()` is trivial; destructor frees nodes.
- **Cache behaviour:** key and value are contiguous in memory — more
  cache-friendly than pointer-based storage.
- **Insertions:** keys `3`, `1`, `5`, `2`, `4` with `Point` values.
- **Removals:** keys `3` and `5`; 3 entries remain at scope end.

---

### Example 3b — `std::map<std::string, Point>`

- **Key/Value:** `std::string` key (SSO-dependent); `Point` struct inline.
- **Heap allocations per entry:** 1 node + 0 or 1 key buffer (SSO-dependent).
- **Cleanup:** fully automatic — `~std::string()` for keys, trivial `~Point()`.
- **Key ordering:** lexicographic (`bot_left` < `bot_right` < `origin` < `top_left`
  < `top_right`).
- **Insertions:** 5 named corner/origin points.
- **Removals:** keys `"origin"` and `"top_right"`; 3 entries remain.

---

### Example 4a — `std::map<int32_t, Person*>`

- **Key/Value:** `int32_t` key inline; value is a **heap-allocated** `Person*`.
- **Heap allocations per entry:** 2+ — one node (stores key + pointer), one
  `Person` object (which may itself allocate a heap buffer for `name_`).
- **Cleanup:** **manual**. The two-step pattern (erase iterator → `delete Person*`)
  triggers `~Person()`, which calls `~std::string()` on `name_` and releases
  the `Person` block. Remaining pointers are deleted in an explicit loop.
- **Non-copyable design:** `Person` deliberately forbids copying, enforcing
  pointer-based ownership semantics.
- **Insertions:** 5 persons — Alice (30), Bob (25), Charlie (35), Dave (40), Eve (28).
- **Removals:** keys `5` (Eve) and `1` (Alice); remaining 3 deleted explicitly.

---

### Example 4b — `std::map<std::string, Person*>`

- **Key/Value:** `std::string` key (SSO-dependent); **heap-allocated** `Person*`.
- **Heap allocations per entry:** up to 4 — node, key buffer, `Person` object,
  `name_` buffer — each conditional on string length vs. SSO threshold.
- **Cleanup:** **manual** for `Person*`; key strings and nodes freed automatically.
- **Key ordering:** lexicographic over lowercase handles (`alice`, `bob`, `charlie`,
  `dave`, `eve`).
- **Insertions:** same 5 persons as 4a, accessed via lowercase string keys.
- **Removals:** keys `"eve"` and `"charlie"`; remaining 3 deleted explicitly.
