"""Shared utilities for fcpp_bridge example scripts.

All example ``main()`` functions perform the same boilerplate steps:
  1. Validate the aggregate class and report warnings.
  2. Transpile to C++ and report the generated size.

These helpers centralise that repeated code so each example stays concise.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Type


def report_validation(
    cls: Type,
    indent: str = "    ",
    logger: Optional[logging.Logger] = None,
) -> List[str]:
    """Validate *cls*, print/log the result, return the warning list.

    Prints to stdout when *logger* is ``None`` (default); routes through the
    given logger otherwise.  Raises the validator's exception on failure —
    callers should not swallow it.

    Parameters
    ----------
    cls:
        The ``@aggregate_function`` class to validate.
    indent:
        Leading whitespace for status lines.
    logger:
        Optional logger to use instead of ``print``.

    Returns
    -------
    list[str]
        The list of non-fatal warning strings (may be empty).
    """
    from fcpp_bridge.python_dsl.validators import AggregateValidator

    warnings = AggregateValidator.validate(cls)
    ok_msg = f"{indent}OK — {len(warnings)} warning(s)"
    if logger is not None:
        logger.info(ok_msg)
        for w in warnings:
            logger.warning("%s  %s", indent, w)
    else:
        print(ok_msg)
        for w in warnings:
            print(f"{indent}  {w}")
    return warnings


def report_transpilation(
    cls: Type,
    indent: str = "    ",
    logger: Optional[logging.Logger] = None,
) -> Optional[str]:
    """Transpile *cls* to C++, print/log the result, return the C++ string.

    Returns ``None`` on failure (error is printed/logged but not re-raised).

    Parameters
    ----------
    cls:
        The ``@aggregate_function`` class to transpile.
    indent:
        Leading whitespace for status lines.
    logger:
        Optional logger to use instead of ``print``.
    """
    try:
        from fcpp_bridge.transpiler import Transpiler
    except ImportError:
        msg = f"{indent}(transpiler not available in this environment)"
        if logger:
            logger.warning(msg)
        else:
            print(msg)
        return None

    try:
        t = Transpiler(cls)
        cpp = t.generate()
        ok_msg = (
            f"{indent}OK — {len(cpp)} bytes of C++ generated"
            f"  (state type: {t.get_state_type_cpp().name})"
        )
        if logger:
            logger.info(ok_msg)
        else:
            print(ok_msg)
        return cpp
    except Exception as exc:
        err_msg = f"{indent}FAIL: {exc}"
        if logger:
            logger.error(err_msg)
        else:
            print(err_msg)
        return None
