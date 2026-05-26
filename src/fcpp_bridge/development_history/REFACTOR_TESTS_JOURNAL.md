# fcpp_bridge — Test Suite Refactoring Journal

**Goal**: Mirror the one-file-per-class source layout in the test suite.  
Each monolithic `test_<phase>.py` becomes a sub-package with one file per component.

**Run tests**: `PYTHONPATH=src src/expr_eval_py/expr_eval_py_env/bin/pytest src/fcpp_bridge/tests/ -v`  
**Baseline**: 482 tests (at time of this refactor).
**Current total**: 578 tests — 578 pass, 0 fail
(+38 v1.0, +3 v1.1, +32 PhysicalNode v1.2, +8 DeviceManager v1.2, +23 liveness strategies v1.3).

---

## Status

| Sub-package             | Old file                | Lines | New files (target) | Status  |
| ----------------------- | ----------------------- | ----- | ------------------ | ------- |
| (misc)                  | `core.py` (stale)       | 2     | DELETE             | ✅ Done |
| `tests/test_logging.py` | (keep as-is)            | 166   | unchanged          | ✅ Done |
| `tests/visualization/`  | `test_visualization.py` | 256   | 4 files            | ✅ Done |
| `tests/compiler/`       | `test_compiler.py`      | 266   | 3 files            | ✅ Done |
| `tests/metrics/`        | `test_metrics.py`       | 397   | 6 files            | ✅ Done |
| `tests/ipc/`            | `test_ipc.py`           | 545   | 4 files            | ✅ Done |
| `tests/grammar/`        | `test_parser.py`        | 677   | 5 files            | ✅ Done |
| `tests/transpiler/`     | `test_transpiler.py`    | 1107  | 3 files            | ✅ Done |
| `tests/dsl/`            | `test_dsl.py`           | 1578  | 6 files            | ✅ Done |

---

## Rules

- Old monolithic file **deleted** after its sub-package is verified passing.
- Sub-packages have `__init__.py` (pytest needs it when parent has one).
- No new `conftest.py` needed in sub-packages — pytest inherits `tests/conftest.py`.
- Mid-file inline imports (used only in their section) become top-of-file imports in the split file.
- `test_logging.py` kept flat — 166 lines, single cohesive component.

---

## Target layout

```
tests/
├── conftest.py              (unchanged)
├── __init__.py              (unchanged)
├── test_logging.py          (unchanged)
├── visualization/
│   ├── __init__.py
│   ├── test_visualizer_base.py
│   ├── test_text_dashboard.py
│   ├── test_swarm_visualizer.py
│   └── test_create_visualizer.py
├── compiler/
│   ├── __init__.py
│   ├── test_program_cache.py
│   ├── test_compiler_core.py
│   └── test_compilation_result.py
├── metrics/
│   ├── __init__.py
│   ├── test_metric_point.py
│   ├── test_state_history.py
│   ├── test_metrics_collector.py
│   ├── test_metrics_summary.py
│   ├── test_metrics_export.py
│   └── test_metrics_performance.py
├── ipc/
│   ├── __init__.py
│   ├── test_data_types.py
│   ├── test_backends.py
│   ├── test_swarm_process.py
│   └── test_device_manager.py
├── grammar/
│   ├── __init__.py
│   ├── test_tokenizer.py
│   ├── test_ast_node.py
│   ├── test_language_parser.py
│   ├── test_ast_to_dsl.py
│   └── test_antlr_parser.py
├── transpiler/
│   ├── __init__.py
│   ├── test_cpp_code_builder.py
│   ├── test_python_ast_visitor.py
│   └── test_transpiler_core.py
└── dsl/
    ├── __init__.py
    ├── test_aggregate_function.py
    ├── test_primitives.py
    ├── test_mixins.py
    ├── test_type_system.py
    ├── test_primitive_base.py
    └── test_validation_pipeline.py
```

---

## Detailed split plan

### tests/visualization/ (test_visualization.py, 256 lines)

| File                        | Sections                                  | Tests |
| --------------------------- | ----------------------------------------- | ----- |
| `test_visualizer_base.py`   | Test 1 (abstract), Test 2 (attach/detach) | 3     |
| `test_text_dashboard.py`    | Test 3                                    | 5     |
| `test_swarm_visualizer.py`  | Tests 4-6                                 | 7     |
| `test_create_visualizer.py` | Test 7                                    | 4     |

### tests/compiler/ (test_compiler.py, 266 lines)

| File                         | Sections                           | Tests |
| ---------------------------- | ---------------------------------- | ----- |
| `test_program_cache.py`      | Tests 1, 4, 5 (cache)              | 6     |
| `test_compiler_core.py`      | Tests 2, 3 (compiler init/compile) | 7     |
| `test_compilation_result.py` | Test 5 (CompilationResult)         | 2     |

### tests/metrics/ (test_metrics.py, 397 lines)

| File                          | Sections                                 | Tests |
| ----------------------------- | ---------------------------------------- | ----- |
| `test_metric_point.py`        | MetricPoint creation                     | 2     |
| `test_state_history.py`       | StateHistory                             | 9     |
| `test_metrics_collector.py`   | Collector basics + callbacks + extractor | 9     |
| `test_metrics_summary.py`     | MetricsSummary                           | 6     |
| `test_metrics_export.py`      | export_json / export_csv                 | 3     |
| `test_metrics_performance.py` | Large-scale tests                        | 3     |

### tests/ipc/ (test_ipc.py, 545 lines)

| File                     | Sections                                  | Tests |
| ------------------------ | ----------------------------------------- | ----- |
| `test_data_types.py`     | NodeState, SwarmSnapshot                  | 8     |
| `test_backends.py`       | UnixSocketBackend, HttpBackend init/parse | 15    |
| `test_swarm_process.py`  | SwarmProcess lifecycle                    | 17    |
| `test_device_manager.py` | DeviceManager                             | rest  |

### tests/grammar/ (test_parser.py, 677 lines)

| File                      | Sections                           | Tests |
| ------------------------- | ---------------------------------- | ----- |
| `test_tokenizer.py`       | Tokenizer tests (sections 1, 7, 8) | 8     |
| `test_ast_node.py`        | AstNode (section 3)                | 2     |
| `test_language_parser.py` | Parser/atoms (sections 2, 4, 5, 6) | 10    |
| `test_ast_to_dsl.py`      | ast_to_dsl (sections 5b, 6b)       | 7     |
| `test_antlr_parser.py`    | AntlrParser (section 7)            | 9     |

### tests/transpiler/ (test_transpiler.py, 1107 lines)

| File                         | Sections                               | Tests |
| ---------------------------- | -------------------------------------- | ----- |
| `test_cpp_code_builder.py`   | CppCodeBuilder (sections 1, 6)         | 7     |
| `test_python_ast_visitor.py` | PythonAstVisitor (sections 3, 5, 6, 7) | 40+   |
| `test_transpiler_core.py`    | Transpiler (sections 2, 4, 8)          | 27+   |

### tests/dsl/ (test_dsl.py, 1578 lines)

| File                          | Sections                                           | Tests |
| ----------------------------- | -------------------------------------------------- | ----- |
| `test_aggregate_function.py`  | Tests 1-6 (basic DSL, validation)                  | 10    |
| `test_primitives.py`          | Tests 7, 9, 11-17 (all FCPP primitives)            | 60+   |
| `test_mixins.py`              | Tests 10, 18 (mixins)                              | 12+   |
| `test_type_system.py`         | Test 8 + Test 11-ext (type inference, C++ proxies) | 40+   |
| `test_primitive_base.py`      | v0.9 Primitive base / Prototype                    | 20+   |
| `test_validation_pipeline.py` | v0.9 ValidationRule / ValidationPipeline           | 10+   |

---

## Resume instructions

If the session was interrupted, check the **Status** table above, find the first ⬜ Pending row, and continue from there.  
Always run the full test suite after each sub-package is complete before moving to the next.

Command to run only a specific sub-package (example):

```bash
PYTHONPATH=src src/expr_eval_py/expr_eval_py_env/bin/pytest src/fcpp_bridge/tests/visualization/ -v
```
