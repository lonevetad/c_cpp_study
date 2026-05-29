from ._cpp_proxy import _CppProxy


class CppMap(
    _CppProxy,
    cpp_template="std::map",
    required_includes=["<map>"],
):
    """Ordered ``std::map<K, V>`` (C++14).  Equivalent to ``dict[K, V]``.
    Usage: ``CppMap[str, int]``"""
