"""Type system for code generation — Python types map to C++ types."""

from __future__ import annotations

import types as _builtins_types
from typing import Any, TypeVar, Union, get_args, get_origin


# ===========================================================================
# CppType — C++ type descriptor
# ===========================================================================

class CppType:
    """Immutable descriptor for a C++ type produced by AggregateType.infer().

    Constructor parameters
    ----------------------
    name : str
        The C++ type expression (e.g. ``"double"``, ``"std::set<int>"``, ``"MyState"``).
    is_primitive : bool
        True for built-in scalar types (int, double, bool, …).
    is_struct : bool
        True when *name* refers to a user-defined struct; *fields* must be set.
    is_template : bool
        True when *name* is an unresolved template parameter (``typename T``).
    fields : dict[str, CppType] | None
        Member map for struct types.
    cpp_std : str | None
        Minimum C++ standard required (``"c++17"``, ``"c++20"``, ``"c++23"``).
    required_includes : list[str] | None
        Extra ``#include`` headers the transpiler must emit for this type.
        The constructor stores a defensive copy so callers cannot accidentally
        mutate the internal list.
    """

    def __init__(
        self,
        name: str,
        *,
        is_primitive: bool = True,
        is_struct: bool = False,
        is_template: bool = False,
        fields: dict[str, "CppType"] | None = None,
        cpp_std: str | None = None,
        required_includes: list[str] | None = None,
    ) -> None:
        self.name: str = name
        self.is_primitive: bool = is_primitive
        self.is_struct: bool = is_struct
        self.is_template: bool = is_template
        self.fields: dict[str, CppType] | None = fields
        self.cpp_std: str | None = cpp_std
        # Defensive copy — callers must not be able to mutate our list from outside.
        self.required_includes: list[str] | None = (
            list(required_includes) if required_includes is not None else None
        )

    def __repr__(self) -> str:
        parts: list[str] = [f"CppType({self.name!r}"]
        if not self.is_primitive:
            parts.append(f", is_primitive={self.is_primitive!r}")
        if self.is_struct:
            parts.append(f", is_struct={self.is_struct!r}")
        if self.is_template:
            parts.append(f", is_template={self.is_template!r}")
        if self.cpp_std is not None:
            parts.append(f", cpp_std={self.cpp_std!r}")
        if self.required_includes is not None:
            parts.append(f", required_includes={self.required_includes!r}")
        return "".join(parts) + ")"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CppType):
            return NotImplemented
        return (
            self.name == other.name
            and self.is_primitive == other.is_primitive
            and self.is_struct == other.is_struct
            and self.is_template == other.is_template
            and self.fields == other.fields
            and self.cpp_std == other.cpp_std
            and self.required_includes == other.required_includes
        )

    def __hash__(self) -> int:
        return hash(self.name)

    def cpp_declaration(self) -> str:
        """Return a C++ struct declaration string, or empty string for non-structs."""
        if not self.is_struct or not self.fields:
            return ""
        lines = [f"struct {self.name} {{"]
        for field_name, field_type in self.fields.items():
            lines.append(f"    {field_type.name} {field_name};")
        lines.append("};")
        return "\n".join(lines)


# ===========================================================================
# _CppProxy hierarchy — Python-side annotations that select C++ templates
# ===========================================================================
#
# Each concrete subclass is declared with keyword arguments that are forwarded
# to _CppProxy.__init_subclass__.  The base class constructor hook assigns the
# three class-level constants (_cpp_template, _cpp_std, _required_includes) so
# that subclasses never need to touch class-variable assignment themselves.
#
# Usage examples:
#   CppArray[float, 3]          → std::array<double, 3>       (C++14)
#   CppSet[int]                 → std::set<int>               (C++14)
#   CppUnorderedMap[str, int]   → std::unordered_map<std::string, int>  (C++14)
#   CppOptional[int]            → std::optional<int>          (C++17)
#   CppVariant[int, float, str] → std::variant<int, double, std::string>  (C++17)
#   CppSpan[double]             → std::span<double>           (C++20)
#   CppExpected[int, str]       → std::expected<int, std::string>  (C++23)
#   CppAny                      → std::any                    (C++17, no subscript)
# ===========================================================================

class _CppProxy:
    """Base for all Python ↔ C++ type proxy annotations.

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


# ---------------------------------------------------------------------------
# C++14 container proxies
# ---------------------------------------------------------------------------

class CppVector(
    _CppProxy,
    cpp_template="std::vector",
    required_includes=["<vector>"],
):
    """Explicit ``std::vector<T>``.  Equivalent to ``list[T]``, but unambiguous.
    Usage: ``CppVector[int]``"""


class CppArray(
    _CppProxy,
    cpp_template="std::array",
    required_includes=["<array>"],
):
    """Fixed-size ``std::array<T, N>`` (C++14).
    Usage: ``CppArray[float, 3]``  →  ``std::array<double, 3>``"""


class CppSet(
    _CppProxy,
    cpp_template="std::set",
    required_includes=["<set>"],
):
    """Ordered ``std::set<T>`` (C++14).  Equivalent to ``set[T]``.
    Usage: ``CppSet[int]``"""


class CppUnorderedSet(
    _CppProxy,
    cpp_template="std::unordered_set",
    required_includes=["<unordered_set>"],
):
    """Hash-based ``std::unordered_set<T>`` (C++14).
    Usage: ``CppUnorderedSet[int]``"""


class CppMultiSet(
    _CppProxy,
    cpp_template="std::multiset",
    required_includes=["<set>"],
):
    """Ordered ``std::multiset<T>`` allowing duplicate elements (C++14).
    Usage: ``CppMultiSet[float]``"""


class CppMap(
    _CppProxy,
    cpp_template="std::map",
    required_includes=["<map>"],
):
    """Ordered ``std::map<K, V>`` (C++14).  Equivalent to ``dict[K, V]``.
    Usage: ``CppMap[str, int]``"""


class CppUnorderedMap(
    _CppProxy,
    cpp_template="std::unordered_map",
    required_includes=["<unordered_map>"],
):
    """Hash-based ``std::unordered_map<K, V>`` (C++14).
    Usage: ``CppUnorderedMap[str, float]``"""


class CppMultiMap(
    _CppProxy,
    cpp_template="std::multimap",
    required_includes=["<map>"],
):
    """Ordered ``std::multimap<K, V>`` allowing duplicate keys (C++14).
    Usage: ``CppMultiMap[str, int]``"""


class CppPair(
    _CppProxy,
    cpp_template="std::pair",
    required_includes=["<utility>"],
):
    """``std::pair<K, V>`` (C++14).
    Usage: ``CppPair[int, float]``"""


# ---------------------------------------------------------------------------
# C++17 proxies
# ---------------------------------------------------------------------------

class CppOptional(
    _CppProxy,
    cpp_template="std::optional",
    cpp_std="c++17",
    required_includes=["<optional>"],
):
    """``std::optional<T>`` (C++17).  Equivalent to ``Optional[T]``.
    Usage: ``CppOptional[int]``"""


class CppVariant(
    _CppProxy,
    cpp_template="std::variant",
    cpp_std="c++17",
    required_includes=["<variant>"],
):
    """``std::variant<T1, T2, …>`` tagged union (C++17).
    Usage: ``CppVariant[int, float, str]``"""


class CppAny(
    _CppProxy,
    cpp_template="std::any",
    cpp_std="c++17",
    required_includes=["<any>"],
):
    """Type-erasing ``std::any`` (C++17).
    Use ``CppAny`` directly without subscript — ``std::any`` carries no type parameter."""


# ---------------------------------------------------------------------------
# C++20 proxy
# ---------------------------------------------------------------------------

class CppSpan(
    _CppProxy,
    cpp_template="std::span",
    cpp_std="c++20",
    required_includes=["<span>"],
):
    """Non-owning contiguous view ``std::span<T>`` (C++20).
    Usage: ``CppSpan[double]``"""


# ---------------------------------------------------------------------------
# C++23 proxies
# ---------------------------------------------------------------------------

class CppExpected(
    _CppProxy,
    cpp_template="std::expected",
    cpp_std="c++23",
    required_includes=["<expected>"],
):
    """Result-type ``std::expected<T, E>`` (C++23).
    Usage: ``CppExpected[int, str]``"""


class CppMdSpan(
    _CppProxy,
    cpp_template="std::mdspan",
    cpp_std="c++23",
    required_includes=["<mdspan>"],
):
    """Multi-dimensional non-owning view ``std::mdspan<T>`` (C++23).
    Usage: ``CppMdSpan[float]``"""


# ===========================================================================
# TemplateParam — represents a C++ template type parameter
# ===========================================================================

class TemplateParam:
    """A C++ template type parameter (``typename T`` in C++14+).

    Create one instance per distinct template parameter name and use it as a
    type annotation in aggregate function definitions.  The transpiler will
    emit an unresolved name and set ``is_template=True`` on the resulting
    ``CppType``.

    Example::

        T = TemplateParam("T")

        @aggregate_function
        class GenericAverage:
            def initial_state(self) -> T: ...
            def compute(self, self_state: T, neighbors: CppVector[T]) -> T: ...
    """

    def __init__(self, name: str) -> None:
        self.name: str = name

    def __repr__(self) -> str:
        return f"TemplateParam({self.name!r})"

    def to_cpp_type(self) -> "CppType":
        """Return an unresolved ``CppType`` representing this template parameter."""
        return CppType(self.name, is_primitive=False, is_template=True)


# ---------------------------------------------------------------------------
# Proxy classification sets — used by AggregateType._infer_bound_proxy
# ---------------------------------------------------------------------------

_SINGLE_ARG_PROXIES: frozenset[type] = frozenset({
    CppVector, CppSet, CppUnorderedSet, CppMultiSet,
    CppOptional, CppSpan, CppMdSpan,
})
_TWO_ARG_PROXIES: frozenset[type] = frozenset({
    CppMap, CppUnorderedMap, CppMultiMap, CppPair, CppExpected,
})


# ===========================================================================
# AggregateType — inference engine
# ===========================================================================

class AggregateType:
    """Infers ``CppType`` descriptors from Python type annotations."""

    # Shared scalar mappings.  AggregateType.infer() returns these directly
    # (not copies) — callers must treat them as read-only.
    PYTHON_TO_CPP: dict[type, CppType] = {
        float: CppType("double",              is_primitive=True),
        int:   CppType("int",                 is_primitive=True),
        bool:  CppType("bool",                is_primitive=True),
        str:   CppType("std::string",         is_primitive=True,
                       required_includes=["<string>"]),
        bytes: CppType("std::vector<uint8_t>", is_primitive=False,
                       required_includes=["<vector>", "<cstdint>"]),
    }

    @staticmethod
    def infer(py_type: Any) -> CppType:
        """Convert a Python type annotation to a ``CppType`` descriptor.

        Handles:

        * Scalars — ``float`` → ``double``, ``int``, ``bool``,
          ``str`` → ``std::string``, ``bytes`` → ``std::vector<uint8_t>``
        * Generic collections — ``list[T]``, ``tuple[T…]``, ``dict[K,V]``,
          ``set[T]``, ``frozenset[T]``
        * Typing constructs — ``Optional[T]``, ``Union[T1,T2,…]``
          (including Python 3.10+ ``T|U`` syntax)
        * ``TypeVar`` / ``TemplateParam`` → unresolved template parameter
          (``is_template=True``)
        * Explicit C++ proxies — ``CppArray``, ``CppSet``, ``CppOptional``,
          ``CppVariant``, ``CppAny``, …
        * Dataclass / annotated class → C++ struct
        """
        # --- explicit proxy: CppArray[float, 3], CppSet[int], etc. ---------
        if isinstance(py_type, _BoundCppProxy):
            return AggregateType._infer_bound_proxy(py_type)

        # --- proxy class used directly (only CppAny is valid unsubscripted) -
        if isinstance(py_type, type) and issubclass(py_type, _CppProxy) and py_type is not _CppProxy:
            return AggregateType._infer_proxy_class(py_type)

        # --- TemplateParam --------------------------------------------------
        if isinstance(py_type, TemplateParam):
            return py_type.to_cpp_type()

        # --- typing.TypeVar → unresolved template parameter ----------------
        if isinstance(py_type, TypeVar):
            return CppType(py_type.__name__, is_primitive=False, is_template=True)

        # --- scalar primitives ---------------------------------------------
        if py_type in AggregateType.PYTHON_TO_CPP:
            return AggregateType.PYTHON_TO_CPP[py_type]

        origin = get_origin(py_type)

        # --- list[T] → std::vector<T> --------------------------------------
        if origin is list:
            args = get_args(py_type)
            if args:
                elem = AggregateType.infer(args[0])
                return CppType(
                    f"std::vector<{elem.name}>",
                    is_primitive=False,
                    required_includes=_merge(["<vector>"], elem.required_includes),
                )
            return CppType("std::vector<double>", is_primitive=False,
                           required_includes=["<vector>"])

        # --- tuple[T, …] → std::tuple<T1, T2, …> --------------------------
        if origin is tuple:
            args = get_args(py_type)
            if args:
                elems = [AggregateType.infer(a) for a in args]
                type_list = ", ".join(e.name for e in elems)
                return CppType(
                    f"std::tuple<{type_list}>",
                    is_primitive=False,
                    required_includes=_merge(["<tuple>"],
                                             *[e.required_includes for e in elems]),
                )
            return CppType("std::tuple<>", is_primitive=False,
                           required_includes=["<tuple>"])

        # --- dict[K, V] → std::map<K, V> -----------------------------------
        if origin is dict:
            args = get_args(py_type)
            if len(args) >= 2:
                k = AggregateType.infer(args[0])
                v = AggregateType.infer(args[1])
                return CppType(
                    f"std::map<{k.name}, {v.name}>",
                    is_primitive=False,
                    required_includes=_merge(["<map>"],
                                             k.required_includes, v.required_includes),
                )
            return CppType("std::map<std::string, double>", is_primitive=False,
                           required_includes=["<map>", "<string>"])

        # --- set[T] → std::set<T> ------------------------------------------
        if origin is set:
            args = get_args(py_type)
            if args:
                elem = AggregateType.infer(args[0])
                return CppType(
                    f"std::set<{elem.name}>",
                    is_primitive=False,
                    required_includes=_merge(["<set>"], elem.required_includes),
                )
            return CppType("std::set<double>", is_primitive=False,
                           required_includes=["<set>"])

        # --- frozenset[T] → std::set<T>  (immutable Python = ordered C++) --
        if origin is frozenset:
            args = get_args(py_type)
            if args:
                elem = AggregateType.infer(args[0])
                return CppType(
                    f"std::set<{elem.name}>",
                    is_primitive=False,
                    required_includes=_merge(["<set>"], elem.required_includes),
                )
            return CppType("std::set<double>", is_primitive=False,
                           required_includes=["<set>"])

        # --- Optional[T] / Union[T, None] → std::optional<T>  (C++17)
        # --- Union[T1, T2, …]             → std::variant<T1, T2, …> (C++17)
        if AggregateType._is_union(origin, py_type):
            args = get_args(py_type)
            non_none = [a for a in args if a is not type(None)]
            if len(args) == 2 and type(None) in args and len(non_none) == 1:
                inner = AggregateType.infer(non_none[0])
                return CppType(
                    f"std::optional<{inner.name}>",
                    is_primitive=False,
                    cpp_std="c++17",
                    required_includes=_merge(["<optional>"], inner.required_includes),
                )
            elems = [AggregateType.infer(a) for a in args]
            type_list = ", ".join(e.name for e in elems)
            return CppType(
                f"std::variant<{type_list}>",
                is_primitive=False,
                cpp_std="c++17",
                required_includes=_merge(["<variant>"],
                                         *[e.required_includes for e in elems]),
            )

        # --- dataclass → C++ struct ----------------------------------------
        if hasattr(py_type, "__dataclass_fields__"):
            struct_name = py_type.__name__
            fields_dict: dict[str, CppType] = {}
            all_inc: list[str] = []
            for fname, fobj in py_type.__dataclass_fields__.items():
                ft = AggregateType.infer(fobj.type)
                fields_dict[fname] = ft
                all_inc.extend(ft.required_includes or [])
            deduped = list(dict.fromkeys(all_inc))
            return CppType(
                struct_name,
                is_primitive=False,
                is_struct=True,
                fields=fields_dict,
                required_includes=deduped if deduped else None,
            )

        # --- annotated class → C++ struct ----------------------------------
        if hasattr(py_type, "__annotations__"):
            struct_name = py_type.__name__
            fields_dict = {}
            all_inc = []
            for fname, ftype in py_type.__annotations__.items():
                ft = AggregateType.infer(ftype)
                fields_dict[fname] = ft
                all_inc.extend(ft.required_includes or [])
            deduped = list(dict.fromkeys(all_inc))
            return CppType(
                struct_name,
                is_primitive=False,
                is_struct=True,
                fields=fields_dict,
                required_includes=deduped if deduped else None,
            )

        # --- bare class name fallback ---------------------------------------
        if hasattr(py_type, "__name__"):
            return CppType(py_type.__name__, is_primitive=False)

        raise ValueError(f"Cannot infer C++ type for Python type: {py_type!r}")

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _is_union(origin: Any, py_type: Any) -> bool:
        if origin is Union:
            return True
        try:
            if isinstance(py_type, _builtins_types.UnionType):   # Python 3.10+ T | U
                return True
        except AttributeError:
            pass
        return False

    @staticmethod
    def _infer_bound_proxy(proxy: _BoundCppProxy) -> CppType:
        cls = proxy._proxy_cls
        args = proxy._args
        template = cls._cpp_template
        cpp_std = cls._cpp_std
        base_inc = list(cls._required_includes)

        if cls is CppAny:
            raise TypeError("CppAny does not accept type arguments — use CppAny directly")

        if cls is CppArray:
            if len(args) != 2:
                raise TypeError("CppArray requires exactly 2 parameters: CppArray[T, N]")
            elem = AggregateType.infer(args[0])
            size = args[1]
            if not isinstance(size, int):
                raise TypeError(
                    f"CppArray size must be an int literal, got {type(size).__name__!r}")
            return CppType(
                f"std::array<{elem.name}, {size}>",
                is_primitive=False,
                required_includes=_merge(base_inc, elem.required_includes),
            )

        if cls is CppVariant:
            if len(args) < 2:
                raise TypeError("CppVariant requires at least 2 type arguments")
            elems = [AggregateType.infer(a) for a in args]
            type_list = ", ".join(e.name for e in elems)
            return CppType(
                f"std::variant<{type_list}>",
                is_primitive=False,
                cpp_std=cpp_std,
                required_includes=_merge(base_inc,
                                         *[e.required_includes for e in elems]),
            )

        if cls in _SINGLE_ARG_PROXIES:
            if len(args) != 1:
                raise TypeError(f"{cls.__name__} requires exactly 1 type argument")
            elem = AggregateType.infer(args[0])
            return CppType(
                f"{template}<{elem.name}>",
                is_primitive=False,
                cpp_std=cpp_std,
                required_includes=_merge(base_inc, elem.required_includes),
            )

        if cls in _TWO_ARG_PROXIES:
            if len(args) != 2:
                raise TypeError(f"{cls.__name__} requires exactly 2 type arguments")
            t1 = AggregateType.infer(args[0])
            t2 = AggregateType.infer(args[1])
            return CppType(
                f"{template}<{t1.name}, {t2.name}>",
                is_primitive=False,
                cpp_std=cpp_std,
                required_includes=_merge(base_inc,
                                         t1.required_includes, t2.required_includes),
            )

        raise TypeError(f"Unknown C++ proxy class: {cls.__name__!r}")

    @staticmethod
    def _infer_proxy_class(cls: type) -> CppType:
        if cls is CppAny:
            return CppType(
                "std::any",
                is_primitive=False,
                cpp_std="c++17",
                required_includes=["<any>"],
            )
        raise TypeError(
            f"{cls.__name__} requires type arguments — use {cls.__name__}[T]")

    # -----------------------------------------------------------------------
    # Transpiler helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def cpp_declaration(cpp_type: CppType) -> str:
        return cpp_type.cpp_declaration()

    @staticmethod
    def is_numeric(cpp_type: CppType) -> bool:
        return cpp_type.name in (
            "int", "double", "float", "long", "short",
            "uint8_t", "int8_t", "uint16_t", "int16_t",
            "uint32_t", "int32_t", "uint64_t", "int64_t",
        )

    @staticmethod
    def is_container(cpp_type: CppType) -> bool:
        return any(
            token in cpp_type.name
            for token in (
                "std::vector", "std::array",
                "std::set", "std::multiset", "std::unordered_set",
                "std::map", "std::multimap", "std::unordered_map",
                "std::tuple", "std::pair",
                "std::optional", "std::variant", "std::any",
                "std::span", "std::expected", "std::mdspan",
            )
        )


# ===========================================================================
# Module-level utility
# ===========================================================================

def _merge(*include_lists: list[str] | None) -> list[str] | None:
    """Deduplicate and flatten include lists; return ``None`` when all empty."""
    seen: dict[str, None] = {}
    for lst in include_lists:
        if lst:
            for inc in lst:
                seen[inc] = None
    return list(seen) if seen else None
