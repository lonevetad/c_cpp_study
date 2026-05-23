"""Type system for code generation — Python types map to C++ types."""

from typing import Type, Union, Any, get_origin, get_args
from dataclasses import dataclass, fields as dataclass_fields


@dataclass
class CppType:
    """C++ type descriptor."""

    name: str  # e.g., "double", "int", "MyState"
    is_primitive: bool = True
    is_struct: bool = False
    fields: dict[str, "CppType"] | None = None  # for struct types

    def cpp_declaration(self) -> str:
        """Generate C++ code for this type."""
        if not self.is_struct or not self.fields:
            return ""

        lines = [f"struct {self.name} {{"]
        for field_name, field_type in self.fields.items():
            lines.append(f"    {field_type.name} {field_name};")
        lines.append("};")
        return "\n".join(lines)


class AggregateType:
    """Infers C++ types from Python type annotations."""

    PYTHON_TO_CPP = {
        float: CppType("double", is_primitive=True),
        int: CppType("int", is_primitive=True),
        bool: CppType("bool", is_primitive=True),
        str: CppType("std::string", is_primitive=True),
    }

    @staticmethod
    def infer(py_type: Type) -> CppType:
        """
        Convert Python type annotation to C++ type descriptor.

        Supports:
        - Primitives: float, int, bool, str
        - Collections: list[T], tuple[T, ...], dict
        - Custom types: @dataclass, regular classes
        """
        if py_type in AggregateType.PYTHON_TO_CPP:
            return AggregateType.PYTHON_TO_CPP[py_type]

        origin = get_origin(py_type)

        # Handle list[T]
        if origin is list:
            args = get_args(py_type)
            if args:
                elem_type = AggregateType.infer(args[0])
                return CppType(
                    f"std::vector<{elem_type.name}>", is_primitive=False
                )
            return CppType("std::vector<double>", is_primitive=False)

        # Handle tuple[T, ...]
        if origin is tuple:
            args = get_args(py_type)
            if args:
                # Fixed-size tuple → std::tuple<T1, T2, ...>
                elem_types = [AggregateType.infer(arg).name for arg in args]
                type_list = ", ".join(elem_types)
                return CppType(f"std::tuple<{type_list}>", is_primitive=False)
            return CppType("std::tuple<>", is_primitive=False)

        # Handle dict[K, V]
        if origin is dict:
            args = get_args(py_type)
            if len(args) >= 2:
                key_type = AggregateType.infer(args[0]).name
                val_type = AggregateType.infer(args[1]).name
                return CppType(
                    f"std::map<{key_type}, {val_type}>", is_primitive=False
                )
            return CppType("std::map<std::string, double>", is_primitive=False)

        # Handle dataclass
        if hasattr(py_type, "__dataclass_fields__"):
            struct_name = py_type.__name__
            fields_dict = {}
            for field_name, field in py_type.__dataclass_fields__.items():
                fields_dict[field_name] = AggregateType.infer(field.type)
            return CppType(struct_name, is_struct=True, fields=fields_dict)

        # Handle regular classes with type hints
        if hasattr(py_type, "__annotations__"):
            struct_name = py_type.__name__
            fields_dict = {}
            for field_name, field_type in py_type.__annotations__.items():
                fields_dict[field_name] = AggregateType.infer(field_type)
            return CppType(struct_name, is_struct=True, fields=fields_dict)

        # Fallback: assume it's a custom type, use class name
        if hasattr(py_type, "__name__"):
            return CppType(py_type.__name__, is_primitive=False)

        raise ValueError(f"Cannot infer C++ type for Python type: {py_type}")

    @staticmethod
    def cpp_declaration(cpp_type: CppType) -> str:
        """Generate C++ struct declaration for a custom type."""
        return cpp_type.cpp_declaration()

    @staticmethod
    def is_numeric(cpp_type: CppType) -> bool:
        """Check if type is numeric (int, double, float)."""
        return cpp_type.name in ("int", "double", "float", "long", "short")

    @staticmethod
    def is_container(cpp_type: CppType) -> bool:
        """Check if type is a container (vector, map, tuple)."""
        return any(
            container in cpp_type.name
            for container in ("std::vector", "std::map", "std::tuple")
        )
