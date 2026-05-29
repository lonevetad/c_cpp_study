---
name: feedback-fcpp-bridge-imports
description: "When creating new Python sub-modules inside fcpp_bridge, use relative or absolute package imports — never bare module names"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e0e1ffd8-f841-4b03-8663-5d988f484735
---

Always use relative (`from .python_dsl import X`) or fully qualified (`from fcpp_bridge.python_dsl import X`) imports inside `fcpp_bridge/` sub-packages. Bare names like `from python_dsl import X` silently break when the package is imported from outside its directory.

**Why:** Hit this in both `fcpp_bridge/__init__.py` and `transpiler/__init__.py` — both used bare `from python_dsl import` and `from transpiler import`, causing `ModuleNotFoundError` whenever pytest loaded them with `PYTHONPATH=src`.

**How to apply:** Any time a new `.py` file is added inside `fcpp_bridge/`, check its imports immediately. If it references a sibling package by bare name, convert to relative import.
