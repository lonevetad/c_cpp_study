from __future__ import annotations

import ctypes
import os
import platform
from pathlib import Path

_pkg = Path(__file__).parent

if platform.system() == "Windows":
    os.add_dll_directory(str(_pkg))
    _lib = ctypes.CDLL(str(_pkg / "_fcpp_core.dll"))
else:
    _lib = ctypes.CDLL(str(_pkg / "_fcpp_core.so"))

_dp = ctypes.POINTER(ctypes.c_double)
_cd = ctypes.c_double
_i4 = ctypes.c_int32


def _bind(name: str, restype, *argtypes) -> None:
    fn = getattr(_lib, name)
    fn.restype  = restype
    fn.argtypes = list(argtypes)


_bind("fcpp_py_version", ctypes.c_char_p)

for _pfx in ("fcpp_vec2", "fcpp_vec3"):
    _bind(f"{_pfx}_norm",     _cd,  _dp)
    _bind(f"{_pfx}_distance", _cd,  _dp, _dp)
    _bind(f"{_pfx}_dot",      _cd,  _dp, _dp)
    _bind(f"{_pfx}_add",      None, _dp, _dp, _dp)
    _bind(f"{_pfx}_sub",      None, _dp, _dp, _dp)
    _bind(f"{_pfx}_mul",      None, _dp, _cd, _dp)
    _bind(f"{_pfx}_div",      None, _dp, _cd, _dp)
    _bind(f"{_pfx}_neg",      None, _dp, _dp)
    _bind(f"{_pfx}_unit",     None, _dp, _dp)
    _bind(f"{_pfx}_eq",       _i4,  _dp, _dp)


def version() -> str:
    return _lib.fcpp_py_version().decode()


_Arr2 = ctypes.c_double * 2
_Arr3 = ctypes.c_double * 3


class Vec2:
    __slots__ = ("_data",)

    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self._data = _Arr2(x, y)

    @classmethod
    def _from_arr(cls, arr: "_Arr2") -> "Vec2":
        v = object.__new__(cls)
        v._data = arr
        return v

    def __getitem__(self, i: int) -> float:
        return self._data[i]

    def __setitem__(self, i: int, v: float) -> None:
        self._data[i] = v

    @property
    def x(self) -> float: return self._data[0]
    @property
    def y(self) -> float: return self._data[1]

    def norm(self) -> float:
        return _lib.fcpp_vec2_norm(self._data)

    def unit(self) -> "Vec2":
        out = _Arr2()
        _lib.fcpp_vec2_unit(self._data, out)
        return Vec2._from_arr(out)

    def dot(self, other: "Vec2") -> float:
        return _lib.fcpp_vec2_dot(self._data, other._data)

    def distance(self, other: "Vec2") -> float:
        return _lib.fcpp_vec2_distance(self._data, other._data)

    def __add__(self, other: "Vec2") -> "Vec2":
        out = _Arr2()
        _lib.fcpp_vec2_add(self._data, other._data, out)
        return Vec2._from_arr(out)

    def __sub__(self, other: "Vec2") -> "Vec2":
        out = _Arr2()
        _lib.fcpp_vec2_sub(self._data, other._data, out)
        return Vec2._from_arr(out)

    def __mul__(self, s: float) -> "Vec2":
        out = _Arr2()
        _lib.fcpp_vec2_mul(self._data, s, out)
        return Vec2._from_arr(out)

    def __rmul__(self, s: float) -> "Vec2":
        return self.__mul__(s)

    def __truediv__(self, s: float) -> "Vec2":
        out = _Arr2()
        _lib.fcpp_vec2_div(self._data, s, out)
        return Vec2._from_arr(out)

    def __neg__(self) -> "Vec2":
        out = _Arr2()
        _lib.fcpp_vec2_neg(self._data, out)
        return Vec2._from_arr(out)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vec2): return NotImplemented
        return bool(_lib.fcpp_vec2_eq(self._data, other._data))

    def __repr__(self) -> str:
        return f"Vec2({self._data[0]}, {self._data[1]})"

    def __iter__(self):
        return iter(self._data)

    def __len__(self) -> int:
        return 2


class Vec3:
    __slots__ = ("_data",)

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> None:
        self._data = _Arr3(x, y, z)

    @classmethod
    def _from_arr(cls, arr: "_Arr3") -> "Vec3":
        v = object.__new__(cls)
        v._data = arr
        return v

    def __getitem__(self, i: int) -> float:
        return self._data[i]

    def __setitem__(self, i: int, v: float) -> None:
        self._data[i] = v

    @property
    def x(self) -> float: return self._data[0]
    @property
    def y(self) -> float: return self._data[1]
    @property
    def z(self) -> float: return self._data[2]

    def norm(self) -> float:
        return _lib.fcpp_vec3_norm(self._data)

    def unit(self) -> "Vec3":
        out = _Arr3()
        _lib.fcpp_vec3_unit(self._data, out)
        return Vec3._from_arr(out)

    def dot(self, other: "Vec3") -> float:
        return _lib.fcpp_vec3_dot(self._data, other._data)

    def distance(self, other: "Vec3") -> float:
        return _lib.fcpp_vec3_distance(self._data, other._data)

    def __add__(self, other: "Vec3") -> "Vec3":
        out = _Arr3()
        _lib.fcpp_vec3_add(self._data, other._data, out)
        return Vec3._from_arr(out)

    def __sub__(self, other: "Vec3") -> "Vec3":
        out = _Arr3()
        _lib.fcpp_vec3_sub(self._data, other._data, out)
        return Vec3._from_arr(out)

    def __mul__(self, s: float) -> "Vec3":
        out = _Arr3()
        _lib.fcpp_vec3_mul(self._data, s, out)
        return Vec3._from_arr(out)

    def __rmul__(self, s: float) -> "Vec3":
        return self.__mul__(s)

    def __truediv__(self, s: float) -> "Vec3":
        out = _Arr3()
        _lib.fcpp_vec3_div(self._data, s, out)
        return Vec3._from_arr(out)

    def __neg__(self) -> "Vec3":
        out = _Arr3()
        _lib.fcpp_vec3_neg(self._data, out)
        return Vec3._from_arr(out)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vec3): return NotImplemented
        return bool(_lib.fcpp_vec3_eq(self._data, other._data))

    def __repr__(self) -> str:
        return f"Vec3({self._data[0]}, {self._data[1]}, {self._data[2]})"

    def __iter__(self):
        return iter(self._data)

    def __len__(self) -> int:
        return 3
