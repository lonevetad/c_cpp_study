# scattered_database.cpp — Error Analysis & Fix Plan

Build errors captured in `scattered_database_build_errors.log`.

## How to capture build errors

From the `fcpp-exercises/` directory:

```bash
./make.sh gui run -O scattered_database > build_errors.log 2>&1
```

`2>&1` redirects stderr (where the compiler writes diagnostics) into the same file as stdout. Equivalent with `tee` if you also want live terminal output:

```bash
./make.sh gui run -O scattered_database 2>&1 | tee build_errors.log
```

---

## Error catalogue

### E1 — `fcpp::get<N>(fcpp::vec<2>)` — lines 200, 200

**Error:**
```
error: no matching function for call to 'get<1>(s_db_data&)'
error: no matching function for call to 'get<0>(s_db_data&)'
```

**Location:** static `hash(s_db_data)` method inside the `scattered_db_response` hash helper (around line 197).

**Root cause:**  
`s_db_data = fcpp::vec<2>`. `fcpp::vec<N>` is an array-like type; it does **not** implement
`std::tuple_element` / `std::get<N>` — those are tuple-protocol traits. `fcpp::get<N>` works
on `fcpp::tuple` but not on `fcpp::vec`.

**FCPP/C++ rule learned:**  
> `fcpp::vec<N>` uses subscript access (`v[0]`, `v[1]`, …), NOT `get<N>(v)`.
> Only `fcpp::tuple<...>` supports `get<N>`.

**Fix:**
```cpp
// Before (wrong):
return (size_t(fcpp::get<1>(data_to_hash)) << offs) | size_t(fcpp::get<0>(data_to_hash));
// After (correct):
return (size_t(data_to_hash[1]) << offs) | size_t(data_to_hash[0]);
```

---

### E2 — `sp_collection` accumulator lambda by non-const reference — lines 396, 510

**Error:**
```
error: no matching function for call to 'sp_collection(..., <lambda(set_nodes_to_source_t&, set_nodes_to_source_t&)>)'
note: candidate: template<...> T sp_collection(...) [with typename = common::if_signature<G, T(T,T)>]
```

**Root cause:**  
`sp_collection` uses an FCPP SFINAE guard:
```cpp
// collection.hpp:73
template <..., typename G, typename = common::if_signature<G, T(T,T)>>
```
which expands to:
```cpp
typename = std::enable_if_t<std::is_convertible<G, std::function<T(T,T)>>::value>
```

`std::function<T(T,T)>` passes its arguments by value. A lambda that takes parameters
by **non-const reference** (`T& a, T& b`) cannot bind to the rvalue arguments that
`std::function` dispatch produces — so `is_convertible` returns `false` and the template is
SFINAE'd away (zero candidates → "no matching function").

Also: `std::set` has no `operator|`, so a generic `[](auto a, auto b){ return a | b; }` also
fails the `is_convertible` check (the lambda body would not compile for `std::set`).

**FCPP/C++ rule learned:**  
> `sp_collection`'s accumulator must satisfy `if_signature<G, T(T,T)>`.  
> Lambda parameters must be **by value** (or at most `const T&`).  
> Never use `operator|` on `std::set` — use `insert(begin, end)`.  
> Generic `auto` lambdas can fail the `is_convertible` check if the body doesn't compile  
> for the deduced `T`; use explicit types to make the check unambiguous.

**Fix:**
```cpp
// Both occurrences (line 401 and line 510):
// Before (wrong — by ref, no operator| on set):
[](set_nodes_to_source_t& a, set_nodes_to_source_t& b){ a.insert(b.begin(), b.end()); return a; }
// After (correct — by value):
[](set_nodes_to_source_t a, set_nodes_to_source_t b){ a.insert(b.begin(), b.end()); return a; }
```

---

### E3 — `spawn_res_query_map` key/value types swapped — lines 319, 422, 467, 468

**Error:**
```
error: conversion from
  'unordered_map<scattered_db_query, spawn_res_query, ...>'   ← what spawn actually returns
to
  'unordered_map<spawn_res_query, scattered_db_query, ...>'   ← what the alias claims
```

**Root cause:**  
FCPP `spawn(CALL, body, key_set)` returns:
```cpp
std::unordered_map<KEY_TYPE, BODY_RETURN_TYPE>
//                 ^KEY      ^VALUE
```
The spawn at line 422 has:
- Key type: `scattered_db_query` (the type of elements in `key_set`)
- Body return: `tuple<spawn_res_query, status>` → extracted value type = `spawn_res_query`

So spawn returns `unordered_map<scattered_db_query, spawn_res_query>`.

The existing definition was written with key and value **reversed** (the comment
`// map< returned_thing , key , hash_robe >` shows the confusion):
```cpp
// Wrong:
using spawn_res_query_map = std::unordered_map<spawn_res_query, scattered_db_query,
                                               common::hash<spawn_res_query>>;
```

Consequence: the for-loop at lines 466-469 had variable assignments **deliberately inverted**
(with a frustrated comment "LI HO INVETITI, PERCHé NON SI SA !!!! MALEDETTO COMPILATORE")
to compensate — which still didn't compile because the types are not symmetric.

**FCPP rule learned:**  
> `spawn(CALL, body, key_set)` → `std::unordered_map<KeyType, BodyReturnType>`  
> The FIRST template argument of the returned map is always the **KEY** (the type of  
> elements in `key_set`), the SECOND is the **value** (what the body returns, minus status).  
> Inverting them is a very common beginner mistake.

**Fix — line 319:**
```cpp
// Before (wrong):
using spawn_res_query_map = std::unordered_map<spawn_res_query, scattered_db_query,
                                               common::hash<spawn_res_query>>;
// After (correct):
using spawn_res_query_map = std::unordered_map<scattered_db_query, spawn_res_query,
                                               common::hash<scattered_db_query>>;
```

**Fix — lines 466-469 (C++14 branch):**  
With the corrected map, `kv.first = scattered_db_query`, `kv.second = spawn_res_query`.
The variable assignments are now correct as written — remove the compensating comment and
the wrong commented-out swapped version:
```cpp
// Correct after map fix:
scattered_db_query k = kv.first;
spawn_res_query    v = kv.second;
```

---

### E4 + E5 combined — `storage_init.hpp` rewrite (Steps 2)

**Error (propagated):**
```
basics.hpp:214:33: error: passing 'const node_t' as 'this' argument discards qualifiers [-fpermissive]
```

**Root cause:**  
`new_coprime_nbr_data` in `storage_init.hpp` is declared:
```cpp
template <typename node_t, typename F>
auto new_coprime_nbr_data(node_t const& node, trace_t call_point, F value_fn)
```

Every FCPP aggregate primitive (including `for_each_nbr`) internally calls
`node.stack_trace.push(...)` and similar **mutable** operations that update the call-trace
for the current round. Taking `node_t const&` prevents this — the compiler rejects it.

**FCPP rule learned:**  
> Every function that calls an FCPP primitive (even indirectly via CALL) **must** take  
> `node_t& node` (non-const mutable reference). `node_t const& node` is always wrong  
> for functions that use FCPP primitives internally.

**Fix — storage_init.hpp line 44:**
```cpp
// Before (wrong):
auto new_coprime_nbr_data(node_t const& node, trace_t call_point, F value_fn)
// After (correct):
auto new_coprime_nbr_data(node_t& node, trace_t call_point, F value_fn)
```

---

### E5 — `std::result_of<F>` / `std::invoke_result<F>` missing argument types — storage_init.hpp lines 46-54

**Error:**
```
type_traits:1151: error: invalid use of incomplete type 'struct std::result_of<lambda>'
type_traits:1159: error: static assertion failed: template argument must be a complete class
```

**Root cause:**  
`std::result_of<F>` and `std::invoke_result<F>` are **not** complete types on their own.
They are template metafunctions that require the call signature (argument types) to determine
the return type:

```cpp
// Wrong — argument types missing; result_of<F> is an incomplete type:
-> std::map<device_t, std::result_of<F>>       // C++14 branch
-> std::map<device_t, std::invoke_result<F>>   // C++17 branch

// Also wrong inside the body:
using V = std::result_of<F>;
using V = std::invoke_result<F>;
```

Correct forms:
- **C++14**: `typename std::result_of<F(node_t&)>::type`
- **C++17+**: `std::invoke_result_t<F, node_t&>`
- **Any standard via `decltype`**: `decltype(std::declval<F>()(std::declval<node_t&>()))`

The `#if __cplusplus <= 201402L` guards are intentional — the codebase is migrating from
C++14 toward C++26 and must compile correctly under both standards. The guards stay.
The fix is to add the missing call-signature argument type inside each branch:

**Fix — storage_init.hpp line 46 (C++14 trailing return type):**
```cpp
// Before: -> std::map<device_t, std::result_of<F>>
// After:
-> std::map<device_t, typename std::result_of<F(node_t&)>::type>
```

**Fix — storage_init.hpp line 48 (C++17+ trailing return type):**
```cpp
// Before: -> std::map<device_t, std::invoke_result<F>>
// After:
-> std::map<device_t, std::invoke_result_t<F, node_t&>>
```

**Fix — storage_init.hpp line 52 (C++14 body using-decl):**
```cpp
// Before: using V = std::result_of<F>;
// After:
using V = typename std::result_of<F(node_t&)>::type;
```

**Fix — storage_init.hpp line 54 (C++17+ body using-decl):**
```cpp
// Before: using V = std::invoke_result<F>;
// After:
using V = std::invoke_result_t<F, node_t&>;
```

---

## Fix plan (ordered by dependency)

All changes are minimal and surgical — no refactoring beyond what fixes the error.

`get<N>` on vec errors come first (Step 1), followed by `storage_init.hpp` fixes, then
the remaining `scattered_database.cpp` fixes.

| Step | File | Line(s) | Change |
|------|------|---------|--------|
| 1 | `run/scattered_database.cpp` | 200 | `fcpp::get<1>(data_to_hash)` → `data_to_hash[1]`; `fcpp::get<0>(data_to_hash)` → `data_to_hash[0]` |
| 2 | `run/storage_init.hpp` | 43-63 | Rewrite `new_coprime_nbr_data`: remove `auto` + trailing `->`, lift return type into template default `T`, add `if_signature` guard, keep `#if` guards (E4+E5) |
| 3 | `run/scattered_database.cpp` | 319 | Swap key/value in `spawn_res_query_map` alias |
| 4 | `run/scattered_database.cpp` | 401 | Lambda params `T& a, T& b` → `T a, T b` (by value) |
| 5 | `run/scattered_database.cpp` | 510 | Same lambda fix inside the response spawn |
| 6 | `run/scattered_database.cpp` | 466-469 | Clean up the compensating comment; variable assignments are now correct |

**Step 2 detail** — full rewrite of `new_coprime_nbr_data` following FCPP coding style:

```cpp
// BEFORE (broken — auto + trailing ->, const node, incomplete result_of):
template <typename node_t, typename F>
auto new_coprime_nbr_data(node_t const& node, trace_t call_point, F value_fn)
#if __cplusplus <= 201402L
    -> std::map<device_t, std::result_of<F>>
#else
    -> std::map<device_t, std::invoke_result<F>>
#endif
{
#if __cplusplus <= 201402L
    using V = std::result_of<F>;
#else
    using V = std::invoke_result<F>;
#endif
    std::map<device_t, V> result;
    ...
}

// AFTER (correct — explicit return type, if_signature guard, #if only in template params):
template <
    typename node_t,
    typename G,
#if __cplusplus <= 201402L
    typename T = typename std::result_of<G(node_t&)>::type,
#else
    typename T = std::invoke_result_t<G, node_t&>,
#endif
    typename = common::if_signature<G, T(node_t&)>
>
std::map<device_t, T> new_coprime_nbr_data(node_t& node, trace_t call_point, G value_fn)
{
    std::map<device_t, T> result;
    for_each_nbr(node, call_point, [&](device_t nbr_id) -> common::unit {
        if (is_coprime(nbr_id, node.uid))
            result.emplace(nbr_id, value_fn(node));
        return {};
    });
    return result;
}
```

Fixes both E4 (`const&` → `&`) and E5 (`result_of<F>` → correct signatures) in one rewrite.
`#if` guard appears exactly once (in template params); body has no conditionals.
`if_signature<G, T(node_t&)>` matches FCPP style for callables accepting a node reference.

### `get<N>` usage audit

All `get<N>` calls in `scattered_database.cpp` (excluding commented-out lines):

| Line | Call | Argument type | Verdict |
|------|------|---------------|---------|
| 200 (×2) | `fcpp::get<0>(data_to_hash)` / `fcpp::get<1>(data_to_hash)` | `s_db_data = fcpp::vec<2>` | **ERROR** — fix is Step 1 |
| 481 | `get<1>(v)` | `v: tuple<scattered_db_query, bool, s_db_data>` | Correct — `get` is on the tuple |
| 482 | `get<2>(v)` | same tuple `v` | Correct — element is `vec<2>` but `get` targets the tuple |

Steps 2, 3a, 3b must all be applied to `storage_init.hpp` before the cascade errors reduce.
Steps are otherwise independent and can be applied in any order within the same file.

---

## FCPP rules distilled from these errors

These rules are not in any FCPP tutorial; they were derived from compiler diagnostics:

1. **`fcpp::vec<N>` uses `[i]`, not `get<N>(v)`** — `get<N>` is for `fcpp::tuple` only.
2. **`sp_collection`/`mp_collection` accumulator must be `T(T,T)` compatible** — the SFINAE guard `if_signature<G, T(T,T)>` means the lambda must be convertible to `std::function<T(T,T)>`. Non-const ref parameters break this.
3. **`spawn` returns `map<KEY, VALUE>`** — KEY = key_set element type, VALUE = body return (minus status). Inverting them is the #1 beginner mistake.
4. **Every function using FCPP primitives must take `node_t&` (non-const)** — FCPP's trace stack is mutable. `const` qualification propagates and breaks all nested primitive calls.
5. **`std::result_of<F>` / `std::invoke_result<F>` require argument types** — `result_of<F(ArgType)>` / `invoke_result_t<F, ArgType>`. Without them the template specialization is incomplete and causes cascading `static_assert` failures.
6. **Prefer template default `T` + `if_signature` over `auto` with trailing `->` for callable-accepting functions** — FCPP style: declare `typename T = invoke_result_t<G, ArgType>` and `typename = common::if_signature<G, T(ArgType)>` as template parameters. The explicit return type `std::map<device_t, T>` replaces `auto`. When multi-standard `#if` guards are needed (C++14 vs C++17+), place the single guard inside the template parameter list — the function body and return type remain clean and guard-free.
