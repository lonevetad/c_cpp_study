from ._cpp_proxy import _CppProxy


class CppPair(
    _CppProxy,
    cpp_template="std::pair",
    required_includes=["<utility>"],
):
    """``std::pair<K, V>`` (C++14).
    Usage: ``CppPair[int, float]``"""
