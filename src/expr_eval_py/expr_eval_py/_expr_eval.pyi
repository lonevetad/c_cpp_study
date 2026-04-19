"""Type stubs for expr_eval_py — consumed by type checkers (mypy, pyright)."""

from __future__ import annotations

class ParseError(ValueError):
    """Raised when the expression string is syntactically invalid."""
    ...

class EvaluationError(RuntimeError):
    """Raised when evaluation fails (type mismatch, unknown variable, etc.)."""
    ...

def evaluate(
    expression: str,
    variables: dict[str, str] | None = ...,
    *,
    verbose: bool = ...,
) -> bool:
    """Evaluate a boolean expression string.

    Parameters
    ----------
    expression:
        The boolean expression to evaluate.
    variables:
        Mapping of variable name → string value.
    verbose:
        Print parsed AST to stdout if True.

    Returns
    -------
    bool

    Raises
    ------
    ParseError
    EvaluationError
    """
    ...

def version() -> str:
    """Return the native library version string."""
    ...
