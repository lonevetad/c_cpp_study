from ._cpp_proxy import _CppProxy


class CppMultiSet(
    _CppProxy,
    cpp_template="std::multiset",
    required_includes=["<set>"],
):
    """Ordered ``std::multiset<T>`` allowing duplicate elements (C++14).
    Usage: ``CppMultiSet[float]``"""
