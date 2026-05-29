from ._cpp_proxy import _CppProxy


class CppUnorderedSet(
    _CppProxy,
    cpp_template="std::unordered_set",
    required_includes=["<unordered_set>"],
):
    """Hash-based ``std::unordered_set<T>`` (C++14).
    Usage: ``CppUnorderedSet[int]``"""
