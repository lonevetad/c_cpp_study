from ._cpp_proxy import _CppProxy


class CppUnorderedMap(
    _CppProxy,
    cpp_template="std::unordered_map",
    required_includes=["<unordered_map>"],
):
    """Hash-based ``std::unordered_map<K, V>`` (C++14).
    Usage: ``CppUnorderedMap[str, float]``"""
