from ._cpp_proxy import _CppProxy


class CppAny(
    _CppProxy,
    cpp_template="std::any",
    cpp_std="c++17",
    required_includes=["<any>"],
):
    """Type-erasing ``std::any`` (C++17).
    Use ``CppAny`` directly without subscript — ``std::any`` carries no type parameter."""
