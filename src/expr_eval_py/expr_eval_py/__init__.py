"""
expr_eval_py — Python bindings for the ExprEval C++26 boolean expression evaluator.

The evaluator supports these operators:
  ==  !=  <  <=  >  >=   (comparison)
  &&  ||  !               (logical)
  -                       (unary numeric negation)
  ( )                     (grouping)

Variable values are strings parsed as ``bool`` ("true"/"false") or ``float``.

Example
-------
>>> from expr_eval_py import evaluate
>>> evaluate("v1 > 10 && v2 == true", {"v1": "15.5", "v2": "true"})
True
>>> evaluate("x != y", {"x": "1", "y": "2"})
True
"""

from __future__ import annotations

import ctypes
import os
import pathlib
import sys

# ── locate and load the shared library ───────────────────────────────────────

_suffix = (
    ".dll"    if sys.platform == "win32"  else
    ".dylib"  if sys.platform == "darwin" else
    ".so"
)
_lib_path = pathlib.Path(__file__).parent / f"_expr_eval_core{_suffix}"

if not _lib_path.exists():
    raise ImportError(
        f"Native library not found: {_lib_path}\n"
        "Run  mingw32-make all  from the expr_eval_py/ directory to build it."
    )

# On Windows, register the package directory as a DLL search path so that
# libwinpthread-1.dll (copied there by the Makefile) is found automatically
# when ctypes loads the main DLL.
if sys.platform == "win32":
    os.add_dll_directory(str(_lib_path.parent))

_lib = ctypes.CDLL(str(_lib_path))

# ── declare C function signatures ─────────────────────────────────────────────
# Must match bridge/bridge.cpp exactly.

_lib.expr_eval_evaluate.restype  = ctypes.c_int32
_lib.expr_eval_evaluate.argtypes = [
    ctypes.c_char_p,                        # expression
    ctypes.POINTER(ctypes.c_char_p),        # var_keys
    ctypes.POINTER(ctypes.c_char_p),        # var_values
    ctypes.c_int32,                         # var_count
    ctypes.c_int32,                         # verbose
    ctypes.POINTER(ctypes.c_int32),         # result_out
    ctypes.c_char_p,                        # error_buf
    ctypes.c_int32,                         # error_buf_size
]

_lib.expr_eval_version.restype  = ctypes.c_char_p
_lib.expr_eval_version.argtypes = []

# ── error codes (mirror bridge.cpp constants) ─────────────────────────────────
_EXPR_OK             = 0
_EXPR_ERR_PARSE      = 1
_EXPR_ERR_EVALUATION = 2
_EXPR_ERR_INTERNAL   = 3
_ERROR_BUF_SIZE      = 2048

# ── public exception types ────────────────────────────────────────────────────

class ParseError(ValueError):
    """Raised when the expression string is syntactically invalid."""

class EvaluationError(RuntimeError):
    """Raised when evaluation fails (type mismatch, unknown variable, etc.)."""

# ── public API ────────────────────────────────────────────────────────────────

def evaluate(
    expression: str,
    variables: dict[str, str] | None = None,
    *,
    verbose: bool = False,
) -> bool:
    """Evaluate a boolean expression string.

    Parameters
    ----------
    expression:
        The boolean expression to evaluate.
    variables:
        Mapping of variable name → string value.  Values are parsed as
        ``bool`` ("true"/"false") or ``float``.  Defaults to empty.
    verbose:
        If ``True``, print the parsed AST to stdout (useful for debugging).
        Defaults to ``False``.

    Returns
    -------
    bool
        The result of the expression.

    Raises
    ------
    ParseError
        If the expression is syntactically invalid.
    EvaluationError
        If a type mismatch, unknown variable, or non-boolean root occurs.
    """
    vars_dict = variables or {}
    n = len(vars_dict)

    # Build ctypes arrays for keys and values.
    c_keys   = (ctypes.c_char_p * n)(*(k.encode() for k in vars_dict))
    c_values = (ctypes.c_char_p * n)(*(v.encode() for v in vars_dict.values()))

    result_out = ctypes.c_int32(0)
    error_buf  = ctypes.create_string_buffer(_ERROR_BUF_SIZE)

    ret = _lib.expr_eval_evaluate(
        expression.encode(),
        c_keys,
        c_values,
        ctypes.c_int32(n),
        ctypes.c_int32(1 if verbose else 0),
        ctypes.byref(result_out),
        error_buf,
        ctypes.c_int32(_ERROR_BUF_SIZE),
    )

    if ret == _EXPR_OK:
        return bool(result_out.value)

    msg = error_buf.value.decode(errors="replace")
    if ret == _EXPR_ERR_PARSE:
        raise ParseError(msg)
    if ret == _EXPR_ERR_EVALUATION:
        raise EvaluationError(msg)
    raise RuntimeError(f"Internal C++ error: {msg}")


def version() -> str:
    """Return the native library version string."""
    return _lib.expr_eval_version().decode()


__all__ = ["evaluate", "version", "ParseError", "EvaluationError"]
