from ._cpp_proxy import _CppProxy


class CppArray(
    _CppProxy,
    cpp_template="std::array",
    required_includes=["<array>"],
):
    """Fixed-size ``std::array<T, N>`` (C++14).
    Usage: ``CppArray[float, 3]``  ->  ``std::array<double, 3>``"""
