from __future__ import annotations

import types as _builtins_types
from typing import Any, TypeVar, Union, get_args, get_origin

from .cpp_type import CppType
from ._cpp_proxy import _CppProxy, _BoundCppProxy
from .cpp_vector import CppVector
from .cpp_array import CppArray
from .cpp_set import CppSet
from .cpp_unordered_set import CppUnorderedSet
from .cpp_multi_set import CppMultiSet
from .cpp_map import CppMap
from .cpp_unordered_map import CppUnorderedMap
from .cpp_multi_map import CppMultiMap
from .cpp_pair import CppPair
from .cpp_optional import CppOptional
from .cpp_variant import CppVariant
from .cpp_any import CppAny
from .cpp_span import CppSpan
from .cpp_expected import CppExpected
from .cpp_md_span import CppMdSpan
from .template_param import TemplateParam


_SINGLE_ARG_PROXIES: frozenset[type] = frozenset({
    CppVector, CppSet, CppUnorderedSet, CppMultiSet,
    CppOptional, CppSpan, CppMdSpan,
})
_TWO_ARG_PROXIES: frozenset[type] = frozenset({
    CppMap, CppUnorderedMap, CppMultiMap, CppPair, CppExpected,
})


def _merge(*include_lists: list[str] | None) -> list[str] | None:
    """Deduplicate and flatten include lists; return ``None`` when all empty."""
    seen: dict[str, None] = {}
    for lst in include_lists:
        if lst:
            for inc in lst:
                seen[inc] = None
    return list(seen) if seen else None


class AggregateType:
    """Infers ``CppType`` descriptors from Python type annotations."""

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
        """Convert a Python type annotation to a ``CppType`` descriptor."""
        if isinstance(py_type, _BoundCppProxy):
            return AggregateType._infer_bound_proxy(py_type)

        if isinstance(py_type, type) and issubclass(py_type, _CppProxy) and py_type is not _CppProxy:
            return AggregateType._infer_proxy_class(py_type)

        if isinstance(py_type, TemplateParam):
            return py_type.to_cpp_type()

        if isinstance(py_type, TypeVar):
            return CppType(py_type.__name__, is_primitive=False, is_template=True)

        if py_type in AggregateType.PYTHON_TO_CPP:
            return AggregateType.PYTHON_TO_CPP[py_type]

        origin = get_origin(py_type)

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

        if hasattr(py_type, "__name__"):
            return CppType(py_type.__name__, is_primitive=False)

        raise ValueError(f"Cannot infer C++ type for Python type: {py_type!r}")

    @staticmethod
    def _is_union(origin: Any, py_type: Any) -> bool:
        if origin is Union:
            return True
        try:
            if isinstance(py_type, _builtins_types.UnionType):
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
