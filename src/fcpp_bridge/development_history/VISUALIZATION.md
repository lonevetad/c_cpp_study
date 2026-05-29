# FCPP Bridge — Phase 7: Visualization & ANTLR Generation

## Overview

Phase 7 adds two capabilities to fcpp_bridge:

| Item                 | What                                                           | Where                       |
| -------------------- | -------------------------------------------------------------- | --------------------------- |
| ANTLR generation     | Script to compile `AggregateProgram.g4` → Python3 parser stubs | `grammar/generate_antlr.py` |
| Visualization plugin | Live / replay GUI for swarm output data                        | `visualization/__init__.py` |

---

## Part 1 — ANTLR Code Generation

### Background

`grammar/AggregateProgram.g4` describes the full FCPP aggregate DSL grammar.  
`fcpp_bridge.grammar.AntlrParser` already has dual-path dispatch:

| State                                                 | Parser used                                               |
| ----------------------------------------------------- | --------------------------------------------------------- |
| `__antlr_gen/` missing **or** `antlr4` runtime absent | Hand-written `AggregateLanguageParser` (Phase 5 fallback) |
| Both present                                          | ANTLR4-backed `AggregateProgramParser` (correct path)     |

Generating the stubs and installing the runtime activates the ANTLR path automatically, with full error recovery and line:column diagnostics.

### Prerequisites

| Tool                        | Version | How to get                                              |
| --------------------------- | ------- | ------------------------------------------------------- |
| Java                        | 11+     | `sudo apt install default-jdk` / `brew install openjdk` |
| `antlr4-python3-runtime`    | 4.13.1  | `pip install antlr4-python3-runtime==4.13.1`            |
| `antlr-4.13.1-complete.jar` | 4.13.1  | `python3 generate_antlr.py --download`                  |

### Generating the stubs

```bash
cd src/fcpp_bridge/grammar

# Download the ANTLR jar (first time only) and generate stubs
python3 generate_antlr.py --download

# Install the Python runtime in the project venv
../../expr_eval_py/expr_eval_py_env/bin/pip install -r requirements_antlr.txt
```

Generated output in `__antlr_gen/`:

```
__antlr_gen/
├── __init__.py
├── AggregateProgramLexer.py
├── AggregateProgramParser.py
├── AggregateProgramListener.py
└── AggregateProgramVisitor.py
```

> `__antlr_gen/` is git-ignored. Re-run `generate_antlr.py` after any grammar change.

### Verifying the integration

```python
from fcpp_bridge.grammar import AntlrParser
p = AntlrParser()
print(p._antlr_available)   # True when stubs + runtime are both present

prog = """
def gossip_avg:
    initial_state: 1.0
    compute(self_state, neighbors): gossip(self_state)
"""
ast = p.parse_string(prog)
print(ast)  # AstNode(node_type='program', ...)
```

### generate_antlr.py flags

```
python3 generate_antlr.py [--download] [--antlr-jar PATH] [--output-dir DIR]

  --download         Fetch the ANTLR jar if not present at --antlr-jar
  --antlr-jar PATH   Path to antlr-4.13.1-complete.jar (default: grammar/)
  --output-dir DIR   Where to write generated stubs (default: grammar/__antlr_gen/)
```

### What changes when ANTLR is active

- `AntlrParser._antlr_available` returns `True`
- Parsing delegates to `_parse_with_antlr()` — full ANTLR4 error recovery
- Syntax errors include `line:column` from the grammar specification
- Listener and Visitor interfaces (`AggregateProgramListener`, `AggregateProgramVisitor`) become available for downstream tooling

---

## Part 2 — Visualization Plugin

### Module: `fcpp_bridge.visualization`

```
visualization/
└── __init__.py    VisualizerBase, TextDashboard, SwarmVisualizer, create_visualizer
```

### Data flow

```
C++ compiled swarm
    ↓ SwarmSnapshot (via IPC: Unix socket / HTTP / gRPC)
SwarmProcess.get_state()  /  DeviceManager.get_all_states()
    ↓
MetricsCollector.record(snapshot)
    ↓ on_update callback
Visualizer.update(snapshot)
    ↓
Live chart (SwarmVisualizer)  /  terminal output (TextDashboard)
```

The visualization plugin is a **passive consumer** — it reads data from the same `SwarmSnapshot` stream that `MetricsCollector` processes. Attaching a visualizer adds a lightweight callback and does not affect the IPC pipeline.

### Class summary

#### `VisualizerBase` (ABC)

| Method                           | Description                                                |
| -------------------------------- | ---------------------------------------------------------- |
| `update(snapshot)`               | Process one snapshot (abstract)                            |
| `start()`                        | Open the display                                           |
| `stop()`                         | Close and clean up                                         |
| `attach(collector)`              | Register `self.update` with `MetricsCollector.on_update()` |
| `detach(collector)`              | Unregister the callback                                    |
| `replay_from_history(collector)` | Feed all recorded snapshots through `update()`             |

#### `TextDashboard`

Terminal output — no external dependencies.

```python
from fcpp_bridge.visualization import TextDashboard

dash = TextDashboard()
dash.start()
dash.attach(collector)       # live mode
# ... later ...
dash.stop()

# or post-hoc:
dash.replay_from_history(collector)
```

Sample output:

```
=== FCPP Swarm Monitor (text) ===
round=     0  nodes=   100  mean=    1.5000  min=    0.0000  max=    3.0000
round=     1  nodes=   100  mean=    1.8500  min=    0.0000  max=    4.2000
=== Stopped after 2 rounds ===
```

#### `SwarmVisualizer`

Live matplotlib visualization (requires `pip install matplotlib`).

Two subplots update as data arrives:

- **Swarm size** — node count per round
- **Node state statistics** — mean line with min-max shaded band

```python
from fcpp_bridge.visualization import SwarmVisualizer

viz = SwarmVisualizer(title="My Swarm", max_rounds=200)
viz.start()           # non-blocking matplotlib window
viz.attach(collector) # figure refreshes on each new snapshot

import matplotlib.pyplot as plt
plt.show(block=True)  # block to keep window open until user closes it
```

Post-hoc replay from recorded history (blocking):

```python
viz = SwarmVisualizer()
viz.replay_from_history(collector)
```

Read accumulated data without opening a window (useful for testing):

```python
data = viz.get_data()
# {'rounds': [...], 'node_counts': [...], 'means': [...], 'mins': [...], 'maxs': [...]}
```

#### `create_visualizer` factory

Picks the best available implementation automatically.

```python
from fcpp_bridge.visualization import create_visualizer

# Tries SwarmVisualizer; falls back to TextDashboard if matplotlib absent
viz = create_visualizer(collector=collector, prefer_gui=True)
viz.start()
```

| Parameter            | Default                | Description                                           |
| -------------------- | ---------------------- | ----------------------------------------------------- |
| `collector`          | `None`                 | If given, calls `viz.attach(collector)` automatically |
| `prefer_gui`         | `True`                 | Try matplotlib first                                  |
| `title`              | `"FCPP Swarm Monitor"` | Window title (SwarmVisualizer)                        |
| `max_rounds`         | `500`                  | Rolling window size (SwarmVisualizer)                 |
| `update_interval_ms` | `100`                  | Animation refresh rate ms (SwarmVisualizer)           |
| `stream`             | `stdout`               | Output stream (TextDashboard)                         |

### Minimal end-to-end example

```python
from fcpp_bridge.ipc import SwarmSnapshot, NodeState
from fcpp_bridge.metrics import MetricsCollector
from fcpp_bridge.visualization import create_visualizer

collector = MetricsCollector()
viz = create_visualizer(collector=collector)   # auto-attaches
viz.start()

# In production this loop is driven by SwarmProcess / DeviceManager:
for rnd in range(50):
    nodes = [NodeState(i, float(i % 10), rnd * 0.1) for i in range(100)]
    collector.record(SwarmSnapshot(rnd, rnd * 0.1, nodes))

viz.stop()
```

### Optional dependency

`SwarmVisualizer` is only imported on construction, so the module loads cleanly even without matplotlib installed. `create_visualizer` and `TextDashboard` never require it.

```bash
pip install matplotlib      # optional; enables SwarmVisualizer
```

---

## Test coverage

Tests are in `tests/test_visualization.py` (16 tests, no matplotlib required for most).

| Test group             | What is covered                                                        |
| ---------------------- | ---------------------------------------------------------------------- |
| Abstract base          | `VisualizerBase` cannot be instantiated                                |
| attach / detach        | Collector callbacks are registered and removed correctly               |
| `TextDashboard`        | start/stop output, numeric/non-numeric formatting, round count, replay |
| `SwarmVisualizer` data | Accumulation, max_rounds trimming, empty snapshot, non-numeric state   |
| Dirty flag             | Set on update, cleared by `_animate`                                   |
| `create_visualizer`    | Text fallback, matplotlib fallback, collector attachment               |

Run:

```bash
pytest src/fcpp_bridge/tests/test_visualization.py -v  # after pip install -e . (or prefix PYTHONPATH=src)
```

---

## Files added / changed in Phase 7

| File                             | Change                                   |
| -------------------------------- | ---------------------------------------- |
| `visualization/__init__.py`      | New — full visualization plugin          |
| `tests/test_visualization.py`    | New — 16 tests                           |
| `grammar/generate_antlr.py`      | New — ANTLR stub generation script       |
| `grammar/requirements_antlr.txt` | New — `antlr4-python3-runtime==4.13.1`   |
| `.gitignore`                     | Added `grammar/__antlr_gen/`             |
| `README.md`                      | Added Phase 7, updated test count to 395 |
| `bridge.md`                      | Added Phase 7 section                    |
| `VISUALIZATION.md`               | This file                                |
