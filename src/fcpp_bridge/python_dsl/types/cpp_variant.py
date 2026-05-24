from ._cpp_proxy import _CppProxy


class CppVariant(
    _CppProxy,
    cpp_template="std::variant",
    cpp_std="c++17",
    required_includes=["<variant>"],
):
    """``std::variant<T1, T2, …>`` tagged union (C++17).
    Usage: ``CppVariant[int, float, str]``"""
