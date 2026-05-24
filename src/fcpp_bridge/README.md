# FCPP Bridge — Python-to-C++ DSL & Transpiler

Production-ready bridge between Python and FCPP (Field Calculus C++14 framework).

## Quick Start

```bash
cd <repo-root>
PYTHONPATH=src src/expr_eval_py/expr_eval_py_env/bin/pytest src/fcpp_bridge/tests/ -v
# 432 pass, 0 fail
```

## Overview

**fcpp_bridge** lets Python programs:

1. **Define** aggregate functions using a Python DSL
2. **Transpile** those functions to optimized C++ code
3. **Compile** dynamically (with caching)
4. **Execute** the compiled swarms
5. **Communicate** with swarms via flexible IPC (sockets, HTTP, gRPC)
6. **Monitor** swarm metrics over time (state history, statistics, export)
7. **Visualize** swarm output live or as a post-hoc replay (matplotlib or terminal)

## Project Phases

| Phase | Component                 | Status   | Tests |
| ----- | ------------------------- | -------- | ----- |
| 1     | Python DSL layer          | ✅ Done  | 42    |
| 2     | Transpiler (Python → C++) | ✅ Done  | 74    |
| 3     | Compiler pipeline         | ✅ Done  | 15    |
| 4     | Runtime & IPC             | ✅ Done  | 55    |
| 5     | Language parser           | ✅ Done  | 47    |
| 6     | Scaling & backends        | ✅ Done  | 35    |
| 7     | Visualization & ANTLR gen | ✅ Done  | 16    |
| v0.8  | Extended type system      | ✅ Done  | +37   |
| v0.9  | OOP/Prototype/logging     | ✅ Done  | +50   |

**Total: 482 tests — 482 pass, 0 fail.**

## Architecture

```
Python Program
    ↓ (DSL definition / string via parser)
AggregateProgram (Python class)
    ↓ (transpile)
C++ source code
    ↓ (compile + cache)
Executable binary
    ↓ (spawn subprocess)
Swarm process
    ↓ (IPC: JSON, HTTP, gRPC)
Python receives state updates
    ↓ (MetricsCollector)
Statistics / JSON / CSV export
```

## File Structure

```
fcpp_bridge/
├── python_dsl/         Phase 1: DSL primitives & decorators
├── transpiler/         Phase 2: Python → C++ code generation
├── compiler/           Phase 3: Build pipeline & caching
├── runtime/            Phase 4: C++ runtime library (generated headers)
├── ipc/                Phase 4B: Communication backends
├── grammar/            Phase 5: Language parser (recursive-descent + ANTLR gen)
├── metrics/            Phase 6: Metrics collection & export
├── visualization/      Phase 7: Live / replay GUI plugin
├── examples/           Demo programs
├── tests/              Pytest test suite (395 tests)
├── cpp_transpiled/     ← Generated C++ code (git-ignored)
└── build/              ← Compiled binaries (git-ignored)
```

## Documentation

- **[bridge.md](../bridge.md)** — Complete architecture & implementation log
- **[Design Decisions](../bridge.md#part-6-key-design-decisions)** — Why this approach
- **[Phase-by-Phase Rollout](../bridge.md#part-5-phase-by-phase-rollout)** — Detailed checklist
- **[Glossary](../bridge.md#appendix-glossary)** — Terminology
- **[VISUALIZATION.md](VISUALIZATION.md)** — Phase 7: ANTLR generation & visualization plugin

## What Works

- ✅ `@aggregate_function` decorator with full pre-transpilation validation
- ✅ `AggregateType.infer()`: Python types → C++ types (primitives, list, tuple, dict, set, frozenset, Optional, Union, dataclass, TypeVar, TemplateParam; full C++14–C++23 proxy classes)
- ✅ `CppType`: explicit constructor (`__init__` with keyword-only args), `required_includes`, `cpp_std`, `is_template` fields; defensive copy of include list
- ✅ 14 C++ proxy annotations: `CppVector`, `CppArray[T,N]`, `CppSet`, `CppUnorderedSet`, `CppMultiSet`, `CppMap`, `CppUnorderedMap`, `CppMultiMap`, `CppPair` (C++14); `CppOptional`, `CppVariant`, `CppAny` (C++17); `CppSpan` (C++20); `CppExpected`, `CppMdSpan` (C++23)
- ✅ `TemplateParam("T")` — unresolved template type parameter (`typename T`)
- ✅ `PythonAstVisitor`: all binary/comparison operators, built-ins (max, min, len, sum), attrs, subscripts; all 64 FCPP primitives inject `CALL` and auto-add coordination headers
- ✅ `CppCodeBuilder` + `Transpiler.generate()` → complete C++ source string
- ✅ `ProgramCache` (SHA-256 hash, manifest, persistent across runs)
- ✅ `Compiler` (GCC invocation, caching, `get_or_compile`)
- ✅ `RuntimeGenerator` (C++ headers: ipc_server, state_serializer, node_manager, main_template)
- ✅ `UnixSocketBackend`, `HttpBackend`, `GrpcBackend` (full gRPC streaming with `.proto`)
- ✅ `SwarmProcess` (subprocess lifecycle, step, get_state, add_nodes)
- ✅ `DeviceManager` (multi-swarm lifecycle, send_all, step_all, get_all_states, context manager)
- ✅ `AggregateLanguageParser` (tokenizer + recursive-descent parser, `parse_string`/`parse_file`; all 64 FCPP primitives with variable-arg parsing)
- ✅ `AntlrParser` (antlr4-backed parser with fallback; `AggregateProgram.g4` grammar file with all 64 primitives)
- ✅ `ast_to_dsl` converter
- ✅ `CmakeGenerator` (CMakeLists.txt generation for FCPP programs)
- ✅ `CompilationErrorParser` (structured GCC/Clang diagnostic parsing)
- ✅ `MetricsCollector` (record, callbacks, custom extractor, bounded history)
- ✅ `StateHistory` (ring-buffer, per-node history, negative indexing)
- ✅ `MetricsSummary` (mean/min/max/std per round, total time, avg node count)
- ✅ `export_json` / `export_csv`
- ✅ `generate_antlr.py` (script to compile grammar → Python3 ANTLR4 stubs; `--download` flag fetches jar)
- ✅ `TextDashboard` (terminal visualizer, no external deps)
- ✅ `SwarmVisualizer` (live matplotlib charts: node count + mean/min/max band)
- ✅ `create_visualizer` factory (auto-selects best available backend)

## Known Gaps (Future Work)

- Phase 7: Multi-swarm coordination UI
- Phase 7: Run `generate_antlr.py --download` to activate the ANTLR4 parser path (requires Java 11+)

## v0.9 — OOP / Prototype / Logging refactor

- **`Primitive` base**: all 64 primitive classes inherit `Primitive`; `clone()` / `clone_with(**changes)` implement the Prototype pattern; `has_callable_args` + `callable_arg_positions` mark G&& callable arguments
- **`ValidationRule` ABC + `ValidationPipeline`**: composable validation rules with `AggregateValidator` delegating internally; custom rules can be injected via `AggregateValidator.set_pipeline()`
- **Class-based mixins**: `_MixinGossip`, `_MixinBroadcast`, `_MixinCollection`, `_MixinElection`, `_MixinTime`, `_MixinGeometry` as proper classes; dynamic subclassing via `type(name, (mixin_cls, cls), {...})`
- **`visit_Lambda`**: `PythonAstVisitor` now transpiles Python lambdas to C++14 generic lambdas (`[=](auto a, auto b) { return …; }`) for FCPP `G&&` callable parameters
- **Logging**: `log.py` flexible logging module; level-based `set_bridge_logging(bool)`; integrated into validators, decorators, and transpiler

## Primitive Coverage Audit

See **[PRIMITIVE_AUDIT.md](PRIMITIVE_AUDIT.md)** for the full record of how all 64 FCPP coordination primitives (across 7 headers) were traced from C++ source → Python DSL → transpiler → grammar, and what was added to close the gaps.

## Relationship to fcpp_py_porting

| Aspect      | fcpp_py_porting                  | fcpp_bridge                     |
| ----------- | -------------------------------- | ------------------------------- |
| Scope       | Vec2/Vec3 + simulation callbacks | Full DSL + code gen + IPC       |
| Compilation | Once (build time)                | Dynamic (per program)           |
| Callback    | Python calls into C++            | C++ runs independently          |
| Status      | Mature (Phase 2 tested)          | All 7 phases + type system (v0.8) |

**Note**: fcpp_py_porting is a reference/learning project. fcpp_bridge is the production design.

## License

Same as parent project.
