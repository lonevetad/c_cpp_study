# fcpp_py — Design Decisions

## §1 Why ctypes, not pybind11 / nanobind / Cython

The machine has:
- Python 3.14.0 compiled with **MSVC** (`python314.dll`, `vcruntime140.dll` in its ABI)
- Only **GCC 15.2.0** (MSYS2 UCRT64) available as a compiler

pybind11 and nanobind produce C++ extension modules (`.pyd`) that must be compiled with the **same compiler** as the Python interpreter. A GCC-compiled `.pyd` against an MSVC Python runtime crashes at the C++ ABI boundary (different name mangling, exception models, STL layouts).

Cython generates C++ code that has the same problem.

**Solution:** ctypes + `extern "C"` bridge. The C ABI is stable across compilers: no name mangling, no C++ exceptions crossing the boundary, no STL types. The bridge DLL is a plain GCC shared library; Python loads it via `ctypes.CDLL` without knowing or caring what compiled it.

The same pattern was validated in `../expr_eval_py/` with 59 passing tests.

---

## §2 Why C++26 when fcpp is C++14

The user requirement is C++26. fcpp's C++14 headers are fully forward-compatible — C++26 is a strict superset. GCC 15.2.0 with `-std=c++26` compiles all used fcpp headers without warnings.

The bridge itself (`src/bridge.cpp`) uses only C++14-compatible constructs (templates, `std::is_same_v` from C++17, `noexcept`). The C++26 flag is present to satisfy the project requirement and would enable C++26 features if added in the future.

---

## §3 Memory layout: `double*` ↔ `fcpp::vec<N>.data`

`fcpp::vec<N>` is a plain struct:
```cpp
template <size_t n>
struct vec {
    real_t data[n];   // public C array, no padding, no vtable
};
```

`real_t` defaults to `double` (`FCPP_REAL_TYPE` macro in `settings.hpp`).

The bridge verifies this at compile time:
```cpp
static_assert(std::is_same_v<fcpp::real_t, double>);
static_assert(sizeof(fcpp::vec<2>) == 2 * sizeof(double));
static_assert(sizeof(fcpp::vec<3>) == 3 * sizeof(double));
```

This allows zero-copy load/store between `const double*` (C ABI) and `fcpp::vec<N>` via `memcpy`:
```cpp
template <size_t N>
static fcpp::vec<N> load(const double* p) noexcept {
    fcpp::vec<N> v;
    std::memcpy(v.data, p, N * sizeof(double));
    return v;
}
```

On the Python side, `Vec2._data` is a `ctypes.c_double * 2` instance. ctypes automatically converts it to `POINTER(c_double)` when passing to a function with that argtype — no explicit cast needed.

---

## §4 Why fcpp is header-only (for our use case)

fcpp's `.cpp` files (e.g., `vec.cpp`, `field.cpp`) are 3-line stub files that just `#include` the corresponding `.hpp`. All actual code is in the headers as templates. Since templates are instantiated at the call site, `bridge.cpp` includes only `lib/data/vec.hpp` and the linker gets everything it needs from that one translation unit.

No fcpp source files are compiled into the bridge. This keeps the build fast and simple.

---

## §5 Incremental compilation with object files

Same approach as `../expr_eval_py/Makefile`:

```makefile
OBJ_DIR  := build
CPPFLAGS := -MMD -MP    # auto-generate .d dependency files

$(OBJ_DIR)/%.o: src/%.cpp
    @mkdir -p $(dir $@)
    $(CXX) $(CXXFLAGS) $(CPPFLAGS) -c $< -o $@

-include $(DEPS)
```

`-MMD` writes `build/bridge.d` listing all headers `bridge.cpp` transitively includes. On re-`make`, if any of those headers changed, only `bridge.cpp` recompiles. With a single translation unit this matters less, but the pattern scales to Phase 2+.

---

## §6 Windows DLL loading: `os.add_dll_directory` + `libwinpthread-1.dll`

GCC's C++ runtime (`libstdc++`) pulls in `libwinpthread-1.dll` (POSIX thread primitives for MSYS2). Without it on the DLL search path, `ctypes.CDLL` raises `OSError`.

**Fix (same as expr_eval_py):**
1. Makefile copies `libwinpthread-1.dll` from `$MSYSTEM_PREFIX/bin/` into `fcpp_py/` alongside `_fcpp_core.dll`. This is a proper Make dependency target (rebuilds only when source is newer):
   ```makefile
   $(WINPTHREAD_DST): $(WINPTHREAD_SRC)
       @cp -f "$<" "$@"
   ```
2. `__init__.py` calls `os.add_dll_directory(str(_pkg))` before `ctypes.CDLL(...)`, so Windows searches `fcpp_py/` for dependencies. MSYS2 does not need to be on `PATH`.

On Linux: `libpthread` is part of glibc; no extra copy needed. `RUNTIME_TARGET :=` (empty) and `CLEAN_RUNTIME = :` (no-op).

---

## §7 Python class design: ctypes Array as `_data`

Each `Vec2` instance holds `self._data = ctypes.c_double * 2(x, y)` — a ctypes stack-allocated array. Benefits:
- No heap allocation per operation; the array is a Python object but lives in a fixed-size buffer
- Can be passed directly to `ctypes` functions expecting `POINTER(c_double)` (auto-conversion)
- `__slots__ = ("_data",)` prevents accidental attribute addition and saves memory

Result vectors use `_from_arr(arr)` classmethod to wrap an already-filled `_Arr2`/`_Arr3` without copying:
```python
@classmethod
def _from_arr(cls, arr):
    v = object.__new__(cls)
    v._data = arr
    return v
```

All arithmetic operators allocate a new `_Arr2`/`_Arr3`, call the bridge to fill it, then wrap it. The original operands are never mutated.

---

## §8 Why no CMake

`CMakeLists.tx` (user's draft) uses FetchContent + nanobind. This won't work on this machine (see §1). CMake is also not installed in the MSYS2 environment. The Makefile approach compiles in seconds with no additional tooling.

If nanobind becomes viable in the future (e.g., using MSVC or compiling Python with GCC), the `CMakeLists.tx` draft is a good starting point. Rename it to `CMakeLists.txt` and add `FetchContent_MakeAvailable(nanobind)` + `nanobind_add_module(...)`.

---

## §9 Why Phase 1 is Vec2 / Vec3 only

`fcpp::field<T>`, `fcpp::tagged_tuple`, and the coordination functions (`old`, `nbr`, `fold_hood`, etc.) are deeply template-bound and require a running FCPP simulation context (`node_t&`, `trace_t`). Exposing them through a C ABI requires wrapping the entire simulation loop, which is a significant undertaking (Phase 2+).

`fcpp::vec<N>` is a standalone value type with no dependencies on the simulation infrastructure — ideal for Phase 1 validation that the build pipeline and ctypes bridge work correctly.

---

## §10 Include path

```
-I fcpp_clone_GITIGNORE_ME/src
-I fcpp_clone_GITIGNORE_ME/src/external
```

`bridge.cpp` uses `#include "lib/data/vec.hpp"`. This resolves relative to the first `-I` path (`src/`), producing `src/lib/data/vec.hpp`. fcpp's internal `#include "lib/..."` chains work for the same reason. The `external/` path provides Eigen and other third-party headers pulled in by some fcpp headers.

Using `-I src/lib` instead would break internal includes (they start with `lib/`, not `data/`).
