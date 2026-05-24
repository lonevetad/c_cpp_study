"""CppType — C++ type descriptor."""

from __future__ import annotations


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
