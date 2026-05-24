from ._cpp_proxy import _CppProxy


class CppOptional(
    _CppProxy,
    cpp_template="std::optional",
    cpp_std="c++17",
    required_includes=["<optional>"],
):
    """``std::optional<T>`` (C++17).  Equivalent to ``Optional[T]``.
    Usage: ``CppOptional[int]``"""
