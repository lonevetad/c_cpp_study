---
name: project-fcpp-bridge
description: "fcpp_bridge v1.9 — 675 tests; standalone repo at ../fcpp_bridge/ (flat layout); FCPP_INCLUDE_PATH env var for C++ headers"
metadata: 
  node_type: memory
  type: project
  originSessionId: e0e1ffd8-f841-4b03-8663-5d988f484735
---

**In-development location** (monorepo): `src/fcpp_bridge/`  
**Standalone repo** (2026-05-29): `/home/cronomatita/Desktop/prog/cpp/fcpp_bridge/` — flat layout, package at `fcpp_bridge/fcpp_bridge/`

Run tests in monorepo: `src/expr_eval_py/expr_eval_py_env/bin/pytest src/fcpp_bridge/tests/ -q` (after `pip install -e .`; or prefix `PYTHONPATH=src`)  
Run tests in standalone: `pytest fcpp_bridge/tests/ -v` (after `python3 -m venv .venv && pip install -e .`; or `PYTHONPATH=. pytest fcpp_bridge/tests/`)

**FCPP C++ dependency**: set `export FCPP_INCLUDE_PATH=/path/to/fcpp/src` before running examples that compile C++.  
`compiler_core.py` and `cmake_generator.py` now read this env var (previously had a broken hardcoded path).

## Phase status (as of 2026-05-28)

| Phase | Component               | Status     | Tests |
|-------|-------------------------|------------|-------|
| 1     | Python DSL              | ✅ Done    | 42    |
| 2     | Transpiler              | ✅ Done    | 74    |
| 3     | Compiler pipeline       | ✅ Done    | 15    |
| 4     | Runtime & IPC           | ✅ Done    | 55    |
| 5     | Language parser         | ✅ Done    | 47    |
| 6     | Scaling & backends      | ✅ Done    | 35    |
| Audit | 64-primitive coverage   | ✅ Done    | +111  |
| 7     | Visualization & ANTLR gen| ✅ Done   | 16    |
| v0.8  | Extended type system    | ✅ Done    | +37   |
| v0.9  | OOP/Prototype/logging   | ✅ Done    | +50   |
| v1.0  | Network listener pipeline | ✅ Done  | +38   |
| v1.1  | Compiler customization + tutorials | ✅ Done | +3 |
| v1.2  | Physical device deployment | ✅ Done | +40 |
| v1.3  | Pluggable liveness strategies | ✅ Done | +23 |
| v1.4  | C++-alike DSL grammar + full-body transpilation | ✅ Done | +32 |
| v1.5  | worker_role_assignment.py example (match/case + spawn) | ✅ Done | +0  |
| v1.6  | self_uid() primitive (node.uid); enum comments; step 7 role tasks | ✅ Done | +1 |
| v1.7  | RoleCommunicationType enum; RIPETITOR→REPEATER; RUBBLES_REMOVER→endpoint | ✅ Done | +0 |
| v1.8  | Library `print()`→`get_logger()`; `examples/_example_utils.py`; `V1_9_PLAN.md` | ✅ Done | +0 |
| v1.8.1 | `worker_role_assignment`: `ROLE_CYCLE` (5 extra repeaters, `DEVICES=26`); `ROLE_COMM_TYPE` frozenset-unpack bug fix | ✅ Done | +0 |
| v1.8.2 | Enum-value refactoring: `WorkerRole.X.value` in comparisons + case labels; `ROLE_CYCLE` uses enum members; no magic integers | ✅ Done | +0 |
| v1.8.3 | Named constants `ADDITIONAL_REPEATERS_EACH_CYCLE` + `FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS`; `DEVICES` derived; `ROLE_CYCLE` uses `*([WorkerRole.REPEATER] * N)` | ✅ Done | +0 |
| v1.8.4 | Transpiler enum constant-folding: `PythonAstVisitor(constants=)` + `_resolve_dotted_chain()`; `visit_Attribute` folds `IntEnum.X.value` to int literals; wired via `compute.__globals__` | ✅ Done | +5 |
| v1.8.5 | Example import fix: `from examples._example_utils` → `from fcpp_bridge.examples._example_utils` in all 6 example files; `PYTHONPATH` requirement documented in README + both TUTORIALs | ✅ Done | +0 |
| v1.9 | `_example_utils`: `neighbors_of`, `SPAWN_STATUS_*`, `build_positions`; 6 examples refactored to use shared helpers; `communication_roles_assignment.py` new example; `FUTURE_EXERCISES.md`; `examples_cohesiveness.md` | ✅ Done | +0 |
| v2.0 | Match guard clause + OR patterns in transpiler; `AbstractExample` Template Method base class; all 7 examples refactored (no more `_demo_simulate`); dynamic node dict | ✅ Done | +8 |
| v1.9-A | Transpiler: `frozenset`→`set_t`, `min_hood`/`max_hood`+Tuple→`std::make_tuple`; `worker_role_assignment` broadcast step; `node_uid__placeholder_flagging.md` updated | ✅ Done | +5 |
| v1.9-B | PhysicalNode RAII connect(); get_state() error → _connected=False | ✅ Done | +3 |
| v1.9-C | OutputChannel hierarchy (ABC + Logging/File/Callback/ProxyOutputChannel); DeviceManager output_channel= kwarg | ✅ Done | +15 |
| v1.9-D | C++ ping/pong handler in RuntimeGenerator template; DeviceManager.accept_registrations() HTTP server | ✅ Done | +8 |
| v1.9-E | AbstractExample rewritten: run() invokes full toolchain (validate→transpile→compile→SwarmProcess); removed round_step/initial_states; added aggregate_class, build_dir, cpp_dir; updated on_round_complete(snapshot); SwarmProcess.latest_snapshot() added | ✅ Done | +10 |
| v1.9-F | All 7 example AbstractExample subclasses migrated to toolchain path: removed round_step/initial_states/pure-Python helpers; added aggregate_class property; log methods use state_data: Any (dict access); on_round_complete stores _last_snapshot; on_simulation_end uses snapshot; collection_compare + message_dispatch got old() round counters; receiver logs simplified; 7 smoke tests added | ✅ Done | +7 |

**Total: 672 tests — 672 pass, 0 fail.**

**v1.9 — communication_roles_assignment + shared helpers** (2026-05-28):
- `examples/_example_utils.py`: added `SPAWN_STATUS_BORDER/INTERNAL/TERMINATED` constants, `neighbors_of(positions, nid, comm)` shared function, `build_positions(n, side_x, side_y, seed)` helper
- All 6 main examples refactored: removed local `neighbors_of` closures, now import from `_example_utils`; `message_dispatch.py` + `worker_role_assignment.py` use `SPAWN_STATUS_*` aliases
- `examples/communication_roles_assignment.py` NEW: `CommunicationRole(UNASSIGNED/SENDER/REPEATER/RECEIVER)`; `NODES=15`, `SINK_POINTS=2`, `SOURCE_POINTS=3`; isolation migration + point placement setup; DSL: `bis_distance×2`, `nbr`, `min_hood`, `old×2`, `broadcast`, `match/case`; 3272 bytes C++; 12 messages delivered
- `development_history/examples_cohesiveness.md`: cohesiveness analysis + refactoring plan
- `development_history/FUTURE_EXERCISES.md`: 8 future exercise hints (FE-1 through FE-8)
- `development_history/EXAMPLES_JOURNAL.md`: new example notes + v1.9 refactoring entry
- 616 tests unchanged

## What was implemented per phase

**Phase 1** — `python_dsl/`: all 64 FCPP primitive classes across 7 coordination headers (basics/utils/spreading/collection/geometry/election/time); `@aggregate_function` decorator; `mixin_collection`, `mixin_geometry`, `mixin_gossip`, `mixin_broadcast`, `mixin_election` (6 methods), `mixin_time` (13 methods). All mixin methods return proper primitive objects.

**Phase 2** — `transpiler/__init__.py`: `CppCodeBuilder`, `PythonAstVisitor` (all binary/comparison ops, calls, constants, attrs, subscripts, lambdas). `visit_Call` injects `CALL` as first arg for all 64 FCPP primitives. `visit_Lambda` emits C++14 generic lambdas `[=](auto a, auto b) { return ...; }` for G&& callable parameters. `_FCPP_PRIMITIVES` dict maps all 64 names → 7 header abbreviations. `Transpiler._generate_compute()` returns `(code, used_prims)` tuple.

**Phase 3** — `compiler/__init__.py`: `ProgramCache` (SHA-256 hash, manifest), `Compiler` (GCC invocation, caching), `CmakeGenerator` (CMakeLists.txt generation), `CompilationErrorParser` (structured GCC/Clang diagnostics via regex). `-fuse-ld=lld` is platform-conditional (see below).

**Phase 4** — `ipc/__init__.py`: `UnixSocketBackend`, `HttpBackend`, `GrpcBackend` (full implementation with streaming background thread), `SwarmProcess` (subprocess lifecycle), `DeviceManager` (multi-swarm coordination: `add/remove/get`, `start_all/close_all`, `send_all/step_all/get_all_states`). `ipc/fcpp_swarm.proto`: full gRPC service definition. `runtime/__init__.py`: C++ header generators.

**v1.8.5 — Example import fix + PYTHONPATH docs** (2026-05-28):
- All 6 example files: `from examples._example_utils import` → `from fcpp_bridge.examples._example_utils import`; bare `examples` was not on `sys.path` under `PYTHONPATH=..` or `PYTHONPATH=src` (neither puts `src/fcpp_bridge/` on the path)
- `README.md`, `TUTORIAL_simple.md`, `TUTORIAL_in_depth.md`: added `> **PYTHONPATH requirement**` blockquote explaining why `src/` must be on the path, `export` vs inline prefix, and `PYTHONPATH=..` for `src/fcpp_bridge/` working directory
- `README.md`: fixed Quick Start comment `611 pass` → `616 pass`
- 616 tests unchanged

**v1.8.4 — Transpiler enum constant-folding** (2026-05-28):
- `transpiler/python_ast_visitor.py`: `PythonAstVisitor.__init__` now accepts optional `constants: dict`; new `_resolve_dotted_chain()` helper walks Attribute chains and resolves against the dict; `visit_Attribute` constant-folds int/float/bool resolutions to literal strings — enables valid C++ case labels for IntEnum values
- `transpiler/transpiler_core.py`: `_transpile_method_body` passes `getattr(method, '__globals__', {})` as `constants` to the visitor, so all module-level names (including IntEnum classes) are available for folding
- `tests/transpiler/test_python_ast_visitor.py`: 5 new tests; module-level `_TestRole(IntEnum)` + `_body_with_consts()` helper
- All docs updated: `DSL_GUIDE.md` §6.7 + §9, `WORKER_ROLE_ASSIGNMENT.md` caveat replaced, `PRE_V19_REFACTORING.md` caveat updated, `EXAMPLES_JOURNAL.md`, `README.md` v1.8.4 row
- 616 tests pass

**v1.8.3 — Named swarm-size constants** (2026-05-28):
- `worker_role_assignment.py`: extracted `ADDITIONAL_REPEATERS_EACH_CYCLE = 5` and `FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS = 2`; `DEVICES = len(ROLE_CYCLE) * FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS`; `ROLE_CYCLE` uses `*([WorkerRole.REPEATER] * ADDITIONAL_REPEATERS_EACH_CYCLE)`
- All docs updated: `WORKER_ROLE_ASSIGNMENT.md` (scenario rewritten with formula tables and tweaking guide), `PRE_V19_REFACTORING.md` (v1.8.3 section), `EXAMPLES_JOURNAL.md` (note added), `README.md` (v1.8.3 row)
- 611 tests pass unchanged

**v1.8.2 — Enum-value refactoring** (2026-05-28):
- `worker_role_assignment.py`: `WorkerRole.X.value` in `is_receiver`/`is_endpoint` guards; `case WorkerRole.X.value:` dotted-name value patterns; `ROLE_CYCLE` uses `WorkerRole` members; `WorkerRole(x).name` → `x.name`; `int(r)` → `r.value` in output
- Docstring note on match/case updated: dotted `a.b.c` patterns are always value patterns in Python 3.10+
- `development_history/PRE_V19_REFACTORING.md`: new history file documenting v1.8.1 + v1.8.2
- 611 tests pass unchanged

**v1.8.1 — ROLE_CYCLE + ROLE_COMM_TYPE fix** (2026-05-28):
- `worker_role_assignment.py`: `ROLE_CYCLE` (13-slot: 8 standard + 5 extra `WorkerRole.REPEATER`); `DEVICES=26` (2 cycles); totals: REPEATER-type=14 > ENDPOINT-type=10 > RECEIVER-type=2
- Bug fix: `ROLE_COMM_TYPE = {**ENDPOINT_ROLES, ...}` raised `TypeError` (frozenset ≠ mapping); fixed with dict comprehensions
- 611 tests pass unchanged

**v1.8 — Logging refactor + _example_utils + v1.9 gap plan** (2026-05-28):
- Library `print()` calls replaced with `get_logger(__name__)` in: `compiler/compiler_core.py`, `ipc/swarm_process.py`, `ipc/physical_node.py`, `ipc/device_manager.py`, `runtime/runtime_generator.py`
- `examples/_example_utils.py`: new shared `report_validation(cls)` and `report_transpilation(cls)` helpers
- All 6 example `main()` functions refactored to use helpers (no more repeated `try/except + for w in warnings`)
- `development_history/V1_9_PLAN.md`: full gap-analysis doc (gaps #1–#9) with design proposals
- 611 tests pass unchanged

**v1.7 — RoleCommunicationType + REPEATER rename + RUBBLES_REMOVER→endpoint** (2026-05-28):
- `examples/worker_role_assignment.py`: renamed `RIPETITOR` → `REPEATER`; added `RoleCommunicationType(IntEnum)` (ENDPOINT=0, RECEIVER=1, REPEATER=2) + `ROLE_COMM_TYPE` dict; `RUBBLES_REMOVER` (6) reclassified endpoint; `UNASSIGNED` (0) reclassified repeater; `ENDPOINT_ROLES` includes role 6; `RELAY_ROLES` replaced by `REPEATER_ROLES`; `is_endpoint` includes role 6; demo sensor readings use `random.uniform`; no transpiler changes, no new tests
- Key design: `RoleCommunicationType` is Python-only metadata (not transpiled); behavior driven by `is_endpoint`/`is_receiver` booleans in `compute()`

**v1.6 — self_uid() + worker_role_assignment refactor** (2026-05-28):
- `python_dsl/primitives/self_uid.py`: new `SelfUid` Primitive class
- `transpiler/python_ast_visitor.py`: `self_uid()` → `node.uid` special case (no CALL counter); added before `max`/`min` builtins block
- `python_dsl/primitives/__init__.py` + `python_dsl/__init__.py`: added `SelfUid` export
- `tests/transpiler/test_python_ast_visitor.py`: `test_ast_visitor_self_uid` asserts output == "node.uid" and CALL not present
- `examples/worker_role_assignment.py`: uses `self_uid()` in steps 2, 4, 5; enum value inline comments (e.g. `# 0 — passive node`); step 7 match/case refactored with role-specific task comments + dummy placeholder variables
- `development_history/WORKER_ROLE_ASSIGNMENT.md`: v1.6 table row; self_uid() note in algorithm; updated spawn+old code; Evolution 1 marked partially done; Known Limitations table updated (sender UID fixed, receiver UID still placeholder)

**v1.4 — C++-alike DSL grammar + full-body transpilation** (2026-05-26):
- `transpiler/python_ast_visitor.py`: added `visit_IfExp` (ternary `a if c else b` → `(c ? a : b)`), `visit_BoolOp` (`and`/`or` → `&&`/`||`), `visit_UnaryOp` (`not`/`-`/`+`), `visit_Assign` (`auto x = expr;` on first use), `visit_AnnAssign`, `visit_AugAssign` (`x += y;`), `visit_Return` (`return expr;`), `visit_If` (if/elif/else), `visit_While`, `visit_For` (range-based only), `visit_Match` (Python 3.10+ → C++ `switch`), `visit_Expr`, `visit_Pass`, `visit_Break`, `visit_Continue`, `visit_List`, `visit_Tuple`. Updated `visit_Call` to handle keyword args + method calls. Added `transpile_statements(stmts, indent=4)` helper. Added `declared_vars: Set[str]` for tracking first-use `auto` declarations.
- `transpiler/transpiler_core.py`: `_generate_compute` now uses `_transpile_method_body` (full body) instead of `_transpile_method_return` (single return extraction). `_transpile_method_body` skips docstrings, calls `transpile_statements`, applies param remapping.
- `grammar/AggregateProgram.g4`: upgraded to Phase 6; added `stmt`, `ifStmt`, `whileStmt`, `forStmt`, `switchStmt`, `assignStmt`, `returnStmt`, `caseClause`, `defaultClause` parser rules; `TernaryExpr`, `BoolExpr`, `NotExpr` expression rules; new lexer tokens `ELSE`, `WHILE`, `FOR`, `IN`, `RANGE`, `SWITCH`, `CASE`, `DEFAULT`, `BREAK`, `NOT`, `AND`, `OR`, `ASSIGN`. ANTLR stubs need regeneration.
- `DSL_GUIDE.md`: new comprehensive guide — primitive reference (all 64), state types, mixins, §6 C++-alike grammar with examples for all new constructs, lambda section, transpilation pipeline diagram, limitations table, 4 complete examples.
- 32 new tests in `tests/transpiler/test_python_ast_visitor.py` (§Phase 6 sections).

**v1.3 — Pluggable liveness strategies** (2026-05-25):
- `ipc/liveness_strategy.py`: `LivenessStrategy` ABC with `on_snapshot(snapshot)`, `check(**kwargs) → Dict[int, bool]`, `discard(node_id)` (no-op default), `close()` (no-op default)
- `PassiveHeartbeatStrategy(timeout=30.0)`: records timestamps per node; `check(timeout=None)` compares `now - last_seen`; zero C++ runtime requirements
- `ActivePingStrategy(backend_getter, ping_timeout=2.0)`: sends `{"cmd": "ping", "node_id": n, "timeout": t}` via backend; expects `{"status": "pong"}`; returns False on any exception or no backend
- `AlwaysAliveStrategy()`: every known node always considered alive — for testing / fixed topologies
- `_IpcNodeBase` extended: `__init__(liveness_strategy=None)` defaults to `PassiveHeartbeatStrategy()`; `set_liveness_strategy(s)` closes old + installs new; `check_liveness(timeout, **kwargs)` delegates to strategy; `_update_heartbeats(snapshot)` → `strategy.on_snapshot(snapshot)`; `_discard_node_from_liveness(node_id)` → `strategy.discard(node_id)`; `close()` calls `strategy.close()` before backend
- Backward-compat: `_heartbeat_timestamps` property returns `strat._timestamps` live reference for `PassiveHeartbeatStrategy` — existing tests writing to the dict still work
- `SwarmProcess` and `PhysicalNode` constructors accept `liveness_strategy=` kwarg passed to `super().__init__`
- `DeviceManager.add()`, `add_simulation()`, `add_physical()` all accept `liveness_strategy=` kwarg
- 23 new tests in `tests/ipc/test_liveness_strategy.py`; analysis in `PHYSICAL_DEPLOYMENT.md` §8

**v1.2 — Physical device deployment** (2026-05-25):
- `ipc/_ipc_node_base.py`: `_IpcNodeBase` — shared base for `SwarmProcess` and `PhysicalNode`; contains listener pipeline (add/remove_listener, add/remove_node_listener, _dispatch_update), passive heartbeat (check_liveness, start/stop_heartbeat_monitor), get_state(), and base close(); `node_count` property overridden in each subclass
- `ipc/physical_node.py`: `PhysicalNode(host, port, backend_type="http", reconnect_interval=5.0)` — connects TO an already-running device (no subprocess); `connect()` creates HttpBackend or GrpcBackend; `close()` disconnects Python side only (device keeps running); `is_connected` bool property
- Auto-reconnect: `start_auto_reconnect(interval)` / `stop_auto_reconnect()` — daemon thread calls `connect()` while `is_connected is False`
- FCPP-level neighbor events: `on_neighbor_joined(cb)` fires first time a node_id appears in snapshot; `on_neighbor_left(cb)` fires via heartbeat timeout; `start_heartbeat_monitor` overridden to compose with neighbor_left callbacks and purge `_seen_node_ids`
- `DeviceManager` extended: `add_simulation(name, binary_path, ...)` → `SwarmProcess`; `add_physical(name, host, port, backend_type)` → `PhysicalNode`; `add()` backward-compat alias; `start_all()` / `connect_all()` separated; `step_all()` skips `PhysicalNode`; `total_nodes()` uses `node_count` property
- `SwarmProcess.node_count` → `num_nodes`; `PhysicalNode.node_count` → `len(_seen_node_ids) or 1`
- `SwarmProcess` now inherits from `_IpcNodeBase`; all duplicated heartbeat + listener code removed
- Progress tracked in `PHYSICAL_DEPLOYMENT_JOURNAL.md`

**v1.1 — Compiler customization + tutorials** (2026-05-24):
- `compiler/compiler_core.py`: `Compiler.__init__` now accepts `std: str = "c++26"`, `opt_level: str = "2"`, `extra_includes: Optional[List[str]] = None`; flags list built from these; `extra_flags` in `compile()` appended last for per-call override
- `TUTORIAL_simple.md`: beginner guide — 20-node hop-channel (BIS distance, nbr+min_hood hops, broadcast source ID), full pipeline walkthrough + pure-Python fallback simulation
- `TUTORIAL_in_depth.md`: production guide — `HopChannelSimulation` class with full lifecycle (build/start/pause/resume/stop), global `ListenerProxy` (logging listener + debug print), per-node listener for node 5, dynamic listener add/remove, compiler flag customization, all node addition strategies, heartbeat/liveness monitoring, complete feature reference table

**v1.0 — Network listener pipeline & node management** (2026-05-24):
- `ipc/updates_listener.py`: `UpdatesListener = Callable[[SwarmSnapshot], None]`
- `ipc/listener_proxy.py`: `ListenerProxy(mode="sequential"|"parallel")` — `add_listener(fn) → int`, `remove_listener(id)`, `__call__(snap)`, `close()`
- `SwarmProcess` node addition: `add_nodes_random(count, *, area, comm_range, max_speed, propulsion)`, `add_node_explicit(id, pos, **kw)`, `add_nodes_sequential(count, start_positions=None)`, `add_nodes(count)` (backward compat alias)
- `SwarmProcess.remove_node(node_id)` — simulation disconnection
- Passive heartbeat: `check_liveness(timeout)`, `start_heartbeat_monitor(interval, timeout, on_dead)`, `stop_heartbeat_monitor()`, `get_state()` now updates timestamps
- Listener pipeline: `add_listener(fn)→int`, `remove_listener(id)`, `add_node_listener(node_id, fn)→int`, `remove_node_listener(node_id, id)`; per-node listeners override global listener; proxy always used internally for uniform ID-based removal
- `_known_node_ids: set` and `_next_sequential_id: int` track all assigned node IDs; initialized from `range(num_nodes)` at `start()` time
- `IpcBackend.subscribe_state_updates` signature updated to use `UpdatesListener`; wired to `SwarmProcess._dispatch_update` in `start()`

**Phase 5** — `grammar/__init__.py`: `AggregateLanguageParser` (hand-written recursive-descent), `AstNode`, `ast_to_dsl`, `AntlrParser` wrapper. `_ALL_PRIMITIVES` frozenset: 64 entries. `grammar/AggregateProgram.g4`: `primitive` rule lists all 64 tokens; `primitiveCall` rule uses `argList?` for variable arity.

**Phase 6** — `metrics/__init__.py`: `MetricsCollector`, `StateHistory` (ring-buffer), `MetricsSummary` (mean/min/max/std), `MetricPoint`; `export_json`, `export_csv`.

**Phase 7** — `visualization/__init__.py`: `VisualizerBase` (ABC with `attach`/`detach`/`replay_from_history`), `TextDashboard` (terminal output, no deps), `SwarmVisualizer` (live matplotlib: 2 subplots — node count + mean/min/max shaded band; `get_data()` for headless testing), `create_visualizer` factory (tries matplotlib, falls back to TextDashboard). `grammar/generate_antlr.py`: CLI script — checks Java, downloads ANTLR 4.13.1 jar (`--download`), runs `java -jar antlr…-Dlanguage=Python3 -visitor -listener`, writes stubs to `grammar/__antlr_gen/`; activates `AntlrParser._antlr_available`. `grammar/requirements_antlr.txt`: `antlr4-python3-runtime==4.13.1`. `VISUALIZATION.md`: full how-to for both ANTLR generation and visualization plugin.

**v0.8 — Extended type system** — `python_dsl/types.py` refactored:
- `CppType`: replaced `@dataclass` with explicit `__init__` (keyword-only args after `name`); added `is_template`, `cpp_std`, `required_includes` fields; defensive copy of `required_includes` list in constructor; explicit `__repr__`, `__eq__`, `__hash__`.
- `_CppProxy`: uses `__init_subclass__(cpp_template, cpp_std, required_includes)` hook so each subclass declares its mapping via class keyword args; base assigns the class attributes with defensive copy.
- `_BoundCppProxy`: explicit `__init__` (removed `__slots__`).
- 14 proxy classes: `CppVector`, `CppArray[T,N]`, `CppSet`, `CppUnorderedSet`, `CppMultiSet`, `CppMap`, `CppUnorderedMap`, `CppMultiMap`, `CppPair` (C++14); `CppOptional`, `CppVariant`, `CppAny` (C++17); `CppSpan` (C++20); `CppExpected`, `CppMdSpan` (C++23).
- `TemplateParam("T")` for unresolved template type parameters (`typename T`).
- `AggregateType.infer()` extended: `set[T]`, `frozenset[T]`, `Optional[T]`, `Union[T1,T2,…]`, `TypeVar`, `bytes`.
- Transpiler auto-emits `required_includes` headers from inferred state type.
- Fixed `MetricsCollector.remove_callback`: `is not` → `!=` (bound-method equality).

**v0.9 — OOP / Prototype / Logging refactor:**
- `python_dsl/primitives.py`: `Primitive` base class with `__repr__`, `__eq__` (callables by identity, values by equality), `__hash__`, `clone()` (shallow copy, Prototype pattern), `clone_with(**changes)` (copy with attribute overrides). All 64 primitive classes inherit `Primitive` (or `Primitive, Generic[T]`). Zero-arg classes get explicit `__init__`. Class-level `has_callable_args: bool` and `callable_arg_positions: tuple` mark G&& callable constructor params:
  - `FoldHood(1)`, `Spawn(0)`, `Gossip(1)`, `SpCollection(3)`, `MpCollection(3,4)`, `WmpCollection(3,4)`, `OldNbr(1)`, `Split(1)`, `AbfDistance(1)`, `BisDistance(3)`, `FlexDistance(5)`, `BisKsourceBroadcast(5)`, `ListIdemCollection(6)`, `ListArithCollection(6)`, `WaveElection(1)`, `WaveElectionDistance(1)`
- `log.py`: `configure_bridge_logging(level, *, stream, filename, fmt, timed)`, `set_bridge_logging(bool)` uses level-based silencing (`_root.setLevel(CRITICAL+1)`) NOT `_root.disabled` (which is bypassed by `callHandlers` during propagation), `is_bridge_logging_enabled()`, `get_logger(name)`. Integrated into validators, decorators, transpiler.
- `validators.py`: `ValidationRule` ABC (abstract `check(cls) -> list[str]`). Concrete rules: `MarkerRule`, `RequiredMethodsRule`, `InitialStateRule`, `ComputeSignatureRule`, `DeprecatedMethodRule`. `ValidationPipeline` runs rules in sequence; rules raise `ValidationError` for critical failures, return warning strings for non-critical. `AggregateValidator` delegates to `_DEFAULT_PIPELINE`; custom pipeline injectable via `set_pipeline()` / `reset_pipeline()`.
- `decorators.py`: Six `_Mixin*` classes (`_MixinGossip`, `_MixinBroadcast`, `_MixinCollection`, `_MixinElection`, `_MixinTime`, `_MixinGeometry`) as proper OOP base classes with methods on the class body. `_apply_mixin(mixin_cls, marker, cls)` creates new class via `type(cls.__name__, (mixin_cls, cls), {...})` (dynamic subclassing). Mixin decorators delegate to `_apply_mixin`.
- `transpiler/__init__.py`: `PythonAstVisitor.visit_Lambda` translates Python lambdas to C++14 generic lambdas `[=](auto params...) { return body; }` for G&& callable parameters. Capture-by-value `[=]` is safe because FCPP calls lambdas immediately within scope.
- `python_dsl/__init__.py`: exports `Primitive`, `ValidationRule`, `ValidationPipeline`.
- Tests: `test_logging.py` (15 tests), new tests in `test_dsl.py` (primitive base, clone, callable metadata, pipeline), new tests in `test_transpiler.py` (visit_Lambda, FCPP calls with lambda args).

## Full primitive list (64 total, 3 excluded)

**basics.hpp (11)**: `nbr`, `old`, `nbr_uid`, `oldnbr`, `align`, `align_inplace`, `mod_other`, `split`, `fold_hood`, `count_hood`, `spawn`  
**utils.hpp (7)**: `min_hood`, `max_hood`, `sum_hood`, `mean_hood`, `all_hood`, `any_hood`, `list_hood`  
**spreading.hpp (6)**: `abf_distance`, `abf_hops`, `bis_distance`, `flex_distance`, `broadcast`, `bis_ksource_broadcast`  
**collection.hpp (9)**: `gossip`, `gossip_min`, `gossip_max`, `gossip_mean`, `sp_collection`, `mp_collection`, `wmp_collection`, `list_idem_collection`, `list_arith_collection`  
**geometry.hpp (12)**: `follow_target`, `follow_path`, `follow_track`, `rectangle_walk`, `random_rectangle_target`, `neighbour_elastic_force`, `neighbour_gravitational_force`, `neighbour_charged_force`, `line_elastic_force`, `plane_elastic_force`, `point_elastic_force`, `point_gravitational_force`  
**election.hpp (6)**: `diameter_election`, `diameter_election_distance`, `color_election`, `color_election_distance`, `wave_election`, `wave_election_distance`  
**time.hpp (13)**: `constant`, `constant_after`, `counter`, `delay`, `round_since`, `time_since`, `timed_decay`, `exponential_filter`, `shared_clock`, `shared_decay`, `shared_filter`, `toggle`, `toggle_filter`

**Excluded**: `spawn_deprecated` (deprecated), `color_election_internal`/`wave_election_internal` (internal).

## V1_9_PLAN — 6 steps (revised 2026-05-28)

Plan file: `development_history/V1_9_PLAN.md`

Projected total: 624 + 48 = **672 tests** after all steps complete.

| Step | Topic | Status |
|---|---|---|
| A | Transpiler completeness (frozenset→set_t, min_hood tuple→make_tuple, receiver_uid broadcast) | ✅ Done — 629 tests (+5) |
| B | Library foundations (print→logger, PhysicalNode RAII, _example_utils helper) | ✅ Done — 632 tests (+3) |
| C | OutputChannel + DeviceManager integration (5 classes, output_channel= kwarg) | ✅ Done — 647 tests (+15) |
| D | Runtime & physical (ping handler in C++ template, accept_registrations) | ✅ Done — 655 tests (+8) |
| E | AbstractExample toolchain bridge — run() invokes full pipeline (validate→transpile→compile→SwarmProcess→listen→log) | ✅ Done — 665 tests (+10) |
| F | Examples subclasses migration — remove pure-Python round_step + helpers; add aggregate_class(); log_line() uses FCPP state_data | ✅ Done — 672 tests (+7) |

**Key design decision (Steps E+F):** examples currently have two classes per file — `@aggregate_function` (C++ spec) and `AbstractExample` subclass (pure-Python sim). The pure-Python sim defeats the project purpose. After Step E, `AbstractExample.run()` transpiles and runs the `@aggregate_function` class through the full FCPP toolchain; state updates come from the C++ binary via `SwarmSnapshot`. After Step F, `round_step()` and `initial_states()` are removed from all 7 subclasses.

## Known gaps (future work)

- Multi-swarm coordination UI (DeviceManager backend done; Steps C/D address this)
- Activate ANTLR4 parser path: run `grammar/generate_antlr.py --download` (requires Java 11+)
- All items in V1_9_PLAN steps A–F above

## Key docs

- `src/fcpp_bridge/DEPLOYMENT.md` — **single consolidated history**: all phases A/B, Phase 7, test refactor, examples, v1.0–v1.3; replaces the 7 individual journals (moved to `development_history/`)
- `src/fcpp_bridge/TUTORIAL_simple.md` — beginner tutorial: hop-channel (20 nodes, BIS + nbr/min_hood + broadcast)
- `src/fcpp_bridge/TUTORIAL_in_depth.md` — production tutorial: HopChannelSimulation class, full feature reference
- `src/bridge.md` — full architecture doc (v1.3)

**Archived originals** (moved to `src/fcpp_bridge/development_history/`):
`PRIMITIVE_AUDIT.md`, `VISUALIZATION.md`, `NETWORK_REFACTOR_JOURNAL.md`,
`REFACTOR_TESTS_JOURNAL.md`, `EXAMPLES_JOURNAL.md`,
`PHYSICAL_DEPLOYMENT.md`, `PHYSICAL_DEPLOYMENT_JOURNAL.md`

## Test sub-package layout (refactored 2026-05-24, extended 2026-05-25)

All monolithic `test_<phase>.py` files split into sub-packages mirroring the source layout. 610 tests pass.

- `tests/dsl/` — 6 files: `test_aggregate_function.py`, `test_primitives.py`, `test_mixins.py`, `test_type_system.py`, `test_primitive_base.py`, `test_validation_pipeline.py`
- `tests/transpiler/` — 3 files: `test_cpp_code_builder.py`, `test_python_ast_visitor.py`, `test_transpiler_core.py`
- `tests/compiler/` — 3 files: `test_program_cache.py`, `test_compiler_core.py`, `test_compilation_result.py`
- `tests/ipc/` — 7 files: `test_data_types.py`, `test_backends.py`, `test_swarm_process.py`, `test_device_manager.py`, `test_network_listener.py`, `test_physical_node.py` (v1.2: 32 tests — PhysicalNode connect, close, auto-reconnect, neighbor join/leave, listeners, heartbeat), `test_liveness_strategy.py` (v1.3: 23 tests — all 3 strategies + _IpcNodeBase integration)
- `tests/grammar/` — 5 files: `test_tokenizer.py`, `test_ast_node.py`, `test_language_parser.py`, `test_ast_to_dsl.py`, `test_antlr_parser.py`
- `tests/metrics/` — 6 files: `test_metric_point.py`, `test_state_history.py`, `test_metrics_collector.py`, `test_metrics_summary.py`, `test_metrics_export.py`, `test_metrics_performance.py`
- `tests/visualization/` — 4 files: `test_visualizer_base.py`, `test_text_dashboard.py`, `test_swarm_visualizer.py`, `test_create_visualizer.py`
- `tests/test_logging.py` — kept flat (single cohesive component, 166 lines)

Progress journal: `src/fcpp_bridge/REFACTOR_TESTS_JOURNAL.md`

## One-file-per-class layout (refactored 2026-05-24)

All non-`__init__.py` files with multiple classes were converted to sub-packages. Each `__init__.py` re-exports all public names so existing import paths remain unchanged.

Layout:
- `python_dsl/primitives/` — 64 primitive classes + `Primitive` base (one `.py` each)
- `python_dsl/types/` — `CppType`, `_CppProxy`, `_BoundCppProxy`, 14 proxy classes, `TemplateParam`, `AggregateType`
- `python_dsl/validators/` — `ValidationError`, `ValidationRule`, 5 rule classes, `ValidationPipeline`, `AggregateValidator`
- `python_dsl/decorators/` — 6 `_Mixin*` classes + decorator functions in `__init__.py`
- `transpiler/` — `TranspilationError`, `CppCodeBuilder`, `PythonAstVisitor`, `Transpiler` (`transpiler_core.py`), `_constants.py`
- `compiler/` — 7 class files + `__init__.py`
- `ipc/` — 11 class files + `__init__.py` (`updates_listener.py`, `listener_proxy.py` added in v1.0; `liveness_strategy.py` added in v1.3)
- `grammar/` — `AstNode`, `ParserError`, `AggregateLanguageParser` + `ast_to_dsl`, `AntlrParser`
- `metrics/` — `MetricPoint`, `MetricsSummary`, `StateHistory`, `MetricsCollector` + `_default_extractor`
- `visualization/` — `VisualizerBase`, `TextDashboard`, `SwarmVisualizer` + `create_visualizer` in `__init__.py`
- `runtime/` — `RuntimeGenerator` in `runtime_generator.py`

Name collision rule: `transpiler/transpiler_core.py` and `compiler/compiler_core.py` (a module named same as its package would shadow it).

Mixin import depth: `decorators/_mixin_*.py` must use `from ..primitives import X` (two dots — up to `python_dsl/`, then into `primitives/`).

## Key bugs fixed

- `fcpp_bridge/__init__.py` and `transpiler/__init__.py`: bare `from python_dsl import` → relative/absolute imports
- `ipc/__init__.py` `GrpcBackend._connect`: `grpc.aio.secure_channel` → `grpc.insecure_channel`
- `ipc/__init__.py` `_parse_snapshot`: `n["state"]` (KeyError) → `n.get("state")`
- `compiler/__init__.py` `ProgramCache.lookup`: removed `.exists()` check (moved to `get_or_compile`)
- `python_dsl/decorators.py` `@aggregate_function`: was not calling `AggregateValidator.validate()`
- `ipc/__init__.py` `SwarmProcess`: added class-level `backend: Optional[IpcBackend] = None` for `patch.object`
- `metrics/__init__.py` `remove_callback`: `is not` → `!=` (bound-method equality)
- `log.py` `set_bridge_logging`: uses level-based silencing NOT `_root.disabled` — Python's `callHandlers` during propagation bypasses the `disabled` flag

## C++ algorithm examples

`src/fcpp_bridge/examples/` — 5 ports of real FCPP C++ algorithms + 2 original DSL-showcase examples (7 total).
All run through the full toolchain via `AbstractExample.run()` (Steps E+F complete).
Progress tracked in `src/fcpp_bridge/development_history/EXAMPLES_JOURNAL.md`.
Per-node log files written to `examples/logs/node_<id>_<name>.log`.

| File | C++ source / origin | Core primitives |
|---|---|---|
| `spreading_collection.py` | `fcpp-sample-project/lib/spreading_collection.hpp` | `abf_distance`, `mp_collection`, `broadcast` |
| `channel_broadcast.py` | `fcpp-sample-project/lib/channel_broadcast.hpp` | `bis_distance`, `broadcast` |
| `collection_compare.py` | `fcpp-sample-project/lib/collection_compare.hpp` | `sp_collection`, `mp_collection`, `wmp_collection` |
| `message_dispatch.py` | `fcpp-sample-project/lib/message_dispatch.hpp` | `bis_distance`, `sp_collection`, `spawn`, `old`, `nbr`, `min_hood` |
| `chain_decaying.py` | `fcpp-sample-project/run/chain_decaying.hpp` | `nbr`, `min_hood`, `self_uid()` |
| `worker_role_assignment.py` | **original** — v1.5–v1.7 DSL showcase | `bis_distance`, `sp_collection`, `spawn`, `old`, `nbr`, `min_hood`, `count_hood`, `self_uid()` + `RoleCommunicationType` |
| `communication_roles_assignment.py` | **original** — v1.9 DSL showcase | `bis_distance` ×2, `old` ×2, `broadcast`, `match/case`, `self_uid()`; 4 roles: SENDER/REPEATER/RECEIVER/UNASSIGNED |

`worker_role_assignment.py` specifics (v1.8.3 as of 2026-05-28):
- 26 nodes (2 × 13-slot ROLE_CYCLE); knobs: `ADDITIONAL_REPEATERS_EACH_CYCLE=5`, `FULL_ROLES_ASSIGNMENT_CYCLES_ROUNDS=2`; REPEATER-type=14 > ENDPOINT-type=10 > RECEIVER-type=2
- `WorkerRole` enum (8 roles: 0=UNASSIGNED, 1=RECEIVER, 2=LIDAR, 3=INFRARED_SENSOR, 4=REPEATER, 5=TORCHLIGHT_MICROPHONE, 6=RUBBLES_REMOVER, 7=FLYING_OVERSEER)
- `RoleCommunicationType(IntEnum)`: ENDPOINT(0), RECEIVER(1), REPEATER(2); mapped via `ROLE_COMM_TYPE` dict
- Endpoint roles (2,3,5,6,7): LIDAR, INFRARED_SENSOR, TORCHLIGHT_MICROPHONE, RUBBLES_REMOVER, FLYING_OVERSEER — inject sensor-reading messages every 10 rounds
- Repeater roles (0,4): UNASSIGNED (passive), REPEATER (active relay) — relay data, do not inject
- RECEIVER role (1): accumulates delivered messages via `old`
- `ENDPOINT_ROLES` frozenset includes role 6 (RUBBLES_REMOVER); `REPEATER_ROLES` frozenset = {0,4}; `RELAY_ROLES` removed
- Demo simulation generates random float sensor readings in message body
- `self_uid()` used in steps 2 (tie-breaker), 4 (sp_collection key), 5 (spawn key sender)
- All 7 CALL-based primitives called BEFORE the switch (CALL-counter alignment requirement)
- Design notes + 7 evolution paths in `development_history/WORKER_ROLE_ASSIGNMENT.md`

v2.0: all examples refactored — `_demo_simulate()` replaced by `AbstractExample` subclass (Template Method pattern). Dynamic node dict: `dict[int, state]` — nodes join/leave by adding/removing keys. Extra log files (receiver_messages.log, comm_receiver_messages.log) opened/closed via `on_simulation_start()`/`on_simulation_end()` hooks. `communication_roles_assignment.py` added as 7th example with `CommunicationRolesExample` subclass.

Each file: `@aggregate_function` class (transpilable) + `AbstractExample` subclass. Steps E+F complete: `run()` invokes full toolchain (`validate→transpile→compile→SwarmProcess→listen→log`); `round_step()`/`initial_states()` removed; `aggregate_class` property added; `on_round_complete(snapshot)` receives `state_data: Any` from FCPP snapshots.
Run: `PYTHONPATH=src python src/fcpp_bridge/examples/<name>.py`

**Why:** compute() call order matches C++ MAIN() exactly. nbr primitives use `# noqa: F821` (unbound in Python — transpiler recognizes by name, not by binding).

## Added examples (FE-9/10/11, added 2026-05-29)

 includes these three advanced examples alongside the core 7.

`examples/ex_utils/` shared utilities:
- `position.py` — `Positions = Dict[int, Tuple[float, ...]]`; `rnd_in_area(n, area, *, seed)` (uniform random, any even-len area tuple); `grid_in_area(n, area, *, row_major=True)` (regular 2-D grid)
- `storage.py` — `NodeStorage = Dict[int, Dict[str, Any]]`; `rnd_vec`, `rnd_vec_variable`, `set_rnd_vec`, `set_rnd_vec_variable`, `spread_data_coprime_ID` (coprime-filtered neighbor IDs), `spread_data_coprime_ID_pos` (coprime-filtered {id: position} map — seed for scattered_database)
- `tiles.py` — `grid_tile_centers(area, cell_size)`, `nearest_tile_center(pos, tile_centers)`, `compute_tile_shapes(tile_centers, area, cell_size)`, `clip_rect_to_rect`, `clip_polygon_to_polygon` (Sutherland-Hodgman)
- `__init__.py` re-exports all public symbols

Import: `from fcpp_bridge.examples.ex_utils import rnd_in_area, spread_data_coprime_ID, ...`

Coprime edge case: `gcd(0, j) = j`, so node 0 is only coprime with node 1.

### Advanced examples (FE-9 → FE-11)

Detailed plan: `development_history/EXAMPLES_PLAN.md`; index entries in `FUTURE_EXERCISES.md`.

| Exercise | File | Builds on | Key DSL |
|----------|------|-----------|---------|
| FE-9 `scattered_database` | `examples/scattered_database.py` | `spread_data_coprime_ID_pos` | `spawn`, `old`, `bis_distance`, `broadcast` |
| FE-10 `area_discovery` | `examples/area_discovery.py` | FE-9 + `tiles.py` | `nbr`, `fold_hood` |
| FE-11 `iteratively_area_discovery` | `examples/iteratively_area_discovery.py` | FE-10 | `spawn`, `old`, `nbr`, `min_hood`, `follow_target`; second `assignment_db` via 1-hop spawn |

Design decisions recorded in `EXAMPLES_PLAN.md §Open Design Questions`:
- FE-9 response routing: reverse `spawn` (primary) vs `bis_distance` + `channel_broadcast` (variant)
- FE-11 diameter: fixed constant first, live `max_hood(bis_distance(...)) + broadcast` as extension
- FE-11 anti-double-assignment: second `assignment_db` + 1-hop spawn (NOT `first_ever_tile` + `nbr`); election on timeout (min-distance via `nbr` + `min_hood`)
- `self_pos()` not a DSL primitive; node movement left as Python-side in examples fallback
- Version B (non-rectangular area) uses `clip_polygon_to_polygon`; non-convex areas need polygon decomposition

## Platform-conditional LLD

`compiler/__init__.py` `Compiler.compile()` adds `-fuse-ld=lld` only when:
- `platform.system() == "Windows"` (always — BFD crashes on fcpp COMDAT tables), or
- `platform.system() == "Linux"` and `shutil.which("lld") is not None`
- macOS: omitted (Apple ld64 does not support `-fuse-ld=lld`)

See [[project-build-cross-platform]] for cross-platform build patterns.
