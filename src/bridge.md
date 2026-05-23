# FCPP Python-to-C++ Bridge — Comprehensive Design Document

**Status**: Architecture Phase (v0.1)  
**Last Updated**: 2026-05-23  
**Project**: `fcpp_bridge/` (to be created)

---

## Executive Summary

Building a production-ready bridge between Python and FCPP (Field Calculus C++14 framework) that allows Python programs to:

1. Define aggregate functions using a Python DSL
2. Transpile those functions to optimized C++ code
3. Dynamically compile and execute the generated code
4. Communicate with running swarms via flexible IPC (sockets, HTTP, gRPC, etc.)
5. Accept and execute programs from strings/files (via ANTLR parser)

**Key insight**: This is NOT a traditional binding. It's a **dynamic transpilation + JIT compilation** system where each Python program becomes a customized, compiled C++ swarm simulator.

---

## Part 1: Context & Constraints

### Current State (fcpp_py_porting)

- **Phase 1**: Vec2/Vec3 bindings (55 passing tests) ✅
- **Phase 2**: Simulation callback infrastructure (partial)
- **Key success**: ctypes + C ABI proven to work across MSVC/GCC
- **Key pain**: Simulation callbacks are Turing-complete but require C++ code generation

### Why Previous Attempt Had Challenges

1. **Planned for C++26, actual fcpp is C++14**: Mismatch between ambition and available primitives
2. **No compile-time type specification**: Python's dynamism conflicts with C++'s compile-time type requirements
3. **Callback-only approach limits expressivity**: Hard to capture complex aggregate logic in callbacks
4. **No code generation step**: Tried to hand-wire simulation instead of generating it

### Fundamental Constraint

**The C++ compiler needs to know, at compile time:**

- The exact types and structures each node will share
- The field types, tuple structures, and computations
- State persistence patterns

**Solution**: Generate monomorphic C++ code from Python DSL, one specialized binary per unique program signature.

---

## Part 2: Architecture Overview

### 6-Phase Implementation Plan

```
Phase 1: Python DSL Layer
  ↓ (transpile)
Phase 2: C++ Code Generator
  ↓ (serialize to disk)
Phase 3: Build Pipeline (CMake/GCC)
  ↓ (compile & link)
Phase 4: Runtime Library (IPC, serialization)
  ↓ (execute & communicate)
Phase 5: Language Parser (ANTLR)
  ↓ (parse programs from strings/files)
Phase 6: Scaling & Backends (HTTP, gRPC, plugins)
```

### High-Level Data Flow

```python
# Python side
program_str = """
aggregate_function_v1:
  initial_state: [0.0]
  compute: (self, neighbors) -> max(neighbors) + self
"""
          ↓ [ANTLR parse]
        AST
          ↓ [Python DSL validate]
      DSLProgram
          ↓ [transpile]
    CppProgram (C++ code string)
          ↓ [write to cpp_transpiled/program_v1.cpp]
      Files on disk
          ↓ [invoke CMake/GCC]
    build/program_v1 (executable)
          ↓ [spawn subprocess]
    SwarmProcess (IPC handle)
          ↓ [JSON over sockets]
    SwarmState { nodes: [{id, state}], time: t }
          ↓ [Python continues]
    Plot/log/send to devices
```

---

## Part 3: Detailed Architecture

### 3.1 Python DSL Layer (`python_dsl/`)

**Goal**: Express aggregate functions using Python classes & decorators, not raw C++.

**Core Classes**:

```python
# Primitive types
class Field:
    """Represents FCPP field<T>"""
    pass

class Neighborhood:
    """Represents nbr<T> — neighbor values"""
    pass

class OldValue:
    """Represents old<T> — previous round's value"""
    pass

# Aggregate function builder
@aggregate_function
class AggregateProgram:
    state_type: Type = float  # or tuple, list, custom struct

    def initial_state(self) -> state_type:
        return 0.0

    def compute(self, self_state: state_type,
                neighbors: Neighborhood[state_type]) -> state_type:
        if not neighbors:
            return self_state
        return max(neighbors.values()) + self_state

# Use case
prog = AggregateProgram()
transpiler = Transpiler(prog)
cpp_code = transpiler.generate()
```

**Features**:

- Inheritance & composition for code reuse
- Mixins for common patterns (broadcasting, gossip, etc.)
- Type annotations for code generation
- Validates before transpilation

**Key Patterns to Support**:

- `nbr(expr)` → neighbor aggregation
- `old(expr)` → temporal tracking
- `spawn(f)` → sub-computations
- `fold_hood(init, expr)` → tree reduction
- `count_hood()`, `min_hood()`, `max_hood()` → aggregates
- `broadcast(source, expr)` → multi-source dissemination
- Custom gossip/distance/collection primitives

### 3.2 Transpiler (`transpiler/`)

**Goal**: Convert Python DSL → monomorphic C++ code.

**Key Steps**:

1. **Type inference**: Analyze Python type annotations → C++ types (double, int, struct, vector)
2. **Code generation**: `ast.NodeVisitor` pattern to walk Python AST, emit C++ statements
3. **Template instantiation**: Generate specialized fcpp main function for this program's types
4. **Boilerplate injection**: Wrap user code with FCPP simulation loop

**Output**: Compilable `.cpp` file with:

```cpp
#include <fcpp/fcpp.hpp>
// Generated types
struct MyState { double value; int count; };

// Generated main aggregate function
AGGREGATE_TEMPLATE(main) : void {
  using state_t = MyState;
  // ... user-defined compute logic
}

// Generated coordination code
MAIN() {
  auto sim = fcpp::simulator<
    fcpp::coordination::basic,
    fcpp::system::online,
    int   // device id type
  >();
  // ... run simulation with IPC hooks
}
```

**Challenges & Solutions**:
| Challenge | Solution |
|-----------|----------|
| Complex type inference | Require explicit type annotations for now; add inference in Phase 2 |
| C++ syntax correctness | Generate to intermediate AST, validate, then emit C++ |
| Performance of generated code | Use `-O3` compilation; inline small functions |
| Debugging generated code | Generate with source line mappings; emit original Python comments as `//` in C++ |

### 3.3 Compilation Pipeline (`compiler/`)

**Goal**: Invoke GCC/CMake, cache results, parallelize.

**Components**:

- `ProgramCache`: Hash Python DSL → binary path; skip recompilation if unchanged
- `CMakeGenerator`: Create `CMakeLists.txt` for generated program
- `GccInvoker`: Run GCC with parallel builds, capture stderr
- `CompilationError`: Parse GCC output, map back to Python source

**Flow**:

```python
cache_key = hash(transpiled_cpp_code)
if cache.has(cache_key):
    binary_path = cache.get(cache_key)
else:
    cpp_file = f"cpp_transpiled/program_{cache_key}.cpp"
    binary_path = f"build/program_{cache_key}"

    compiler.write_program(cpp_file, transpiled_cpp_code)
    compiler.compile(cpp_file, binary_path)  # blocks until done
    cache.store(cache_key, binary_path)

return binary_path
```

**Optimization**: Use incremental builds, parallel `-j$(nproc)`, ccache if available.

### 3.4 Runtime Library (`runtime/`)

**Goal**: Support the compiled C++ side with minimal overhead.

**C++ components**:

- `ipc_server.hpp`: Unix socket listener for Python commands
- `state_serializer.hpp`: Convert node states to JSON
- `node_manager.hpp`: Add/remove nodes dynamically
- `barrier.hpp`: Synchronization between Python and C++ sides

**C interface**:

```c
// Created by compiler, called by main()
void fcpp_swarm_init(int port, int num_nodes);
void fcpp_swarm_step();  // run one round
void fcpp_swarm_destroy();

// Called by Python via subprocess stdin
// Commands: {"cmd": "step"}, {"cmd": "get_state"}, {"cmd": "add_node", "count": 5}
```

### 3.5 IPC Layer (`ipc/`)

**Goal**: Multiple communication backends, pluggable.

**Phase 1 (minimal)**: JSON over Unix sockets

```python
class IpcBackend(ABC):
    @abstractmethod
    def send_command(self, cmd: dict) -> dict: pass
    @abstractmethod
    def subscribe_state_updates(self, cb): pass

class UnixSocketBackend(IpcBackend):
    """Default: /tmp/fcpp_swarm_<pid>.sock"""

class HttpBackend(IpcBackend):
    """REST API: POST /command, GET /state"""

class GrpcBackend(IpcBackend):
    """gRPC streaming"""
```

\*\*Switchable via `SwarmProcess`:

```python
swarm = SwarmProcess(binary_path, ipc_backend="http://localhost:8080")
# or
swarm = SwarmProcess(binary_path, ipc_backend="unix")
```

### 3.6 Language Parser (`grammar/`)

**Goal**: Accept aggregate programs as strings/files.

**ANTLR grammar** (`AggregateProgram.g4`):

```antlr
aggregateProgram : functionDef+;

functionDef : 'def' NAME ':'
              ('initial_state' ':' expr ';')?
              ('compute' ':' expr ';')?
              ('when' NAME '(' args ')' ':' expr ';')*;

expr : NAME
     | NUMBER
     | expr '+' expr
     | 'nbr' '(' expr ')'
     | 'old' '(' expr ')'
     | 'max_hood' '(' expr ')'
     | 'fold_hood' '(' init ',' expr ')'
     | ...
```

**Python parser** (`grammar/parser.py`):

```python
parser = AggregateLanguageParser()
ast = parser.parse_string(program_str)  # or parse_file()
dsl_program = AstToDsl(ast).convert()   # AST → Python DSL
transpiler.generate(dsl_program)         # DSL → C++
```

---

## Part 4: File Structure

```
src/fcpp_bridge/
├── BRIDGE.md                      ← This document
├── CMakeLists.txt                 Build config (uses runtime library)
├── Makefile                       Quick local test builds
│
├── python_dsl/                    Phase 1: DSL layer
│   ├── __init__.py
│   ├── primitives.py              (Field, Neighborhood, OldValue, etc.)
│   ├── decorators.py              (@aggregate_function, mixins)
│   ├── types.py                   (Type system for code gen)
│   └── validators.py              (Pre-transpilation validation)
│
├── transpiler/                    Phase 2: Code generator
│   ├── __init__.py
│   ├── core.py                    (Transpiler main class)
│   ├── visitor.py                 (AST visitor → C++ emitter)
│   ├── type_inference.py          (Type analysis)
│   ├── builtins.py                (nbr, old, spawn, fold_hood, etc.)
│   └── templates.py               (C++ template boilerplate)
│
├── compiler/                      Phase 3: Build pipeline
│   ├── __init__.py
│   ├── cache.py                   (Program caching)
│   ├── cmake_gen.py               (CMakeLists.txt generation)
│   ├── gcc_invoker.py             (GCC subprocess wrapper)
│   └── errors.py                  (Parse & report compilation errors)
│
├── runtime/                       Phase 4: C++ runtime library
│   ├── ipc_server.hpp             (Socket listener)
│   ├── state_serializer.hpp       (State → JSON)
│   ├── node_manager.hpp           (Dynamic node lifecycle)
│   └── main_template.hpp          (Boilerplate for generated main)
│
├── ipc/                           Phase 4B: Communication backends
│   ├── __init__.py
│   ├── backend.py                 (Abstract base)
│   ├── unix_socket.py             (Unix socket impl)
│   ├── http.py                    (REST API)
│   ├── grpc_backend.py            (gRPC streaming)
│   └── serializers.py             (JSON, Protocol Buffers)
│
├── grammar/                       Phase 5: ANTLR language
│   ├── AggregateProgram.g4        (ANTLR grammar)
│   ├── parser.py                  (Python parser wrapper)
│   ├── ast_to_dsl.py              (ANTLR AST → Python DSL)
│   └── __antlr_gen/               ← Auto-generated by antlr4
│
├── cpp_transpiled/                ← Generated C++ code (git-ignored)
│   ├── program_<hash>.cpp
│   └── ...
│
├── build/                         ← Compiled binaries (git-ignored)
│   ├── program_<hash>
│   └── ...
│
├── examples/                      Phase 6: Demo programs
│   ├── simple_averaging.py        (Averaging aggregate)
│   ├── gossip_protocol.py         (Gossip pattern)
│   ├── distance_broadcast.py      (Multi-hop broadcast)
│   └── from_string_parser.py      (Parse aggregate from string)
│
├── tests/                         Test suite (pytest)
│   ├── test_dsl.py                (DSL validation)
│   ├── test_transpiler.py         (Generated C++ correctness)
│   ├── test_compiler.py           (Build pipeline)
│   ├── test_ipc.py                (IPC backends)
│   └── test_e2e.py                (End-to-end: Python → compiled → execute)
│
└── fcpp_clone_GITIGNORE_ME/       FCPP source (symlink or git-ignored clone)
```

---

## Part 5: Phase-by-Phase Rollout

### Phase 1: Python DSL (Weeks 1-2)

- [x] Design DSL classes (Field, Neighborhood, etc.)
- [ ] Implement basic aggregate function decorator
- [ ] Add type annotation support
- [ ] Pre-transpilation validators
- [ ] 20+ unit tests

**Deliverable**: `AggregateProgram` class can represent simple programs; no code gen yet.

### Phase 2: Transpiler (Weeks 2-4)

- [ ] AST visitor → C++ emitter (skeleton)
- [ ] Transpile simple expressions (literals, binary ops)
- [ ] Transpile primitives (nbr, old, fold_hood)
- [ ] Type inference for generated C++
- [ ] Generated code compiles (even if incorrect at runtime)
- [ ] 50+ tests

**Deliverable**: Python DSL → compilable C++ code.

### Phase 3: Compiler Pipeline (Weeks 4-5)

- [ ] Program caching (hash-based)
- [ ] CMakeLists.txt generator
- [ ] GCC subprocess invoker
- [ ] Error parsing (map GCC errors back to Python)
- [ ] 15+ tests

**Deliverable**: One-button compilation: `program.compile()` → binary path.

### Phase 4: Runtime & IPC (Weeks 5-7)

- [ ] Unix socket server (C++ side)
- [ ] State serialization (C++ → JSON)
- [ ] Node lifecycle management
- [ ] Python subprocess launcher
- [ ] UnixSocket backend + HTTP backend
- [ ] 30+ tests (including integration tests)

**Deliverable**: Python ↔ C++ swarm communication working.

### Phase 5: ANTLR Language (Weeks 7-8)

- [ ] Write ANTLR grammar
- [ ] ANTLR parser → Python AST
- [ ] Convert AST to DSL objects
- [ ] Parse program from string
- [ ] 20+ tests

**Deliverable**: `bridge.parse_string(program_str)` → ready to compile & run.

### Phase 6: Scaling & Plugins (Weeks 8+)

- [ ] HTTP backend (REST API)
- [ ] gRPC backend (streaming)
- [ ] Metrics collection (state history)
- [ ] GUI/visualization plugin (optional)
- [ ] Device management UI
- [ ] Documentation & tutorials

**Deliverable**: Production-ready bridge; scale to 1000+ nodes.

---

## Part 6: Key Design Decisions

### Why Transpilation, Not Interpretation?

- **Interpreted callbacks** (current Phase 2): Slow, limits complexity
- **JIT compilation** (this design): Fast execution, full C++ expressivity, compile-once-run-many-times

### Why No Hot Reload?

- FCPP's node state is in-process memory; can't safely reload while running
- Trade-off: regenerate program → recompile → restart swarm (acceptable for research/simulation)
- Future: add incremental state export/import for warm restarts

### Why ctypes (Not Direct C++ Binding)?

- MSVC (Python 3.14) vs GCC (available compiler) → ABI mismatch
- ctypes uses stable C ABI; cross-compiler compatible
- Proven in fcpp_py_porting Phase 1 (55 passing tests)

### Why Cache Compiled Binaries?

- Compilation is expensive (fcpp templates)
- Same program signature → same binary
- Hash(`transpiled_cpp_code`) → cache key
- Typical cache hit rate: 80%+ in interactive development

### Why Phase Node Count Dynamic?

- Simulate device joins/leaves without recompiling
- IPC command: `{"cmd": "add_node", "count": 5}`
- Doesn't alter core program logic

---

## Part 7: Success Criteria

### Phase 1 ✅ DSL

- Simple program in Python compiles to valid C++ syntax
- Type annotations propagate correctly

### Phase 2 ✅ Transpiler

- Generated C++ builds without errors
- Output is reasonably optimized (no unnecessary copies)

### Phase 3 ✅ Compiler

- Two identical programs produce same binary (cache hit)
- GCC errors map back to readable Python errors
- Build time < 10 seconds for typical programs

### Phase 4 ✅ Runtime & IPC

- Python can spawn compiled swarm
- Python can send commands, receive state updates
- Swarm runs independently while Python idles
- Multiple IPC backends work (Unix socket, HTTP, gRPC)

### Phase 5 ✅ ANTLR Parser

- Parse example programs from strings
- Coverage of all aggregate primitives

### Phase 6 ✅ Production

- Simulate 1000-node swarms without memory leaks
- Compile 100 different programs without cache collisions
- Metrics system captures node state over time

---

## Part 8: Relationship to fcpp_py_porting

| Component          | fcpp_py_porting                       | fcpp_bridge                               |
| ------------------ | ------------------------------------- | ----------------------------------------- |
| **Scope**          | Vec2/Vec3 + basic simulation callback | Full DSL → code gen → IPC                 |
| **Compilation**    | Once, at build time                   | Dynamically, per program                  |
| **Callback model** | Python callbacks into C++ sim         | C++ sim runs independently, IPC to Python |
| **Expressivity**   | Limited by callback interface         | Full aggregate language                   |
| **Reuse**          | Use ctypes & build lessons            | Reuse Makefile pattern, LLD workaround    |
| **Status**         | Mature (Phase 2 tested)               | Architecture phase                        |

**Decision**: Keep fcpp_py_porting as reference; don't refactor it. Start fresh in fcpp_bridge with architecture designed for this from day one.

---

## Part 9: Open Questions & Risks

### Q1: Type inference complexity

**Risk**: Python's dynamic typing makes full inference hard.  
**Mitigation**: Require explicit annotations for now; infer only within function scope.

### Q2: Generated code performance

**Risk**: Generated C++ might be slower than hand-written FCPP programs.  
**Mitigation**: Benchmark against hand-written equivalents; use `-O3` compilation.

### Q3: Debugging generated code

**Risk**: Users can't easily debug if compiled program crashes.  
**Mitigation**: Generate with `-g` symbols; map stack traces back to Python source.

### Q4: ANTLR grammar maintenance

**Risk**: Grammar version mismatches, complex parse trees.  
**Mitigation**: Vendor specific ANTLR version; write comprehensive parser tests.

### Q5: Multi-swarm coordination

**Risk**: What if user runs 10 different swarms simultaneously?  
**Mitigation**: Each swarm gets unique port/socket; Python side multiplexes IPC streams.

---

## Part 10: Getting Started

### Next Steps (Week 1)

1. [x] Write this architecture document (you are here)
2. [ ] Create empty fcpp_bridge/ project structure
3. [ ] Implement Python DSL classes (primitives.py, decorators.py)
4. [ ] Write 20 tests for DSL validation
5. [ ] Set up GitHub Actions for continuous testing

### Immediate Coding Tasks

```bash
mkdir -p src/fcpp_bridge/{python_dsl,transpiler,compiler,runtime,ipc,grammar,examples,tests}
# Copy skeleton Makefile from fcpp_py_porting for quick testing
# Initialize pytest conftest.py
```

---

## Appendix: Glossary

- **DSL**: Domain-Specific Language (Python classes modeling FCPP concepts)
- **Transpile**: Translate high-level Python code → lower-level C++ code
- **Monomorphic**: Single specialized instance (vs polymorphic: many instances)
- **IPC**: Inter-Process Communication (Python subprocess ↔ compiled C++ process)
- **COMDAT**: Common Data sections; GCC/linker feature; requires LLD on Windows
- **ctypes**: Python standard library for calling C ABI functions
- **ANTLR**: ANother Tool for Language Recognition; parser generator
- **Field**: FCPP primitive representing spatially-distributed values
- **Neighborhood**: Local view of neighbors' states (nbr in FCPP parlance)
- **Aggregate**: Distributed computation collective result
- **Swarm**: Collection of FCPP nodes/devices running coordinated program

---

**Document Version**: 0.1  
**Author**: Claude Code, guided by user  
**Next review**: After Phase 1 prototype complete
