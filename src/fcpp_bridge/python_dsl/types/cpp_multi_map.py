from ._cpp_proxy import _CppProxy


class CppMultiMap(
    _CppProxy,
    cpp_template="std::multimap",
    required_includes=["<map>"],
):
    """Ordered ``std::multimap<K, V>`` allowing duplicate keys (C++14).
    Usage: ``CppMultiMap[str, int]``"""
