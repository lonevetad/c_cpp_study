# FCPP Bridge — Python-to-C++ DSL & Transpiler

Production-ready bridge between Python and FCPP (Field Calculus C++14 framework).

## Quick Start

```bash
cd <repo-root>
PYTHONPATH=src src/expr_eval_py/expr_eval_py_env/bin/pytest src/fcpp_bridge/tests/ -v
# 624 pass, 0 fail
```

> **`PYTHONPATH` requirement**: `fcpp_bridge` is not published on PyPI — it lives
> in `src/fcpp_bridge/` inside this repository.  Python must find the `src/`
> directory on its module search path before any `import fcpp_bridge` will work.
>
> ```bash
> # Persistent for the terminal session (run from the repository root):
> export PYTHONPATH=/path/to/c_cpp_study/src
>
> # — or — inline prefix for a single command:
> PYTHONPATH=src python src/fcpp_bridge/examples/worker_role_assignment.py
> ```
>
> If your working directory is `src/fcpp_bridge/`, the `src/` directory is one
> level up (`..`):
>
> ```bash
> PYTHONPATH=.. /usr/bin/python3 examples/worker_role_assignment.py
> ```

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

| Phase | Component                                 | Status  | Tests                              |
| ----- | ----------------------------------------- | ------- | ---------------------------------- |
| 1     | Python DSL layer                          | ✅ Done | 42                                 |
| 2     | Transpiler (Python → C++)                 | ✅ Done | 74                                 |
| 3     | Compiler pipeline                         | ✅ Done | 15                                 |
| 4     | Runtime & IPC                             | ✅ Done | 55                                 |
| 5     | Language parser                           | ✅ Done | 47                                 |
| 6     | Scaling & backends                        | ✅ Done | 35                                 |
| 7     | Visualization & ANTLR gen                 | ✅ Done | 16                                 |
| v0.8  | Extended type system                      | ✅ Done | +37                                |
| v0.9  | OOP/Prototype/logging                     | ✅ Done | +50                                |
| v1.0  | Network listener pipeline                 | ✅ Done | +38                                |
| v1.1  | Compiler customization + tutorials        | ✅ Done | +3                                 |
| v1.2  | Physical device deployment                | ✅ Done | +32 PhysicalNode, +8 DeviceManager |
| v1.3  | Pluggable liveness strategies             | ✅ Done | +23                                |
| v1.4  | C++-alike DSL control flow + per-step CLI | ✅ Done | +32                                |
| v1.5  | worker_role_assignment.py example (match/case + spawn) | ✅ Done | +0 |
| v1.6  | `self_uid()` primitive (→ `node.uid`); enum comments; step 7 role tasks | ✅ Done | +1 |
| v1.7  | `RoleCommunicationType` enum; `RIPETITOR`→`REPEATER`; `RUBBLES_REMOVER`→endpoint | ✅ Done | +0 |
| v1.8  | Logging refactor: library `print()` → `get_logger()`; `_example_utils` validation helper; v1.9 gap-analysis plan | ✅ Done | +0 |
| v1.8.1 | `worker_role_assignment`: `ROLE_CYCLE` (5 extra `WorkerRole.REPEATER` nodes, `DEVICES=26`); `ROLE_COMM_TYPE` frozenset-unpack bug fix | ✅ Done | +0 |
| v1.8.2 | Enum-value refactoring: `WorkerRole.X.value` in comparisons and `case` labels; `ROLE_CYCLE` uses enum members; `int(r)` → `r.value` in output | ✅ Done | +0 |
| v1.8.3 | Named constants `ADDITIONAL_REPEATERS_EACH_CYCLE` and `FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS`; `DEVICES` derived; `ROLE_CYCLE` uses unpacking `*([WorkerRole.REPEATER] * N)` | ✅ Done | +0 |
| v1.8.4 | Transpiler enum constant-folding: `PythonAstVisitor` resolves `IntEnum.X.value` dotted chains to integer literals via `compute.__globals__`; valid C++ `case` labels and comparisons | ✅ Done | +5 |
| v1.8.5 | Example import fix: `from examples._example_utils` → `from fcpp_bridge.examples._example_utils` in all 6 example files; `PYTHONPATH` requirement documented in README, TUTORIAL_simple, TUTORIAL_in_depth | ✅ Done | +0 |
| v1.9 | `communication_roles_assignment.py` new example; shared helpers (`neighbors_of`, `build_positions`, `SPAWN_STATUS_*`) added to `_example_utils.py`; all 6 existing examples refactored to use shared `neighbors_of`; `FUTURE_EXERCISES.md` (FE-1 through FE-8) | ✅ Done | +0 |
| v2.0 | Match guard clauses (`case X if cond:`) + OR patterns (`case A \| B:`) in transpiler; `AbstractExample` base class; all 7 main examples refactored with `AbstractExample`; nodes represented as dynamic dict (join/leave support); `match_guard_or_pattern.md`; `bridge.md` fully updated | ✅ Done | +13 |

**Total: 624 tests — 624 pass, 0 fail.**

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
├── ipc/                    Phase 4B / v1.0-v1.3: Communication backends + listener + physical nodes
│   ├── node_state.py
│   ├── swarm_snapshot.py
│   ├── updates_listener.py   UpdatesListener type alias
│   ├── listener_proxy.py     ListenerProxy (sequential / parallel-async)
│   ├── ipc_backend.py
│   ├── unix_socket_backend.py
│   ├── http_backend.py
│   ├── grpc_backend.py
│   ├── liveness_strategy.py  LivenessStrategy ABC + PassiveHeartbeat / ActivePing / AlwaysAlive
│   ├── _ipc_node_base.py     _IpcNodeBase: shared listener pipeline + pluggable liveness
│   ├── swarm_process.py      simulation: spawns subprocess, step, node strategies
│   ├── physical_node.py      physical deployment: connect to running device, auto-reconnect
│   └── device_manager.py     heterogeneous fleet: simulation + physical nodes
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
├── tests/                  Pytest test suite (578 tests, one sub-package per phase)
│   ├── dsl/                Phase 1 tests (6 files)
│   ├── transpiler/         Phase 2 tests (3 files)
│   ├── compiler/           Phase 3 tests (3 files)
│   ├── ipc/                Phase 4 tests (7 files, +test_physical_node.py, +test_liveness_strategy.py)
│   ├── grammar/            Phase 5 tests (5 files)
│   ├── metrics/            Phase 6 tests (6 files)
│   └── visualization/      Phase 7 tests (4 files)
├── cpp_transpiled/         ← Generated C++ code (git-ignored)
└── build/                  ← Compiled binaries (git-ignored)
```

## Examples

The `examples/` directory contains Python ports of real FCPP C++ algorithms from
`fcpp-sample-project` and `fcpp-exercises`, plus original DSL-showcase examples, written
for demonstration and learning.  Each file defines an `@aggregate_function` class
(transpilable to C++) and a pure-Python `_demo_simulate()` that runs the algorithm and
writes per-node log files to `examples/logs/`.

Run any example:

```bash
cd <repo-root>
PYTHONPATH=src python src/fcpp_bridge/examples/<example>.py
```

`end_to_end.py` supports per-step execution so you can skip stages you've already run:

```bash
# validate + transpile only (no C++ compiler needed)
PYTHONPATH=src python src/fcpp_bridge/examples/end_to_end.py --steps validate transpile

# resume from compile (loads the C++ artifact written by a prior transpile run)
PYTHONPATH=src python src/fcpp_bridge/examples/end_to_end.py --from compile

# jump straight to the simulation
PYTHONPATH=src python src/fcpp_bridge/examples/end_to_end.py --steps run --nodes 20
```

See `TUTORIAL_simple.md §Running individual steps` for the full flag reference.

All 7 main examples subclass `AbstractExample` (v2.0) — `_demo_simulate()` is replaced by a class that implements `initial_positions`, `initial_states`, `round_step`, `log_header`, `log_line`.  Nodes are managed as `dict[int, state]` so nodes can join or leave dynamically during simulation.

| Python file               | C++ source / origin                                | Key FCPP primitives                                                                                |
| ------------------------- | -------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `spreading_collection.py`    | `fcpp-sample-project/lib/spreading_collection.hpp` | `rectangle_walk`, `abf_distance`, `mp_collection`, `broadcast`                                            |
| `channel_broadcast.py`       | `fcpp-sample-project/lib/channel_broadcast.hpp`    | `rectangle_walk`, `bis_distance`, `broadcast`                                                             |
| `collection_compare.py`      | `fcpp-sample-project/lib/collection_compare.hpp`   | `rectangle_walk`, `abf_distance`, `sp_collection`, `mp_collection`, `wmp_collection`, `count_hood`        |
| `message_dispatch.py`        | `fcpp-sample-project/lib/message_dispatch.hpp`     | `rectangle_walk`, `bis_distance`, `nbr`, `min_hood`, `sp_collection`, `spawn`, `old`                     |
| `chain_decaying.py`          | `fcpp-sample-project/run/chain_decaying.hpp`       | `nbr`, `min_hood`                                                                                         |
| `worker_role_assignment.py`  | **original** — v1.5–v1.9 DSL showcase             | `bis_distance`, `nbr`, `min_hood`, `count_hood`, `sp_collection`, `spawn`, `old`, `self_uid()` + `match/case` + `RoleCommunicationType` |
| `communication_roles_assignment.py` | **original** — v1.9 DSL showcase           | `bis_distance`×2, `nbr`, `min_hood`, `old`×2, `broadcast`, `self_uid()` + `match/case` + `CommunicationRole` |

See [EXAMPLES_JOURNAL.md](development_history/EXAMPLES_JOURNAL.md) for the full algorithm notes, source inventory,
and resume instructions.

## Documentation

- **[bridge.md](../bridge.md)** — Complete architecture & implementation log
- **[Design Decisions](../bridge.md#part-6-key-design-decisions)** — Why this approach
- **[Phase-by-Phase Rollout](../bridge.md#part-5-phase-by-phase-rollout)** — Detailed checklist
- **[Glossary](../bridge.md#appendix-glossary)** — Terminology
- **[VISUALIZATION.md](VISUALIZATION.md)** — Phase 7: ANTLR generation & visualization plugin
- **[DSL_GUIDE.md](DSL_GUIDE.md)** — Complete Python DSL reference: primitives, types, mixins, C++-alike grammar (if/while/for/match→switch), transpilation pipeline, limitations, full examples
- **[TUTORIAL_simple.md](TUTORIAL_simple.md)** — Beginner tutorial: 20-node hop-channel (BIS + nbr/min_hood + broadcast); per-step CLI
- **[TUTORIAL_in_depth.md](TUTORIAL_in_depth.md)** — Production tutorial: custom class, listener proxy, node management, heartbeat
- **[WORKER_ROLE_ASSIGNMENT.md](development_history/WORKER_ROLE_ASSIGNMENT.md)** — Design notes for the `worker_role_assignment.py` example: algorithm walkthrough, DSL feature decisions, 7 evolution paths
- **[PHYSICAL_DEPLOYMENT.md](PHYSICAL_DEPLOYMENT.md)** — v1.2: analysis, design decisions, and changes for physical device deployment support
- **[PHYSICAL_DEPLOYMENT_JOURNAL.md](PHYSICAL_DEPLOYMENT_JOURNAL.md)** — v1.2: step-by-step status tracker and architecture diagram

## What Works

- ✅ `@aggregate_function` decorator with full pre-transpilation validation
- ✅ `AggregateType.infer()`: Python types → C++ types (primitives, list, tuple, dict, set, frozenset, Optional, Union, dataclass, TypeVar, TemplateParam; full C++14-C++23 proxy classes)
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

- ✅ `PythonAstVisitor`: match guard clauses (`case X if cond:` → `case X: if (cond) { ... } break;`) and OR patterns (`case A | B:` → `case A: case B:` C++14 fallthrough labels)
- ✅ `AbstractExample` (v2.0): Template Method base class for demo simulations; subclasses override `initial_positions`, `initial_states`, `round_step`, `log_header`, `log_line`, and optional hooks (`on_simulation_start`, `on_simulation_end`, `on_round_complete`); `run(num_rounds)` handles node lifecycle + log file I/O; all 7 main examples subclass it

## Known Gaps (Future Work)

- Phase 7: Multi-swarm coordination UI
- Phase 7: Run `generate_antlr.py --download` to activate the ANTLR4 parser path (requires Java 11+)

## v2.0 — Match guard clauses, OR patterns, AbstractExample, and examples refactoring

- **`transpiler/python_ast_visitor.py`** — `visit_Match` extended with two new patterns:
  - **Guard clauses** (`case X if cond:`): body wrapped in `if (cond) { ... }`; `break` still follows unconditionally so a non-matching guard exits the switch.  Guard expressions must not contain aggregate primitives (CALL-counter rule).
  - **OR patterns** (`case A | B | C:`): each value emitted as a separate `case X:` label (C++14 fallthrough), sharing one body and one `break`.
  - **Combined**: `case A | B if cond:` wraps the shared OR body in an `if` block.
- **`development_history/match_guard_or_pattern.md`** — full feature doc: AST note, generated C++ examples, CALL-counter warning, remaining limitations (sequence / class / capture patterns).
- **`DSL_GUIDE.md §6.7`** — updated with guard clause and OR pattern syntax, generated C++ examples, expanded limitations table, and summary table new rows.
- **`examples/abstract_example.py`** — new `AbstractExample(ABC)` base class (Template Method pattern):
  - Abstract methods: `log_prefix`, `initial_positions()`, `initial_states(positions)`, `round_step(round_num, positions, states)`, `log_header(node_id, state)`, `log_line(round_num, node_id, state)`.
  - Optional hooks: `on_simulation_start()`, `on_simulation_end()`, `on_round_complete(round_num, positions, states)`.
  - `run(num_rounds)` — creates log dir, iterates rounds, manages per-node log files, handles nodes that join (new dict key) or leave (key removed), calls hooks.
  - Nodes represented as `dict[int, state]` throughout: dynamic join/leave is first-class, not an afterthought.
- **All 7 main examples refactored** — `_demo_simulate()` replaced by a `class XxxExample(AbstractExample)`:
  `spreading_collection.py`, `channel_broadcast.py`, `collection_compare.py`, `message_dispatch.py`, `chain_decaying.py`, `worker_role_assignment.py`, `communication_roles_assignment.py`.
  Extra log files (receiver_messages.log, comm_receiver_messages.log) managed via `on_simulation_start / on_simulation_end / on_round_complete`.
- **`bridge.md`** (root `src/bridge.md`) — fully updated from v0.6/v1.3 to v2.0: new file structure, entries 17–20 in the getting-started checklist, updated test count (624).
- **8 new transpiler tests**: `test_match_guard_simple`, `test_match_guard_expression`, `test_match_guard_body_indented`, `test_match_guard_default_with_guard`, `test_match_or_pattern_two_values`, `test_match_or_pattern_three_values`, `test_match_or_pattern_body_once`, `test_match_or_pattern_with_enum_folding`.

## v1.8 — Logging refactor + v1.9 gap-analysis plan

- **Library `print()` → `get_logger()`**: all status/diagnostic `print()` calls in
  library code replaced with the `fcpp_bridge.log` infrastructure (`get_logger(__name__)`).
  Affected files: `compiler/compiler_core.py`, `ipc/swarm_process.py`,
  `ipc/physical_node.py`, `ipc/device_manager.py`, `runtime/runtime_generator.py`.
  `visualization/text_dashboard.py` intentionally unchanged (its output IS the
  visualizer output). `grammar/generate_antlr.py` intentionally unchanged (CLI tool).
- **`examples/_example_utils.py`** — new shared utility module with `report_validation(cls)`
  and `report_transpilation(cls)` helpers.  Every example's `main()` now delegates the
  validate+transpile boilerplate to these helpers, eliminating 5+ copies of the same
  `try/except + for w in warnings` block.  Examples updated: `spreading_collection.py`,
  `channel_broadcast.py`, `message_dispatch.py`, `chain_decaying.py`,
  `collection_compare.py`, `worker_role_assignment.py`.
- **`development_history/V1_9_PLAN.md`** — full v1.9 gap-analysis document covering:
  Gap #1 (receiver UID: why `broadcast` is the solution), Gap #2 (`set_t{node.uid}`
  transpilation), Gap #3 (`min_hood` tuple → `std::make_tuple`), Gap #4 (`nbr_uid()`
  vs `self_uid()` distinction), Gap #6 (`ActivePingStrategy` C++ ping handler),
  Gap #7 (`DeviceManager.accept_registrations`), Gap #8 (`PhysicalNode` RAII-style
  exception cleanup), Gap #9 (`OutputChannel` multi-channel output design with
  OOP/Prototype hierarchy).
- **No new tests** — test count remains 611.  The library refactor is
  transparent: callers who have not called `configure_bridge_logging()` see no output
  at all (NullHandler default); callers who opt in get structured log records instead
  of bare prints.

## v1.7 — RoleCommunicationType + REPEATER rename + RUBBLES_REMOVER as endpoint

- **`examples/worker_role_assignment.py`**:
  - Renamed `RIPETITOR` → `REPEATER` (corrected spelling/English).
  - Added `RoleCommunicationType(IntEnum)` — ENDPOINT(0), RECEIVER(1), REPEATER(2) — and
    `ROLE_COMM_TYPE` dict mapping each `WorkerRole` to its communication role.
  - Reclassified `RUBBLES_REMOVER` (6) as ENDPOINT: it now injects sensor-reading messages
    toward RECEIVER via spawn.
  - Reclassified `UNASSIGNED` (0) as REPEATER (passive relay candidate).
  - Updated `ENDPOINT_ROLES` (added role 6), replaced `RELAY_ROLES` with `REPEATER_ROLES`.
  - Demo simulation generates random sensor readings in endpoint messages.
- **No transpiler changes** — `RoleCommunicationType` is Python-only metadata; the DSL
  `compute()` logic drives C++ behavior via `is_endpoint`/`is_receiver` booleans.
- **No new tests** — test count remains 611.

## v1.6 — self_uid() primitive + worker_role_assignment refactor

- **`python_dsl/primitives/self_uid.py`** — new `SelfUid` primitive; `self_uid()` in Python DSL
  transpiles to `node.uid` in C++ (direct node-field access, **no CALL counter**).
  Safe to call inside `match/case` branches or `if/else` arms.
  In the Python execution layer `self_uid()` returns `0` (placeholder); generated C++ is correct.
- **`transpiler/python_ast_visitor.py`** — `self_uid()` special case added before the built-in
  fallthrough: emits `node.uid`, never adds `CALL`.
- **`examples/worker_role_assignment.py`** — updated to use `self_uid()` in steps 2 (tie-breaker),
  4 (`sp_collection` local value), and 5 (spawn key sender); `WorkerRole` enum entries annotated
  with `# N — description`; step 7 `match/case` refactored so each case includes a role-specific
  task description (or a clearly marked placeholder for real-world implementation).
- **`development_history/WORKER_ROLE_ASSIGNMENT.md`** — documentation updated to match code.
- **1 new test** — `test_ast_visitor_self_uid` in `tests/transpiler/test_python_ast_visitor.py`.

## v1.5 — Worker Role Assignment example (DSL showcase)

- **`examples/worker_role_assignment.py`** — original (non-ported) example; 24-node disaster-response
  swarm with 8 `WorkerRole` values (UNASSIGNED, RECEIVER, LIDAR, INFRARED_SENSOR, REPEATER,
  TORCHLIGHT_MICROPHONE, RUBBLES_REMOVER, FLYING_OVERSEER).  Demonstrates `match/case` → C++ `switch`
  and `spawn`-based message routing from endpoint sensor nodes to RECEIVER nodes every 10 rounds.
- All 7 aggregate primitives (`bis_distance`, `nbr`, `min_hood`, `count_hood`, `sp_collection`,
  `spawn`, `old`) called before the `match/case` — required by FCPP's CALL-counter alignment.
- **`development_history/WORKER_ROLE_ASSIGNMENT.md`** — algorithm design notes, DSL feature rationale,
  `node.uid` placeholder explanation, 7 evolution paths (dynamic election, hierarchical relay tiers,
  message TTL, multi-receiver redundancy, visualization integration).

## v1.4 — C++-alike DSL control flow + per-step pipeline CLI

- **`PythonAstVisitor`** — full statement-level transpilation: `if`/`elif`/`else`, `while`,
  `for range(...)`, `match/case` → C++ `switch`, variable assignments (`auto` on first use,
  plain assignment on re-use), `return`, `pass`, `break`, `continue`; ternary expressions,
  boolean operators (`and`/`or`/`not`), unary operators, list/tuple literals, method calls,
  built-ins (`abs`, `int`, `float`, `bool`)
- **`Transpiler._transpile_method_body`** replaces `_transpile_method_return`; the entire
  `compute()` body is transpiled (not just the first `return` expression)
- **`AggregateProgram.g4`** upgraded to Phase 6: `stmt`, `ifStmt`, `whileStmt`, `forStmt`,
  `switchStmt`, `assignStmt`, `returnStmt` parser rules; `TernaryExpr`, `BoolExpr`, `NotExpr`
  expression alternatives; `ELSE`, `WHILE`, `FOR`, `IN`, `RANGE`, `SWITCH`, `CASE`,
  `DEFAULT`, `BREAK`, `NOT`, `AND`, `OR`, `ASSIGN` lexer tokens
- **`DSL_GUIDE.md`** — new comprehensive reference: all primitives, types, mixins,
  C++-alike grammar guide, transpilation pipeline diagram, limitations, four full examples
- **`end_to_end.py`** — `--steps` and `--from` CLI flags for per-step execution;
  `transpile` saves `consensus_latest.cpp`; `compile` saves `.latest_binary`; missing
  artifacts produce a clear error with the exact command to run

## v1.3 — Pluggable liveness strategies

- **`LivenessStrategy` ABC** (`ipc/liveness_strategy.py`): `on_snapshot(snapshot)`,
  `check(**kwargs) → Dict[int, bool]`, `discard(node_id)`, `close()`.
  Unknown kwargs passed to `check()` must be silently ignored for forward compatibility.

- **`PassiveHeartbeatStrategy(timeout=30.0)`** (default): alive if a snapshot containing
  the node was received within `timeout` seconds. No messages sent; zero C++ runtime
  requirements. `timeout` can be overridden per call: `check(timeout=5.0)`.

- **`ActivePingStrategy(backend_getter, ping_timeout=2.0)`**: sends `{"cmd": "ping",
"node_id": <id>}` via the IPC backend; alive if `{"status": "pong"}` is received within
  `ping_timeout` seconds. `backend_getter` is a callable (e.g. `lambda: node.backend`) so
  the strategy always sees the current backend after reconnects. **Requires** the compiled
  FCPP binary to implement the ping handler.

- **`AlwaysAliveStrategy()`**: every known node is always alive. Useful for testing, fixed
  sensor grids, or disabling liveness checks without removing the monitor thread.

- **`_IpcNodeBase` integration**:
  - Constructor kwarg: `liveness_strategy=<strategy>` (default: `PassiveHeartbeatStrategy()`)
  - Runtime swap: `node.set_liveness_strategy(new_strat)` — closes old strategy, installs new
  - `check_liveness(timeout=30.0, **kwargs)` forwards all kwargs to the strategy's `check()`
  - `_heartbeat_timestamps` kept as a backward-compat property (returns `strategy._timestamps`
    for passive strategy; empty dict for others)

- **All constructors accept `liveness_strategy=`**: `SwarmProcess`, `PhysicalNode`,
  `DeviceManager.add_simulation`, `DeviceManager.add_physical`.

## v1.2 — Physical device deployment

- **`_IpcNodeBase`**: private base class that `SwarmProcess` and `PhysicalNode` both inherit from;
  contains the shared listener pipeline, passive heartbeat, and `get_state()` pull path.
- **`PhysicalNode(host, port, backend_type, reconnect_interval)`**: connects Python to a physical
  device (robot, drone, phone, sensor, workstation) that is already running a compiled FCPP binary;
  no subprocess is spawned.
  - `connect()` — creates `HttpBackend` or `GrpcBackend`; subscribes push updates.
  - `close()` — disconnects Python side; the physical device keeps running.
  - `start_auto_reconnect()` / `stop_auto_reconnect()` — background thread that calls `connect()`
    whenever `is_connected` is False (survives transient link drops).
  - `on_neighbor_joined(cb)` — `cb(node_id)` fires the first time a node_id appears in any
    incoming `SwarmSnapshot` (FCPP-level neighbor join via radio).
  - `on_neighbor_left(cb)` — `cb(node_id)` fires when the heartbeat monitor declares a node
    silent for longer than the configured timeout (FCPP-level neighbor leave).
  - `start_heartbeat_monitor(interval, timeout, on_dead)` — overrides the base method to also
    trigger `on_neighbor_left` callbacks and purge the node from `_seen_node_ids`.
- **`DeviceManager` extended**:
  - `add_simulation(name, binary_path, ...)` → `SwarmProcess` (explicit form of existing `add()`)
  - `add_physical(name, host, port, backend_type)` → `PhysicalNode`
  - `start_all()` — starts only simulation nodes; `connect_all()` connects only physical nodes
  - `step_all()` — steps only `SwarmProcess` instances; `PhysicalNode` entries are silently skipped
    (physical devices run their own FCPP round loop)
  - `total_nodes()` uses the new `node_count` property: `SwarmProcess.node_count = num_nodes`;
    `PhysicalNode.node_count = len(seen_node_ids) or 1`

See **[PHYSICAL_DEPLOYMENT_JOURNAL.md](PHYSICAL_DEPLOYMENT_JOURNAL.md)** for full architecture
notes, design decisions, and the class hierarchy diagram.

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

| Aspect      | fcpp_py_porting                  | fcpp_bridge                                             |
| ----------- | -------------------------------- | ------------------------------------------------------- |
| Scope       | Vec2/Vec3 + simulation callbacks | Full DSL + code gen + IPC                               |
| Compilation | Once (build time)                | Dynamic (per program)                                   |
| Callback    | Python calls into C++            | C++ runs independently                                  |
| Status      | Mature (Phase 2 tested)          | 7 phases + type system + v1.2 IPC + physical deployment |

**Note**: fcpp_py_porting is a reference/learning project. fcpp_bridge is the production design.

## License

Same as parent project.
