---
name: project-fcpp-export-list-rule
description: FCPP export_list bookkeeping rule — critical gotcha when adding new functions that use nbr()
metadata: 
  node_type: memory
  type: project
  originSessionId: 3bbcec65-fb79-4f48-bf88-dc1ba62b0b6a
---

**Rule:** In FCPP, every type used by `nbr()` (or any neighborhood aggregate) — transitively, through every function that `main` calls — must be listed in `main_t`'s `export_list`. This is manual bookkeeping; the compiler cannot infer it.

```cpp
FUN_EXPORT my_fun_t = export_list<MyType>;           // declare per-function exports
FUN_EXPORT main_t   = export_list<..., my_fun_t>;    // must include it here too
```

**Why:** The framework builds the network's `multitype_map` from `main_t`. If a type is missing, you get a `static_assert` failure at the `multitype_map::insert` call site:
> "unsupported type access (add type A to exports type list)"

**How to apply:** Whenever a new `FUN_EXPORT foo_t` is added for a function called by `main`, immediately add `foo_t` to `main_t`'s `export_list`. Forgetting this is the most common FCPP compile error.
