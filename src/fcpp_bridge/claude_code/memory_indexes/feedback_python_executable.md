---
name: feedback-python-executable
description: "Python interpreter is /usr/bin/python3; pip install -e . preferred over PYTHONPATH=src; venv pytest for tests"
metadata:
  node_type: memory
  type: feedback
  originSessionId: bugfix/fcpp_bridge/it1
---

The user's canonical Python interpreter is `/usr/bin/python3`.
Do NOT use `src/expr_eval_py/expr_eval_py_env/bin/python` for Python invocations.

**Why:** User explicitly corrected on 2026-05-28: "the real Python executable/interpreter's
location is `/usr/bin/python3`. Update this reference for ALL future invocations of Python".

**`pip install -e .` preferred over `PYTHONPATH=src`** (added 2026-05-29):
A `pyproject.toml` now exists at the repo root. Running `pip install -e .` once inside the
venv (or a new `.venv`) makes `import fcpp_bridge` available without any prefix.

**How to apply:**
- Preferred (after one-time install): `python -m fcpp_bridge.examples.foo` — no prefix needed.
- Quick imports: `python -c "import fcpp_bridge; ..."`
- Fallback (no install): `PYTHONPATH=src /usr/bin/python3 -m fcpp_bridge.examples.foo`
- System Python is PEP 668-blocked for pip; use a venv: `python -m venv .venv && source .venv/bin/activate && pip install -e .`
- Pytest: use the venv pytest binary directly — `src/expr_eval_py/expr_eval_py_env/bin/pytest src/fcpp_bridge/tests/ -q`
  (no PYTHONPATH prefix needed after install; still required without install).
