# fcpp_py — Summary

Python 3.x bindings for the [fcpp](https://github.com/fcpp/fcpp) C++14 aggregate computing library.
Uses the same **ctypes + C ABI bridge** pattern as `../expr_eval_py/`.

## Phase 1 scope: geometric vectors

Exposed types: `Vec2` (2D) and `Vec3` (3D) — wrappers around `fcpp::vec<2>` and `fcpp::vec<3>`.

| Operation | Vec2 | Vec3 |
|-----------|:----:|:----:|
| construction / element access | ✓ | ✓ |
| `norm()` | ✓ | ✓ |
| `unit()` | ✓ | ✓ |
| `distance(other)` | ✓ | ✓ |
| `dot(other)` | ✓ | ✓ |
| `+`, `-`, `*scalar`, `/scalar`, unary `-` | ✓ | ✓ |
| `==`, `!=` | ✓ | ✓ |
| `__iter__`, `__len__`, `__repr__` | ✓ | ✓ |

## File structure

```
fcpp_py_porting/
├── Makefile                 incremental build (GCC, -std=c++26)
├── src/bridge.cpp           C ABI bridge — only file that #includes fcpp headers
├── fcpp_py/__init__.py      ctypes loader + Vec2/Vec3 Python classes
├── fcpp_py/_fcpp.pyi        type stubs
├── tests/test_bindings.py   pytest tests
└── fcpp_clone_GITIGNORE_ME/ fcpp source (git-ignored, read-only)
```

## Quick start

```bash
# from src/fcpp_py_porting/ in MSYS2 bash:
mingw32-make test
```

## Key design choices

- ctypes (not pybind11): Python 3.14 = MSVC build; only GCC available → ABI mismatch
- C++26 compiler (`-std=c++26`), fcpp headers are C++14 — fully forward-compatible
- Bridge copies `double*` ↔ `fcpp::vec<N>.data` via `memcpy` (layout verified by `static_assert`)
- fcpp is header-only; only `bridge.cpp` compiles (fast build)
