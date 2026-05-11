# Explanation — Design choices for `expr_eval_py`

This document explains every significant choice made when building the Python
bindings, and which alternatives were considered but rejected.

---

## 1. Why ctypes instead of pybind11

**pybind11** is the most popular C++/Python binding library and would normally
be the first choice.  It generates clean, Pythonic bindings with almost no
boilerplate.  However it requires compiling an extension module (`.pyd` on
Windows) that is loaded directly into the Python interpreter.

**The ABI problem on this machine:**

| Component | Compiler |
|---|---|
| Python 3.14 at `C:\python314\` | MSVC (Microsoft Visual C++) |
| GCC 15.2.0 at MSYS2 UCRT64 | GNU g++ |

A `.pyd` extension must be compiled with the **same compiler** as the Python
interpreter it loads into.  Specifically:

- **C++ exception handling ABI** differs between MSVC (`__try`/`__except`,
  SEH) and GCC (`sjlj` or `DWARF`).  A C++ exception thrown in a GCC-compiled
  DLL and caught in MSVC code (or vice versa) is undefined behaviour — the
  program crashes silently.
- **Name mangling** differs between compilers.  A symbol exported as
  `_ZN7ExprEval10ParseErrorC1ERKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE`
  by GCC becomes `?ParseError@ExprEval@@QAA...` under MSVC.
- **`std::string` layout** can differ between `libstdc++` (GCC) and the MSVC
  STL, causing memory corruption if a `std::string` is created in one and
  destroyed in the other.

A **C ABI** (functions declared `extern "C"`, returning only `int`, `char*`,
etc.) is stable across all compilers: no name mangling, no C++ exception
propagation, no STL type sharing.  The boundary is clean and safe.

**ctypes** loads a plain DLL and calls C functions through it — the exact
mechanism needed here.

### Why not Cython

Cython 3.2.4 is installed and generates fast C extensions.  However Cython
generates `.pyd` files with the same ABI requirement as pybind11 — they must
be compiled with the Python's compiler (MSVC).  Wrapping C++ with Cython also
requires `.pxd` declaration files and is significantly more verbose for pure
binding work.

### Why not SWIG

SWIG is mature but generates large amounts of boilerplate code, its C++ support
is complex, and it has no advantage over ctypes for a simple function-boundary
bridge.

### Why not cffi

`cffi` is an alternative to `ctypes` with a cleaner API for inline C
declarations.  It is not installed and would require an extra `pip install`.
`ctypes` is part of the standard library — zero dependencies.

### When pybind11 IS the right choice

If this project were compiled with MSVC (via Visual Studio or `cl.exe`), or if
the Python used were the MSYS2 UCRT64 Python (compiled with the same GCC),
pybind11 would be the correct choice.  The binding code would be shorter and
the Python types (exceptions, default arguments) would be integrated more
naturally.

---

## 2. Why a C ABI bridge file (`bridge/bridge.cpp`)

All C++ complexity — exceptions, STL types, stream I/O — stays inside the
bridge and is converted to C types before crossing the language boundary:

```
C++26 library                bridge.cpp              Python
─────────────────────────────────────────────────────────────
ExprEval::ParseError   →  return EXPR_ERR_PARSE (int32)  →  ParseError (Python)
std::string message    →  strncpy to char[] buffer       →  str.decode()
std::map<str,str>      ←  char* keys[], char* values[]   ←  dict[str,str]
bool result            →  int32_t *result_out = 0 or 1   →  bool
std::cout output       →  CoutSuppressor redirects        →  (suppressed)
```

Every C++ exception is caught and converted to an error code + message string.
No C++ object ever crosses the `extern "C"` boundary.

---

## 3. Why `verbose=False` by default

The C++ `ExprEval::evaluate` function prints the full AST to `stdout` for every
call — a debugging aid in the C++ project.  From Python, this output is
unexpected and pollutes the terminal.

The bridge suppresses it by default using `CoutSuppressor`, a RAII object that
redirects `std::cout` to an `ostringstream` for the duration of the call.

```cpp
struct CoutSuppressor {
    std::ostringstream  sink;
    std::streambuf*     prev;
    CoutSuppressor()  : prev(std::cout.rdbuf(sink.rdbuf())) {}
    ~CoutSuppressor()   { std::cout.rdbuf(prev); }
};
```

When `verbose=True`, the suppressor is not used, and the AST prints normally.
This is exposed as a keyword-only argument (`*` in the Python signature) to
make it explicit:

```python
evaluate("v > 10", {"v": "15"}, verbose=True)   # correct
evaluate("v > 10", {"v": "15"}, True)            # TypeError — intentional
```

Keyword-only prevents accidental positional use where a plain bool could
be confused with a variable value.

---

## 4. Why `ParseError(ValueError)` and `EvaluationError(RuntimeError)`

Python has a well-defined exception hierarchy.  Mapping C++ exceptions to the
most semantically appropriate Python base class lets callers use standard
patterns without knowing the custom types:

```python
try:
    evaluate(user_input, vars)
except ValueError:
    # Invalid input — same branch as int("abc"), json.loads("{bad}")
    print("Bad expression")
except RuntimeError:
    # Runtime failure — same branch as other runtime errors
    print("Evaluation failed")
```

Mapping choices:

| C++ exception | Python base | Rationale |
|---|---|---|
| `ParseError` | `ValueError` | Malformed input — analogous to Python's own `ValueError` for bad inputs |
| `EvaluationError` | `RuntimeError` | Runtime type/state failure — not an input format error |

Alternatively both could inherit from a single `ExprEvalError(Exception)` base.
That would allow `except ExprEvalError` to catch both with one clause, but
loses the standard-library hierarchy integration.

---

## 5. Why `os.add_dll_directory()` instead of `PATH` manipulation

The DLL compiled with GCC depends on `libwinpthread-1.dll` from MSYS2.  Even
with `-static-libgcc -static-libstdc++`, `libstdc++.a` itself references
`libwinpthread-1.dll` internally, so it appears as a runtime dependency.

Options considered:

| Option | Verdict |
|---|---|
| Tell user to add MSYS2 to PATH | Fragile — relies on user environment, fails in virtual envs and CI |
| `os.environ["PATH"] += ";..."` before loading | Deprecated on Python 3.8+; `os.add_dll_directory` replaced it |
| Copy the DLL to `expr_eval_py/` + `os.add_dll_directory(package_dir)` | Chosen: self-contained, works without MSYS2 on PATH |
| Full static link with `-static` | `-static` links the entire CRT statically, which conflicts with the UCRT Python expects |

`os.add_dll_directory()` (Python 3.8+) registers a directory in the Windows
DLL search path for the duration of the process.  By calling it with the
package directory before `ctypes.CDLL(...)`, Windows finds `libwinpthread-1.dll`
next to the main DLL without any PATH change.

---

## 6. Runtime DLL copy: proper Make dependency target

The Makefile copies `libwinpthread-1.dll` via a proper Make dependency rule:

```makefile
$(WINPTHREAD_DST): $(WINPTHREAD_SRC)
    @mkdir -p $(dir $@)
    @cp -f "$<" "$@"
    @echo "Copied runtime: $@"
```

`all: $(LIB) $(RUNTIME_TARGET)` lists `$(WINPTHREAD_DST)` as a prerequisite on
Windows (`RUNTIME_TARGET := $(WINPTHREAD_DST)`) and nothing on Linux
(`RUNTIME_TARGET :=`).  Make only runs the copy when `$(WINPTHREAD_SRC)` is
newer than `$(WINPTHREAD_DST)`.

### Why the original approach used a shell recipe

The previous Makefile called `cp` unconditionally inside the `all` recipe
because the dependency rule:

```makefile
$(WINPTHREAD_DST): $(WINPTHREAD_SRC)
    cp $< $@
```

failed under GNU Make on MSYS2: Make appends `*` to the path of executable
files when it expands the rule, making the source path
`/c/msys64/ucrt64/bin/libwinpthread-1.dll*` — a glob that matches nothing.

### How the new approach avoids the problem

`WINPTHREAD_SRC` is now constructed from `MSYSTEM_PREFIX` (an environment
variable MSYS2 always exports, e.g., `/ucrt64`), not via wildcard or `ls`:

```makefile
PREFIX         := $(if $(MSYSTEM_PREFIX),$(MSYSTEM_PREFIX),/ucrt64)
WINPTHREAD_SRC := $(PREFIX)/bin/libwinpthread-1.dll
```

Make evaluates `$(WINPTHREAD_SRC)` as a plain string — no `*` appended — so
the dependency rule works correctly.  As a bonus the path adapts to whatever
MSYS2 subsystem is active (UCRT64, MINGW64, …) instead of being hardcoded.

---

## 7. Incremental compilation with object files

The Makefile compiles each source file separately into an object file under
`build/`, then links them in one step:

```makefile
CPPFLAGS    := -MMD -MP
OBJ_DIR     := build
OBJS_CORE   := $(patsubst $(EXPR_EVAL_ROOT)/src/%.cpp, $(OBJ_DIR)/src/%.o, $(LIB_SRCS_CORE))
OBJS_BRIDGE := $(patsubst bridge/%.cpp, $(OBJ_DIR)/bridge/%.o, $(LIB_SRCS_BRIDGE))
DEPS        := $(OBJS:.o=.d)

$(LIB): $(OBJS)
    $(CXX) $(CXXFLAGS) $(LDFLAGS) $^ -o $@

$(OBJ_DIR)/src/%.o: $(EXPR_EVAL_ROOT)/src/%.cpp
    $(CXX) $(CPPFLAGS) $(CXXFLAGS) $(INC) -c $< -o $@

$(OBJ_DIR)/bridge/%.o: bridge/%.cpp
    $(CXX) $(CPPFLAGS) $(CXXFLAGS) $(INC) -c $< -o $@

-include $(DEPS)
```

### Why this replaced one-step compilation

The previous Makefile compiled all 11 sources in a single `g++` invocation —
simple but not incremental.  Any change to any file (including headers) forced
a full rebuild.

The separate-compilation approach:

- Rebuilds only modified translation units.
- `-MMD` generates a `.d` dependency file per `.o` at compile time, listing
  every header the translation unit included.
- `-MP` adds phony targets for headers so Make does not error if a header is
  deleted between builds.
- `-include $(DEPS)` silently loads all `.d` files; the `-` prefix suppresses
  errors on first build (before any `.d` file exists).

This is the same pattern used by `../expr_eval/multiclass/Makefile`.

### Trade-offs

| Approach | Simplicity | Incremental | Header-change aware |
|---|---|---|---|
| One-step (old) | ✅ | ❌ | ❌ |
| Object files (new) | moderate | ✅ | ✅ via `-MMD -MP` |

For 11 source files the difference in rebuild time is modest, but the approach
scales correctly as the library grows and avoids stale-header bugs.

---

## 8. Why `variables` defaults to `None` not `{}`

In Python, mutable default arguments are evaluated **once** at function
definition time and shared across all calls:

```python
def bad(variables={}):   # same dict object for every call — bug waiting to happen
    variables["x"] = "1"

def good(variables=None):
    if variables is None:
        variables = {}   # fresh dict each call
```

The `evaluate` wrapper uses `variables or {}` which creates a fresh empty
dict each call when `None` is passed.

The ctypes default argument `py::arg("variables") = ExprEval::Variables{}`
(if this were pybind11) would be safe because C++ creates a new `Variables`
object per call.  For our pure-Python wrapper the `None` pattern is the
correct idiom.

---

## 9. Why type stubs (`.pyi` file)

`_expr_eval.pyi` provides type information for static analysis tools (mypy,
pyright, VS Code IntelliSense).  Without it, tools see `evaluate` as returning
`Any` and cannot warn about wrong argument types.

With the stub:
```python
result = evaluate("v > 1", {"v": "yes"})   # mypy: OK (str values are valid)
result = evaluate("v > 1", {"v": 42})      # mypy: error — int not str
result + " text"                            # mypy: error — bool + str
```

The stub is separate from `__init__.py` to avoid the runtime overhead of
importing typing machinery in production code.

---

## 10. Summary — alternatives comparison table

| Approach | Works on this machine | Extra install needed | Code complexity | Type safety |
|---|---|---|---|---|
| **ctypes + C bridge** (chosen) | ✅ | none | medium | via .pyi stubs |
| pybind11 | ❌ (ABI mismatch) | pybind11 + cmake | low | auto-generated |
| Cython | ❌ (ABI mismatch) | nothing (installed) | high (.pyx syntax) | medium |
| SWIG | ❌ (ABI mismatch) | SWIG | very high | auto-generated |
| cffi | ✅ | cffi | low-medium | via stubs |
| nanobind | ❌ (ABI mismatch) | nanobind + cmake | low | auto-generated |

**ctypes** wins precisely because it operates at the OS DLL level rather than
the Python C extension level — the compiler ABI does not matter.

---

## 11. Cross-platform Makefile design

The Makefile must produce a `.dll` on Windows and a `.so` on Linux from the
same source files.  The key differences between the two platforms:

| Aspect | Windows (MSYS2) | Linux |
|---|---|---|
| Shared library suffix | `.dll` | `.so` |
| Position-independent code | not needed (PE format) | `-fPIC` mandatory |
| GCC runtime dep | `libwinpthread-1.dll` (must be copied) | glibc (system-provided) |
| Make binary | `mingw32-make` | `make` |
| Python interpreter | `command -v python3` → `command -v python` (unified; detected before the platform `ifeq` block) | ← same |

### Platform detection

GNU Make sets `$(OS)` to `Windows_NT` on all Windows hosts (including MSYS2
and Cygwin).  On Linux and macOS it is unset.  This is the idiomatic detection:

```makefile
# Python detection is platform-independent — placed before the ifeq block.
PYTHON := $(shell command -v python3 2>/dev/null || command -v python 2>/dev/null)

ifeq ($(OS),Windows_NT)
    LIB_SUFFIX := .dll
    ...
else
    LIB_SUFFIX := .so
    CXXFLAGS   += -fPIC
    ...
endif
```

`command -v` is a POSIX shell built-in that locates executables on PATH without
invoking an external process.  It is available in both MSYS2 bash and Linux
bash.  `2>/dev/null` silences the "not found" message so Make gets an empty
string on miss rather than an error.  The `||` chain tries `python3` first on
both platforms; `python` is the fallback.

### Why `-fPIC` on Linux only

Position-independent code (PIC) means the shared library's text segment can
be loaded at any virtual address.  On Linux/ELF, this is **required** for
`.so` files — without it the dynamic linker may crash.  On Windows/PE, the
format handles relocation differently; `-fPIC` is unnecessary and slightly
slower (it adds an indirection layer for every global access).

### Why GCC runtime embedding differs

On Windows, `libstdc++` internally references `libwinpthread-1.dll` even
when `-static-libstdc++` is used.  No linker flag eliminates this; the DLL
must be distributed alongside the main DLL.  `os.add_dll_directory()` in
`__init__.py` ensures Python finds it.

On Linux, `libstdc++` and `libgcc` can be fully embedded with
`-static-libgcc -static-libstdc++`.  The only runtime dependency remaining
is glibc (`libc.so.6`), which is always present on any Linux system.  No
extra file copy is needed.

### RUNTIME_TARGET and CLEAN_RUNTIME variables

The runtime copy uses two platform-specific variables.  `RUNTIME_TARGET` is
set to `$(WINPTHREAD_DST)` on Windows and left empty on Linux; `CLEAN_RUNTIME`
is a shell command used inside the `clean` recipe:

```makefile
ifeq ($(OS),Windows_NT)
    RUNTIME_TARGET := $(WINPTHREAD_DST)
    CLEAN_RUNTIME   = rm -f "$(WINPTHREAD_DST)"
else
    RUNTIME_TARGET :=
    CLEAN_RUNTIME   = :
endif

all: $(LIB) $(RUNTIME_TARGET)
```

On Linux `$(RUNTIME_TARGET)` expands to nothing, so `all` only depends on
`$(LIB)`.  On Windows, Make tracks whether `$(WINPTHREAD_DST)` is up-to-date
with respect to `$(WINPTHREAD_SRC)` and skips the copy when it is.

`CLEAN_RUNTIME` remains a shell-command variable (not a Make target) because
`clean` is always phony — no dependency tracking is needed there.  `:` is the
POSIX no-op built-in; it silently does nothing on Linux.
