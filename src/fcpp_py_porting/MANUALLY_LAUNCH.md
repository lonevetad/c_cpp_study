# Manual Launch Guide — fcpp_py_porting

This document describes all steps to manually test the C++ bridge, Python bridge, and build/run the chain_decaying example in the original C++ way.

## Prerequisites

### Windows (MSYS2 UCRT64)
```bash
# Required tools
pacman -S mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-make mingw-w64-ucrt-x86_64-cmake mingw-w64-ucrt-x86_64-lld
```

### Linux (Ubuntu/Mint)
```bash
# Install dependencies
sudo apt-get install build-essential cmake python3 python3-dev python3-pip
# Install pytest for Python tests
pip3 install pytest
```

---

## 1. Manual Testing of C++ Bridge

### 1.1 Compile bridge.cpp manually

The bridge is a C ABI wrapper around fcpp vector operations (Vec2, Vec3).

**Windows (MSYS2):**
```bash
cd src/fcpp_py_porting

# Ensure build directory exists
mkdir -p build

# Compile bridge.cpp
g++ -std=c++26 -O2 -fPIC -Wall -Wextra -MMD -MP \
    -I fcpp_clone_GITIGNORE_ME/src \
    -I fcpp_clone_GITIGNORE_ME/src/external \
    -c src/bridge.cpp -o build/bridge.o
```

**Linux:**
```bash
cd src/fcpp_py_porting
mkdir -p build

# Same as Windows
g++ -std=c++26 -O2 -fPIC -Wall -Wextra -MMD -MP \
    -I fcpp_clone_GITIGNORE_ME/src \
    -I fcpp_clone_GITIGNORE_ME/src/external \
    -c src/bridge.cpp -o build/bridge.o
```

### 1.2 Link to create the C bridge library

**Windows (creates `.dll`):**
```bash
# Create the DLL
g++ -shared -static-libgcc -static-libstdc++ \
    -Wl,--gc-sections -fuse-ld=lld \
    -o fcpp_py/_fcpp_core.dll build/bridge.o
```

**Linux (creates `.so`):**
```bash
# Create the shared library
g++ -shared -static-libgcc -static-libstdc++ \
    -Wl,--gc-sections -fuse-ld=lld \
    -o fcpp_py/_fcpp_core.so build/bridge.o
```

### 1.3 Test C bridge with Python ctypes

```python
import ctypes
from pathlib import Path

# Load the library
lib_path = Path("fcpp_py/_fcpp_core.dll")  # or .so on Linux
lib = ctypes.CDLL(str(lib_path))

# Get version
lib.fcpp_py_version.restype = ctypes.c_char_p
version = lib.fcpp_py_version().decode()
print(f"Bridge version: {version}")

# Test Vec2 norm (3,4 should be 5)
lib.fcpp_vec2_norm.restype = ctypes.c_double
lib.fcpp_vec2_norm.argtypes = [ctypes.POINTER(ctypes.c_double)]
v = (ctypes.c_double * 2)(3.0, 4.0)
norm = lib.fcpp_vec2_norm(v)
print(f"Vec2(3,4) norm: {norm}")  # Should print 5.0
```

---

## 2. Manual Testing of Python Bridge

### 2.1 Run Python tests (Phase 1: Vec2/Vec3)

```bash
cd src/fcpp_py_porting

# Run all Phase 1 tests (55 tests for Vec2/Vec3)
python -m pytest tests/test_bindings.py -v

# Run specific test
python -m pytest tests/test_bindings.py::test_vec2_norm_345 -v
```

**Expected output:**
```
55 passed in 0.64s
```

### 2.2 Run Python tests (Phase 2: Simulation)

```bash
# Run all Phase 2 tests (16 tests for Simulation)
python -m pytest tests/test_simulation.py -v

# Or run with compact output
python -m pytest tests/test_simulation.py -q
```

**Expected output:**
```
16 passed in X.XXs
```

### 2.3 Run comprehensive tests

```bash
# All advanced tests (25 comprehensive tests)
python -m pytest tests/test_comprehensive.py -v
```

### 2.4 Run entire test suite

```bash
# All 96 tests (55 Phase 1 + 16 Phase 2 + 25 comprehensive)
python -m pytest tests/ -v --tb=short

# Or compact output
python -m pytest tests/ -q
```

**Expected output:**
```
96 passed in 0.72s
```

### 2.5 Manual Python API test

```python
from fcpp_py import Vec2, Vec3, Simulation, version

# Test vectors
print(f"Version: {version()}")

v2 = Vec2(3.0, 4.0)
print(f"Vec2 norm: {v2.norm()}")  # Should be 5.0
print(f"Vec2 unit: {v2.unit()}")

v3 = Vec3(1.0, 2.0, 3.0)
print(f"Vec3 norm: {v3.norm()}")
print(f"Vec3.x: {v3.x}, Vec3.y: {v3.y}, Vec3.z: {v3.z}")

# Test simulation
print(f"Compile info: {Simulation.compile_info()}")

with Simulation() as sim:
    # Step to spawn devices
    if sim.next_time() >= 0:
        sim.step()
    print(f"Device count: {sim.device_count()}")
    ids = sim.get_ids()
    print(f"Device IDs: {ids[:3]}...")
```

### 2.6 Run example: averaging simulation

```bash
cd src/fcpp_py_porting

# Run the averaging example
python examples/averaging.py
```

**Expected output:**
```
Simulation compile-time config:
  State size:  8 doubles/device
  Max devices: 100
  Dimension:   3D

Created simulation with XXX devices

Running simulation (manual stepping):
  Step 1: time=0.0123, devices=100, avg_state[0]=0.000123
  ...
```

---

## 3. Manual Build and Run of chain_decaying Example

The `chain_decaying` example demonstrates the original FCPP way of building a C++ simulation with the full interactive GUI (requires OpenGL).

### 3.1 Structure

```
examples/
├── chain_decaying.cpp      # Main program (interactive_simulator with GUI)
├── chain_decaying.hpp      # Coordination algorithm (chain decaying)
└── (no build files yet)
```

### 3.2 Build chain_decaying manually

Since fcpp uses CMake, we need to set up a minimal CMakeLists.txt for the example.

**Create `examples/CMakeLists.txt`:**
```cmake
cmake_minimum_required(VERSION 3.18)
project(fcpp_chain_decaying CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Include fcpp headers from git-ignored clone
include_directories(${CMAKE_SOURCE_DIR}/../fcpp_clone_GITIGNORE_ME/src)
include_directories(${CMAKE_SOURCE_DIR}/../fcpp_clone_GITIGNORE_ME/src/external)

# Build executable
add_executable(chain_decaying
    chain_decaying.cpp
)

# Link OpenGL/X11 (required by fcpp for GUI)
if(NOT WIN32)
    find_package(X11 REQUIRED)
    find_package(OpenGL REQUIRED)
    target_link_libraries(chain_decaying
        X11::X11
        OpenGL::GL
    )
endif()

# For Windows, OpenGL comes from CMake
if(WIN32)
    find_package(OpenGL REQUIRED)
    target_link_libraries(chain_decaying
        OpenGL::GL
    )
endif()
```

**Compile (from `examples/` folder):**

**Windows (MSYS2):**
```bash
cd examples

# Create build directory
mkdir -p build
cd build

# Configure with CMake (C++14, as per fcpp requirement)
cmake -G "Unix Makefiles" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_STANDARD=14 \
    ..

# Build
mingw32-make -j4

# Output: ./chain_decaying.exe (or chain_decaying on Linux)
```

**Linux:**
```bash
cd examples

mkdir -p build
cd build

# Configure (requires X11 and OpenGL development packages)
cmake -G "Unix Makefiles" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_STANDARD=14 \
    ..

# Build
make -j4

# Output: ./chain_decaying
```

### 3.3 Run chain_decaying

**Windows:**
```bash
cd examples/build

# Run the executable
./chain_decaying.exe
```

**Linux:**
```bash
cd examples/build

# Run the executable
./chain_decaying
```

**What to expect:**
- An interactive GUI window opens (requires X11/OpenGL)
- Chain decaying simulation runs with visualized nodes
- Left click to interact with the simulation
- Close the window to exit

**Headless output (redirect to file):**
```bash
# Generate plot file instead of GUI
./chain_decaying > chain_decaying_output.txt 2>&1

# This creates plot data suitable for Asymptote visualization
```

### 3.4 Alternative: Build all fcpp examples at once

If you want to build the full fcpp test suite:

**Windows (MSYS2):**
```bash
cd fcpp_clone_GITIGNORE_ME

# Use fcpp's build system
./make.sh

# Or with CMake:
mkdir -p build
cd build
cmake -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release ..
mingw32-make -j4

# Tests will be in build/test/
```

**Linux:**
```bash
cd fcpp_clone_GITIGNORE_ME

./make.sh

# Or:
mkdir -p build
cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j4
```

---

## 4. Complete Build Pipeline with Makefile

The project includes a comprehensive Makefile that automates everything:

### 4.1 Build everything

**Windows:**
```bash
cd src/fcpp_py_porting
mingw32-make all
```

**Linux:**
```bash
cd src/fcpp_py_porting
make all
```

This will:
1. Compile `bridge.cpp` → `build/bridge.o`
2. Compile `simulation.cpp` → `build/simulation.o`
3. Link → `fcpp_py/_fcpp_core.dll` (Windows) or `.so` (Linux)
4. Copy `libwinpthread-1.dll` (Windows only)

### 4.2 Run all tests

```bash
mingw32-make test  # Windows
make test          # Linux
```

### 4.3 Clean build

```bash
mingw32-make clean  # Windows
make clean          # Linux
```

---

## 5. Troubleshooting

### LLD Linker Errors

If you get `error: unknown argument: --no-keep-memory`, the LLD linker doesn't support this flag.

**Fix:** Update Makefile to remove `--no-keep-memory`:
```makefile
# OLD:
LDFLAGS := ... -Wl,--gc-sections,--no-keep-memory ...

# NEW:
LDFLAGS := ... -Wl,--gc-sections ...
```

### Missing Python Headers

On Linux, if Python tests fail:
```bash
# Install Python development headers
sudo apt-get install python3-dev
```

### Missing Dependencies (Linux)

For chain_decaying with GUI:
```bash
# X11 development
sudo apt-get install libx11-dev

# OpenGL development
sudo apt-get install libgl1-mesa-dev
```

### Windows PATH issues

If `mingw32-make` is not found:
```powershell
# Add MSYS2 to PATH in PowerShell:
$env:PATH = "C:\msys64\ucrt64\bin;$env:PATH"

# Or use full path:
C:\msys64\ucrt64\bin\mingw32-make.exe all
```

---

## 6. Summary Table

| Task | Command | Platform | Output |
|------|---------|----------|--------|
| Compile bridge | `g++ -c src/bridge.cpp ...` | Both | `build/bridge.o` |
| Link bridge | `g++ -shared ... build/bridge.o ...` | Both | `fcpp_py/_fcpp_core.dll/.so` |
| Test Phase 1 | `pytest tests/test_bindings.py -v` | Both | 55 passed |
| Test Phase 2 | `pytest tests/test_simulation.py -v` | Both | 16 passed |
| Test All | `pytest tests/ -q` | Both | 96 passed |
| Build all | `mingw32-make all` (Wnd) or `make all` (Lnx) | Both | DLL/SO + runtime |
| Run tests | `mingw32-make test` or `make test` | Both | Full test suite |
| Build chain_decaying | `cmake ..` && `make -j4` | Both | `chain_decaying` executable |
| Run chain_decaying | `./chain_decaying` | Both | Interactive GUI (requires OpenGL) |

---

## 7. Environment Variables & Configuration

### Build Configuration (Makefile override parameters)

```bash
# Override simulation parameters at compile time
mingw32-make DEVICES=50 SIDE=100 COMM=30 all

# Parameters:
# - DEVICES: number of devices (default: 100)
# - SIDE: spatial domain width (default: 200)
# - HEIGHT: spatial domain height (default: 10)
# - COMM: communication radius (default: 50)
# - DIM: spatial dimension (default: 3)
# - STATES: state array size per device (default: 8)
# - CXXSTD: C++ standard (default: c++26)
```

### Python Environment

```bash
# Use virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux
venv\Scripts\activate     # Windows

# Install test dependencies
pip install pytest

# Run tests
pytest tests/ -v
```

---

## 8. Development Workflow

### After editing bridge.cpp:
```bash
g++ ... -c src/bridge.cpp -o build/bridge.o
g++ -shared ... -o fcpp_py/_fcpp_core.dll build/bridge.o
python -m pytest tests/test_bindings.py -v
```

### After editing simulation.cpp:
```bash
g++ ... -c src/simulation.cpp -o build/simulation.o
g++ -shared ... -o fcpp_py/_fcpp_core.dll build/bridge.o build/simulation.o
python -m pytest tests/test_simulation.py -v
```

### After editing examples/chain_decaying.cpp:
```bash
cd examples/build
cmake ..
mingw32-make  # or make
./chain_decaying
```

---

**Last updated:** May 1, 2026  
**C++ Standard:** C++26 (bridge), C++14 (fcpp and examples)  
**Python Version:** 3.8+
