"""Base Primitive class for all FCPP DSL primitives."""

import copy
from typing import Any


_MISSING = object()  # sentinel for missing attributes in __eq__


class Primitive:
    """Base class for all FCPP DSL primitives.

    Provides a shared interface for introspection, default equality/hashing,
    and the *Prototype* design-pattern methods :meth:`clone` and
    :meth:`clone_with`.

    Class attributes (override in subclasses as needed)
    ---------------------------------------------------
    has_callable_args : bool
        ``True`` when one or more constructor arguments are callables (C++
        ``G&&`` forwarding-reference parameters).
    callable_arg_positions : tuple[int, ...]
        Zero-based indices of constructor parameters that are callables.
        Documented so the transpiler can emit the correct C++ lambda syntax.
    """

    has_callable_args: bool = False
    callable_arg_positions: tuple = ()

    # ------------------------------------------------------------------
    # Default __repr__: ClassName(attr=value, …)
    # Subclasses that define their own __repr__ take precedence via MRO.
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        attrs = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
        if not attrs:
            return f"{type(self).__name__}()"
        parts = ", ".join(
            f"{k}=<callable>" if callable(v) else f"{k}={v!r}"
            for k, v in attrs.items()
        )
        return f"{type(self).__name__}({parts})"

    # ------------------------------------------------------------------
    # Default __eq__: compare type + all instance attrs; callables by identity.
    # ------------------------------------------------------------------
    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        for k, self_v in self.__dict__.items():
            other_v = getattr(other, k, _MISSING)
            if other_v is _MISSING:
                return False
            if callable(self_v) or callable(other_v):
                if self_v is not other_v:
                    return False
            elif self_v != other_v:
                return False
        return True

    def __hash__(self) -> int:
        return hash(type(self).__name__)

    # ------------------------------------------------------------------
    # Prototype pattern
    # ------------------------------------------------------------------
    def clone(self) -> "Primitive":
        """Return a shallow copy of this primitive (Prototype pattern)."""
        return copy.copy(self)

    def clone_with(self, **changes: Any) -> "Primitive":
        """Return a shallow copy with selected attributes overridden.

        Raises ``AttributeError`` if a key in *changes* does not correspond
        to an existing instance attribute.
        """
        obj = copy.copy(self)
        for key, value in changes.items():
            if not hasattr(obj, key):
                raise AttributeError(
                    f"{type(self).__name__!r} has no attribute {key!r}")
            setattr(obj, key, value)
        return obj
