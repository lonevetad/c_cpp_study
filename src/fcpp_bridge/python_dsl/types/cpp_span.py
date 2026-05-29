from ._cpp_proxy import _CppProxy


class CppSpan(
    _CppProxy,
    cpp_template="std::span",
    cpp_std="c++20",
    required_includes=["<span>"],
):
    """Non-owning contiguous view ``std::span<T>`` (C++20).
    Usage: ``CppSpan[double]``"""
