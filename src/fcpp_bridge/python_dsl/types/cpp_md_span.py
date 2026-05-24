from ._cpp_proxy import _CppProxy


class CppMdSpan(
    _CppProxy,
    cpp_template="std::mdspan",
    cpp_std="c++23",
    required_includes=["<mdspan>"],
):
    """Multi-dimensional non-owning view ``std::mdspan<T>`` (C++23).
    Usage: ``CppMdSpan[float]``"""
