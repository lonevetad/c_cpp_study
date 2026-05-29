---
name: project-build-cross-platform
description: Cross-platform build patterns for the Makefiles and CMakeLists in this project (Windows/Linux/macOS)
metadata: 
  node_type: memory
  type: project
  originSessionId: e0e1ffd8-f841-4b03-8663-5d988f484735
---

## Platform detection pattern (Makefiles)

```makefile
UNAME_S := $(shell uname -s 2>/dev/null)

ifeq ($(OS),Windows_NT)        # MSYS2 / MinGW
    ...
else ifeq ($(UNAME_S),Darwin)  # macOS
    ...
else                           # Linux / other POSIX
    ...
endif
```

`$(OS)` is set to `Windows_NT` by Windows (including MSYS2). On Linux/macOS it is empty, so `uname -s` is the discriminator.

## Shared library suffixes per platform

| Platform | Suffix  | Linker flag    |
|----------|---------|----------------|
| Windows  | `.dll`  | `-shared`      |
| macOS    | `.dylib`| `-dynamiclib`  |
| Linux    | `.so`   | `-shared`      |

**macOS ctypes loaders must ask for `.dylib`** — `sys.platform == "darwin"` check already in `expr_eval_py/__init__.py`; added to `fcpp_py/__init__.py` in 2026-05-23 session.

## macOS-specific linker flags

- Use `-Wl,-dead_strip` instead of `-Wl,--gc-sections` (Apple ld64 does not support `--gc-sections`)
- Do NOT use `-static-libgcc` or `-static-libstdc++` (GCC flags; Apple clang has no `libgcc`)
- Do NOT use `-fuse-ld=lld` (Apple ld64 is the default; lld not installed by default)
- `-fPIC` is the default on macOS — including it is harmless but redundant

## CMakeLists: X11 vs OpenGL per platform

macOS has no X11 by default. Always use three-way guard:
```cmake
if(APPLE)
    find_package(OpenGL REQUIRED)
    target_link_libraries(target OpenGL::GL)
elseif(WIN32)
    find_package(OpenGL REQUIRED)
    target_link_libraries(target OpenGL::GL)
else()  # Linux
    find_package(X11 REQUIRED)
    find_package(OpenGL REQUIRED)
    target_link_libraries(target X11::X11 OpenGL::GL)
endif()
```

`if(NOT WIN32)` is **wrong** for macOS — it requires X11 which macOS lacks.

## LLD linker policy

- **Windows**: always use `-fuse-ld=lld` (BFD ld crashes on large COMDAT tables from fcpp templates)
- **Linux**: use `-fuse-ld=lld` only when lld is installed (`command -v lld` or `shutil.which("lld")`)
- **macOS**: never use `-fuse-ld=lld`

## Files changed in 2026-05-23 cross-platform session

| File | Change |
|------|--------|
| `src/fcpp_py_porting/Makefile` | Added macOS branch; removed hardcoded `/c/Users/ottin/…` LLD path |
| `src/fcpp_py_porting/fcpp_py/__init__.py` | Added `elif _system == "Darwin": .dylib` branch |
| `src/expr_eval_py/Makefile` | Added macOS branch (Python loader already expected `.dylib`) |
| `src/fcpp_py_porting/examples/CMakeLists.txt` | Added `if(APPLE)` branch; removed X11 requirement on macOS |
| `src/fcpp_bridge/compiler/__init__.py` | `-fuse-ld=lld` now platform-conditional |

**Why:** How to apply: whenever adding a new Makefile or CMakeLists.txt, always include the three-way platform guard. Never use `if(NOT WIN32)` as a proxy for "Linux-only" — that is broken on macOS.
