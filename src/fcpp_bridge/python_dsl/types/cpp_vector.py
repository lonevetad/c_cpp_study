from ._cpp_proxy import _CppProxy


class CppVector(
    _CppProxy,
    cpp_template="std::vector",
    required_includes=["<vector>"],
):
    """Explicit ``std::vector<T>``.  Equivalent to ``list[T]``, but unambiguous.
    Usage: ``CppVector[int]``"""
