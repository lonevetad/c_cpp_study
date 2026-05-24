"""_CppProxy and _BoundCppProxy — internal proxy classes for C++ type annotations."""

from __future__ import annotations
from typing import Any


class _CppProxy:
    """Base for all Python <-> C++ type proxy annotations.

    Subclass it with ``cpp_template``, ``cpp_std``, and ``required_includes``
    keyword arguments.  ``__init_subclass__`` will assign them as class-level
    constants so that ``AggregateType`` can read them back via the class object.
    """

    # Populated by __init_subclass__ in every concrete subclass.
    _cpp_template: str
    _cpp_std: str | None
    _required_includes: list[str]

    def __init_subclass__(
        cls,
        cpp_template: str = "",
        cpp_std: str | None = None,
        required_includes: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init_subclass__(**kwargs)
        cls._cpp_template = cpp_template
        cls._cpp_std = cpp_std
        # Defensive copy so each subclass owns its own list.
        cls._required_includes = list(required_includes) if required_includes is not None else []

    @classmethod
    def __class_getitem__(cls, args: Any) -> "_BoundCppProxy":
        if cls is _CppProxy:
            raise TypeError("_CppProxy is internal — use CppVector, CppSet, etc.")
        if not isinstance(args, tuple):
            args = (args,)
        return _BoundCppProxy(cls, args)


class _BoundCppProxy:
    """A proxy type bound to specific type arguments at subscription time.

    Produced by ``CppArray[float, 3]``, ``CppSet[int]``, etc.
    ``AggregateType.infer`` reads ``_proxy_cls`` and ``_args`` to build
    the corresponding ``CppType``.
    """

    def __init__(self, proxy_cls: type, args: tuple) -> None:
        self._proxy_cls: type = proxy_cls
        self._args: tuple = args

    def __repr__(self) -> str:
        args_str = ", ".join(repr(a) for a in self._args)
        return f"{self._proxy_cls.__name__}[{args_str}]"
