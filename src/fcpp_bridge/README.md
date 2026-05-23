# FCPP Bridge — Python-to-C++ DSL & Transpiler

Production-ready bridge between Python and FCPP (Field Calculus C++14 framework).

## Quick Start

```bash
# Not yet runnable; Project in architecture/skeleton phase
cd src/fcpp_bridge
pytest tests/  # Run basic DSL tests
```

## Overview

**fcpp_bridge** lets Python programs:

1. **Define** aggregate functions using a Python DSL
2. **Transpile** those functions to optimized C++ code
3. **Compile** dynamically (with caching)
4. **Execute** the compiled swarms
5. **Communicate** with swarms via flexible IPC (sockets, HTTP, gRPC)

## Project Phases

| Phase | Component                 | Status      | ETA     |
| ----- | ------------------------- | ----------- | ------- |
| 1     | Python DSL layer          | 🟡 Skeleton | Week 2  |
| 2     | Transpiler (Python → C++) | ⬜ Planned  | Week 4  |
| 3     | Compiler pipeline         | ⬜ Planned  | Week 5  |
| 4     | Runtime & IPC             | ⬜ Planned  | Week 7  |
| 5     | ANTLR language parser     | ⬜ Planned  | Week 8  |
| 6     | Scaling & backends        | ⬜ Planned  | Week 9+ |

## Architecture

```
Python Program
    ↓ (DSL definition)
AggregateProgram (Python class)
    ↓ (transpile)
C++ source code
    ↓ (compile + cache)
Executable binary
    ↓ (spawn subprocess)
Swarm process
    ↓ (IPC: JSON, HTTP, gRPC)
Python receives state updates
```

## File Structure

```
fcpp_bridge/
├── bridge.md               ← Full architecture doc (READ THIS FIRST)
├── python_dsl/             Phase 1: DSL primitives & decorators
├── transpiler/             Phase 2: Python → C++ code generation
├── compiler/               Phase 3: Build pipeline & caching
├── runtime/                Phase 4: C++ runtime library
├── ipc/                    Phase 4B: Communication backends
├── grammar/                Phase 5: ANTLR parser
├── examples/               Demo programs
├── tests/                  Pytest test suite
├── cpp_transpiled/         ← Generated C++ code (git-ignored)
└── build/                  ← Compiled binaries (git-ignored)
```

## Documentation

- **[bridge.md](../bridge.md)** — Complete architecture (70+ pages)
- **[Design Decisions](../bridge.md#part-6-key-design-decisions)** — Why this approach
- **[Phase-by-Phase Rollout](../bridge.md#part-5-phase-by-phase-rollout)** — Timeline
- **[Glossary](../bridge.md#appendix-glossary)** — Terminology

## Getting Started

See [bridge.md Part 10: Getting Started](../bridge.md#part-10-getting-started).

## Status

This is **architecture phase** (v0.1). Skeleton Python files created; implementation begins Phase 1.

### What Works

- ✅ Project structure
- ✅ Basic DSL classes (Field, Neighborhood, OldValue, etc.)
- ✅ Decorator infrastructure
- ✅ Type system skeleton
- ✅ Test harness (pytest)

### What's Next

- [ ] Complete DSL validation (Phase 1)
- [ ] Implement transpiler visitor (Phase 2)
- [ ] Connect to GCC build pipeline (Phase 3)
- [ ] Add IPC backends (Phase 4)
- [ ] Integrate ANTLR parser (Phase 5)

## Relationship to fcpp_py_porting

| Aspect      | fcpp_py_porting                  | fcpp_bridge               |
| ----------- | -------------------------------- | ------------------------- |
| Scope       | Vec2/Vec3 + simulation callbacks | Full DSL + code gen + IPC |
| Compilation | Once (build time)                | Dynamic (per program)     |
| Callback    | Python calls into C++            | C++ runs independently    |
| Status      | Mature (Phase 2 ~70%)            | Architecture phase        |

**Note**: fcpp_py_porting is a reference/learning project. fcpp_bridge is the production design.

## License

Same as parent project.
