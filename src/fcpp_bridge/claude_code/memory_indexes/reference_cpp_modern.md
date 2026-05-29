---
name: reference-cpp-modern
description: "C++ modern standards reference — C++14 focus (FCPP target), smart pointers, lambdas, templates, RAII, STL; skill at ~/.claude/commands/cpp-modern.md"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 30462d41-0a8b-4ed3-9933-02f384ad3e82
---

C++ modern standards knowledge collected from this project (FCPP uses **C++14** as its compile target).

## Primary skill file
`~/.claude/commands/cpp-modern.md` — invoke with `/cpp-modern` for full reference.

## Key C++14 features (used by FCPP)
- **Generic lambdas**: `[=](auto a, auto b){ return a + b; }` — C++14's most important addition for FCPP aggregate functions
- **`std::make_unique`**: available from C++14 (missing in C++11)
- **Return type deduction**: `auto compute() { return std::make_tuple(...); }`
- **Variable templates**: `template<typename T> constexpr T pi = T(3.14159...);`
- **Relaxed `constexpr`**: full function bodies (not just single return)
- **Init-capture lambdas**: `[val = std::move(expensive)](){ ... }`

## What to avoid when targeting C++14
- `if constexpr` → C++17
- Structured bindings → C++17
- `std::optional` / `std::variant` → C++17
- Concepts / Ranges → C++20
- Fold expressions in templates → C++17

## RAII and ownership
- Always prefer `std::unique_ptr` / `std::shared_ptr` over raw owning pointers
- Rule of Zero: let smart-member types handle the special members
- Rule of Five: if you declare any of {dtor, copy ctor, copy assign, move ctor, move assign}, declare all five
- `noexcept` is required on move operations and destructors for STL efficiency

## Template patterns used in FCPP internals
- `ARGS` expands to `(node_t& node, trace_t trace, ...)` via macro
- `FUN` marks aggregate functions; `CODE` initialises the call counter
- `CALL` expands to `node, trace_t{trace, ++call_point}`
- Generic lambdas used everywhere: `[&](auto key){ return std::make_pair(val, status); }`

## Include order (Google style, used in this project)
1. Related header
2. System headers `<vector>`, `<map>`, etc.
3. Third-party / FCPP headers
4. Project headers
