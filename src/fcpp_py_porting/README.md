# fcpp_py — Python bindings for FCPP

Python 3.8+ bindings for the **fcpp** (Field Calculus C++ framework) aggregate computing library. Uses **ctypes + C ABI** for cross-platform compatibility.

## Quick start

```bash
# Windows (MSYS2)
cd src/fcpp_py_porting
mingw32-make test

# Linux
cd src/fcpp_py_porting
make test
```

## Features

### Phase 1: Vector algebra
- **Vec2, Vec3** — 2D/3D vector math
- Operations: `+`, `-`, `*` (scalar), `/` (scalar), `.norm()`, `.dot()`, `.distance()`, `.unit()`
- Properties: `.x`, `.y`, `.z` (read-only)
- Indexing: `v[0]`, `v[1]` (read/write)

### Phase 2: Aggregate simulation
- **Simulation** — generic fcpp network simulator with Python per-round callbacks
- Compile-time params: devices, spatial dimension, state size, communication radius
- Per-round callback: Python function receives device ID, simulation time, own state, neighbor IDs & states → returns updated state
- Methods: `run(time)`, `step()`, `get_all_states()`, `get_ids()`, `device_count()`
- Context manager support: `with Simulation() as sim: ...`

## Installation

### Build requirements
- **Windows 11 (MSYS2 UCRT64)**: GCC 15.2.0, mingw32-make, LLD linker
- **Linux (Ubuntu/Mint)**: GCC ≥ 15, make, standard build tools
- **Python**: 3.8+ (tested with 3.14 on Windows, 3.10+ on Linux)

### Install LLD (required for Windows linking)
```bash
# In MSYS2 terminal:
pacman -S mingw-w64-ucrt-x86_64-lld
```

### Build
```bash
cd src/fcpp_py_porting
mingw32-make all  # Windows
make all          # Linux
```

Output: `fcpp_py/_fcpp_core.dll` (Windows) or `_fcpp_core.so` (Linux)

### Test
```bash
mingw32-make test  # Windows
make test          # Linux
```

## Usage

### Vector math
```python
from fcpp_py import Vec2, Vec3

v2 = Vec2(3.0, 4.0)
print(v2.norm())      # → 5.0
print(v2.unit())      # → Vec2(0.6, 0.8)
print(v2 + Vec2(1, 0))  # → Vec2(4.0, 4.0)

v3 = Vec3(1, 2, 3)
print(v3.norm())      # → 3.742...
```

### Simulation
```python
from fcpp_py import Simulation

def aggregate_step(dev_id, time, self_state, neighbor_ids, neighbor_states):
    """Per-round callback."""
    if not neighbor_states:
        return self_state  # no neighbors: no change
    # Average with neighbors
    avg = [sum(n[i] for n in neighbor_states) / len(neighbor_states) 
           for i in range(len(self_state))]
    return [0.7*s + 0.3*a for s, a in zip(self_state, avg)]

with Simulation() as sim:
    print(f"Devices: {sim.device_count()}")
    print(f"Config: {Simulation.compile_info()}")
    
    sim.set_callback(aggregate_step)
    sim.run(2.0)  # run to time 2.0
    
    ids, states = sim.get_all_states()
    for dev_id, state in zip(ids[:5], states[:5]):
        print(f"Device {dev_id}: {state}")
```

## Architecture

### Phase 1 (Vec2/Vec3)
- **bridge.cpp**: C ABI wrapper around fcpp vector functions
- **Makefile**: compiles bridge.cpp → _fcpp_core.dll/.so
- **__init__.py**: ctypes bindings + Python Vec2/Vec3 classes

### Phase 2 (Simulation)
- **simulation.cpp**: Full fcpp simulation engine (network topology, round scheduling, neighbor message-passing)
- **vec_vararg.hpp**: C++20 compatibility fix — explicit template specializations for `vec<1,2,3>` to restore brace-init
- **Python callback**: C function pointer ↔ Python via ctypes
- **Simulation class**: High-level Python API wrapping C simulation functions

## Compile-time parameters

Edit `Makefile` before build to adjust:
```makefile
DEVICES ?= 100      # max devices (default 100)
SIDE    ?= 200      # spatial dimension XY (default 200)
HEIGHT  ?= 10       # Z height (default 10)
COMM    ?= 50       # communication radius (default 50)
DIM     ?= 3        # spatial dimension (default 3)
STATES  ?= 8        # per-device state array size (default 8)
```

Usage: `mingw32-make DEVICES=50 COMM=30 all`

## Testing

### Run all tests
```bash
mingw32-make test  # Windows
make test          # Linux
```

### Test coverage
- **Vec2/Vec3**: 55 tests (Phase 1, currently passing)
- **Simulation**: ~20 tests (Phase 2, requires successful build)

Run specific tests:
```bash
python -m pytest tests/test_bindings.py -v  # Vec2/Vec3
python -m pytest tests/test_simulation.py -v  # Simulation
```

## Examples

See `examples/` directory:
- `averaging.py` — Simple averaging aggregate function

Run:
```bash
python examples/averaging.py
```

## Known issues & limitations

### Windows linker
- **Issue**: `ld returned 5 exit status` crash when linking large COMDAT section tables
- **Fix**: Use LLD linker (`-fuse-ld=lld`) instead of BFD ld
- **Install**: `pacman -S mingw-w64-ucrt-x86_64-lld`

### C++ standard
- Requires **C++26** for full fcpp feature support
- C++20 aggregate init incompatibility fixed via `vec_vararg.hpp` specializations

### Why ctypes, not pybind11/nanobind?
Python 3.14 on Windows = MSVC build; GCC on Linux = ABI mismatch. C ABI (`extern "C"`) is compiler-neutral and works across MSVC/GCC.

## File structure

```
src/fcpp_py_porting/
├── CLAUDE.md               Project context & documentation
├── README.md               This file
├── Makefile                Build configuration
├── src/
│   ├── bridge.cpp          Vec2/Vec3 C ABI (Phase 1)
│   ├── simulation.cpp      Simulation C ABI (Phase 2)
│   └── vec_vararg.hpp      C++20 aggregate-init fix
├── fcpp_py/
│   ├── __init__.py         Main Python module (ctypes + classes)
│   └── _fcpp.pyi           Type stubs for IDE/mypy
├── tests/
│   ├── test_bindings.py    Vec2/Vec3 tests
│   └── test_simulation.py  Simulation tests
├── examples/
│   └── averaging.py        Example: averaging aggregate
├── build/                  ← Generated (build artifacts)
├── fcpp_clone_GITIGNORE_ME/← FCPP source (read-only)
└── summary.md, explanation.md  Technical deep-dives
```

## Status

| Component | Status | Tests |
|-----------|--------|-------|
| Vec2/Vec3 | ✓ Complete | 55/55 passing |
| Simulation | ⚠ Complete (awaiting LLD build) | ~20 tests ready |

## Development notes

### C ABI design
- All exported functions use `extern "C"` for symbol stability
- All pointer arguments are validated at module boundary (bridge, simulation)
- Python callbacks are wrapped via `ctypes.CFUNCTYPE` with proper lifetime management
- No C++ exceptions cross the boundary (all wrapped in try-catch)

### Threading
- Simulation uses `parallel<false>` (single-threaded)
- Python callbacks are thread-safe by virtue of GIL
- Multi-threaded simulation possible with `parallel<true>` but requires callback thread-safety

### Performance
- Vec math: direct ctypes calls, minimal overhead
- Simulation: per-round callback latency dominated by fcpp's template instantiation, not ctypes bridge
- Compile-time parameters can dramatically affect performance (e.g., larger COMM radius = more neighbors = more callback work)

## License & Attribution

- **fcpp** source: read-only, in `fcpp_clone_GITIGNORE_ME/` (not included in repo)
- **fcpp_py bindings**: custom work

## See also

- `explanation.md` — design rationale & technical deep-dives
- `summary.md` — feature summary & changelog
- `CLAUDE.md` — project context & build environment details
