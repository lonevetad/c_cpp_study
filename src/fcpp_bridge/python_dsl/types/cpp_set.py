from ._cpp_proxy import _CppProxy


class CppSet(
    _CppProxy,
    cpp_template="std::set",
    required_includes=["<set>"],
):
    """Ordered ``std::set<T>`` (C++14).  Equivalent to ``set[T]``.
    Usage: ``CppSet[int]``"""
