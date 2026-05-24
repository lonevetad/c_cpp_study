from ._cpp_proxy import _CppProxy


class CppExpected(
    _CppProxy,
    cpp_template="std::expected",
    cpp_std="c++23",
    required_includes=["<expected>"],
):
    """Result-type ``std::expected<T, E>`` (C++23).
    Usage: ``CppExpected[int, str]``"""
