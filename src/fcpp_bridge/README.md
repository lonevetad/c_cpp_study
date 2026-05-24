# FCPP Bridge — Python-to-C++ DSL & Transpiler

Production-ready bridge between Python and FCPP (Field Calculus C++14 framework).

## Quick Start

```bash
cd <repo-root>
PYTHONPATH=src src/expr_eval_py/expr_eval_py_env/bin/pytest src/fcpp_bridge/tests/ -v
# 482 pass, 0 fail
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
| v1.0  | Network listener pipeline | ✅ Done  | +38   |
| v1.1  | Compiler customization + tutorials | ✅ Done | +3 |

**Total: 523 tests — 523 pass, 0 fail.**

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

Each sub-package follows a **one-file-per-class** layout. Every `__init__.py` re-exports all public names so existing import paths remain unchanged.

```
fcpp_bridge/
├── python_dsl/             Phase 1: DSL primitives & decorators
│   ├── primitives/         64 primitive classes (one .py each) + Primitive base
│   ├── types/              CppType, 14 proxy classes, TemplateParam, AggregateType
│   ├── validators/         ValidationError, ValidationRule ABC, 5 rule classes,
│   │                       ValidationPipeline, AggregateValidator
│   └── decorators/         6 _Mixin* classes + aggregate_function / mixin_* decorators
├── transpiler/             Phase 2: Python → C++ code generation
│   ├── transpilation_error.py
│   ├── cpp_code_builder.py
│   ├── python_ast_visitor.py
│   ├── transpiler_core.py
│   └── _constants.py       _FCPP_PRIMITIVES dict (shared by visitor + transpiler)
├── compiler/               Phase 3: Build pipeline & caching
│   ├── compilation_error.py
│   ├── compilation_result.py
│   ├── program_cache.py
│   ├── compiler_core.py
│   ├── cmake_generator.py
│   ├── compilation_diagnostic.py
│   └── compilation_error_parser.py
├── runtime/                Phase 4: C++ runtime library (generated headers)
│   └── runtime_generator.py
├── ipc/                    Phase 4B / v1.0: Communication backends + listener pipeline
│   ├── node_state.py
│   ├── swarm_snapshot.py
│   ├── updates_listener.py   UpdatesListener type alias
│   ├── listener_proxy.py     ListenerProxy (sequential / parallel-async)
│   ├── ipc_backend.py
│   ├── unix_socket_backend.py
│   ├── http_backend.py
│   ├── grpc_backend.py
│   ├── swarm_process.py      node add/remove strategies, heartbeat, listener mgmt
│   └── device_manager.py
├── grammar/                Phase 5: Language parser (recursive-descent + ANTLR gen)
│   ├── ast_node.py
│   ├── parser_error.py
│   ├── aggregate_language_parser.py   (+ ast_to_dsl function)
│   └── antlr_parser.py
├── metrics/                Phase 6: Metrics collection & export
│   ├── metric_point.py
│   ├── metrics_summary.py
│   ├── state_history.py
│   └── metrics_collector.py
├── visualization/          Phase 7: Live / replay GUI plugin
│   ├── visualizer_base.py
│   ├── text_dashboard.py
│   └── swarm_visualizer.py
├── log.py                  Flexible logging (no classes; used by all sub-packages)
├── examples/               Demo programs
├── tests/                  Pytest test suite (482 tests, one sub-package per phase)
│   ├── dsl/                Phase 1 tests (6 files)
│   ├── transpiler/         Phase 2 tests (3 files)
│   ├── compiler/           Phase 3 tests (3 files)
│   ├── ipc/                Phase 4 tests (4 files)
│   ├── grammar/            Phase 5 tests (5 files)
│   ├── metrics/            Phase 6 tests (6 files)
│   └── visualization/      Phase 7 tests (4 files)
├── cpp_transpiled/         ← Generated C++ code (git-ignored)
└── build/                  ← Compiled binaries (git-ignored)
```

## Examples

The `examples/` directory contains Python ports of real FCPP C++ algorithms from
`fcpp-sample-project` and `fcpp-exercises`, written for demonstration and learning.
Each file defines an `@aggregate_function` class (transpilable to C++) and a pure-Python
`_demo_simulate()` that runs the algorithm and writes per-node log files to `examples/logs/`.

Run any example:
```bash
cd <repo-root>
PYTHONPATH=src python src/fcpp_bridge/examples/<example>.py
```

| Python file | C++ source | Key FCPP primitives |
|---|---|---|
| `spreading_collection.py` | `fcpp-sample-project/lib/spreading_collection.hpp` | `rectangle_walk`, `abf_distance`, `mp_collection`, `broadcast` |
| `channel_broadcast.py` | `fcpp-sample-project/lib/channel_broadcast.hpp` | `rectangle_walk`, `bis_distance`, `broadcast` |
| `collection_compare.py` | `fcpp-sample-project/lib/collection_compare.hpp` | `rectangle_walk`, `abf_distance`, `sp_collection`, `mp_collection`, `wmp_collection`, `count_hood` |
| `message_dispatch.py` | `fcpp-sample-project/lib/message_dispatch.hpp` | `rectangle_walk`, `bis_distance`, `nbr`, `min_hood`, `sp_collection`, `spawn`, `old` |
| `chain_decaying.py` | `fcpp-sample-project/run/chain_decaying.hpp` | `nbr`, `min_hood` |

See [EXAMPLES_JOURNAL.md](EXAMPLES_JOURNAL.md) for the full algorithm notes, source inventory,
and resume instructions.

## Documentation

- **[bridge.md](../bridge.md)** — Complete architecture & implementation log
- **[Design Decisions](../bridge.md#part-6-key-design-decisions)** — Why this approach
- **[Phase-by-Phase Rollout](../bridge.md#part-5-phase-by-phase-rollout)** — Detailed checklist
- **[Glossary](../bridge.md#appendix-glossary)** — Terminology
- **[VISUALIZATION.md](VISUALIZATION.md)** — Phase 7: ANTLR generation & visualization plugin
- **[TUTORIAL_simple.md](TUTORIAL_simple.md)** — Beginner tutorial: 20-node hop-channel (BIS + nbr/min_hood + broadcast)
- **[TUTORIAL_in_depth.md](TUTORIAL_in_depth.md)** — Production tutorial: custom class, listener proxy, node management, heartbeat

## What Works

- ✅ `@aggregate_function` decorator with full pre-transpilation validation
- ✅ `AggregateType.infer()`: Python types → C++ types (primitives, list, tuple, dict, set, frozenset, Optional, Union, dataclass, TypeVar, TemplateParam; full C++14–C++23 proxy classes)
- ✅ `CppType`: explicit constructor (`__init__` with keyword-only args), `required_includes`, `cpp_std`, `is_template` fields; defensive copy of include list
- ✅ 14 C++ proxy annotations: `CppVector`, `CppArray[T,N]`, `CppSet`, `CppUnorderedSet`, `CppMultiSet`, `CppMap`, `CppUnorderedMap`, `CppMultiMap`, `CppPair` (C++14); `CppOptional`, `CppVariant`, `CppAny` (C++17); `CppSpan` (C++20); `CppExpected`, `CppMdSpan` (C++23)
- ✅ `TemplateParam("T")` — unresolved template type parameter (`typename T`)
- ✅ `PythonAstVisitor`: all binary/comparison operators, built-ins (max, min, len, sum), attrs, subscripts; all 64 FCPP primitives inject `CALL` and auto-add coordination headers
- ✅ `CppCodeBuilder` + `Transpiler.generate()` → complete C++ source string
- ✅ `ProgramCache` (SHA-256 hash, manifest, persistent across runs)
- ✅ `Compiler` (GCC invocation, caching, `get_or_compile`; `std`, `opt_level`, `extra_includes` constructor params for full flag customization)
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

## v1.0 — Network listener pipeline & node management refactor

- **`UpdatesListener`**: `Callable[[SwarmSnapshot], None]` type alias in `updates_listener.py`
- **`ListenerProxy`**: proxy that dispatches state updates to a dynamic list of listeners;
  `mode="sequential"` (default) or `"parallel"` (thread-pool); `add_listener(fn)` → `int` ID;
  `remove_listener(id)`; `close()` shuts down the thread pool
- **`SwarmProcess` — node addition strategies**:
  - `add_nodes_random(count, *, area, comm_range, max_speed, propulsion)` → `List[int]` (random unique IDs)
  - `add_node_explicit(node_id, position, *, comm_range, max_speed, propulsion)` — physical/production devices
  - `add_nodes_sequential(count, start_positions=None)` → `List[int]` (sequential IDs, unique by construction)
  - `add_nodes(count)` preserved as backward-compatible alias
- **`SwarmProcess.remove_node(node_id)`**: removes a node by ID (simulation disconnection)
- **Passive heartbeat / liveness**:
  - `check_liveness(timeout=30.0)` → `Dict[int, bool]` — alive if last seen within timeout seconds
  - `start_heartbeat_monitor(interval, timeout, on_dead=None)` — background thread, idempotent
  - `stop_heartbeat_monitor()`
  - `get_state()` now also updates heartbeat timestamps (pull path)
- **`SwarmProcess` — listener pipeline**:
  - `add_listener(fn)` → `int` — global listener; auto-creates `ListenerProxy` on first call
  - `remove_listener(listener_id)`
  - `add_node_listener(node_id, fn)` → `int` — per-node override (takes priority over global)
  - `remove_node_listener(node_id, listener_id)`
  - `_dispatch_update(snapshot)` routes each node's snapshot: per-node proxy → global proxy
- **`IpcBackend.subscribe_state_updates`** signature updated to use `UpdatesListener`

## v1.1 — Compiler customization + tutorials

- **`Compiler` constructor** now accepts `std: str = "c++26"`, `opt_level: str = "2"`,
  `extra_includes: List[str] = None` — full control over the C++ standard, optimization
  level (`-O0` through `-O3`/`-Os`/`-Og`), and extra include directories.
  `extra_flags` in `compile()` still allows per-call overrides (appended last, GCC takes
  last occurrence for `-O` and `-std`).
- **`TUTORIAL_simple.md`** — beginner guide: 20-node network, source=3, destination=18;
  BIS distance + hop count via `nbr`/`min_hood` + source-ID broadcast; full pipeline
  (define → transpile → compile → run → listen); pure-Python simulation fallback.
- **`TUTORIAL_in_depth.md`** — production guide: `HopChannelSimulation` wrapper class,
  global `ListenerProxy` (logging + debug), per-node override for node 5, dynamic
  listener add/remove, start/pause/resume/stop lifecycle, node add/remove/heartbeat,
  compiler flag customization, complete reference table.

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
| Status      | Mature (Phase 2 tested)          | 7 phases + type system + v1.0 IPC |

**Note**: fcpp_py_porting is a reference/learning project. fcpp_bridge is the production design.

## License

Same as parent project.
