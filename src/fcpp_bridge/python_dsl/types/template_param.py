from __future__ import annotations

from .cpp_type import CppType


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

    def to_cpp_type(self) -> CppType:
        """Return an unresolved ``CppType`` representing this template parameter."""
        return CppType(self.name, is_primitive=False, is_template=True)
