from __future__ import annotations

import ctypes
import os
import platform
from pathlib import Path

_pkg = Path(__file__).parent

_system = platform.system()
if _system == "Windows":
    os.add_dll_directory(str(_pkg))
    _lib = ctypes.CDLL(str(_pkg / "_fcpp_core.dll"))
elif _system == "Darwin":
    _lib = ctypes.CDLL(str(_pkg / "_fcpp_core.dylib"))
else:
    _lib = ctypes.CDLL(str(_pkg / "_fcpp_core.so"))

_dp = ctypes.POINTER(ctypes.c_double)
_cd = ctypes.c_double
_i4 = ctypes.c_int32


def _bind(name: str, restype, *argtypes) -> None:
    fn = getattr(_lib, name)
    fn.restype = restype
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
        if not isinstance(other, Vec2):
            return NotImplemented
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
        if not isinstance(other, Vec3):
            return NotImplemented
        return bool(_lib.fcpp_vec3_eq(self._data, other._data))

    def __repr__(self) -> str:
        return f"Vec3({self._data[0]}, {self._data[1]}, {self._data[2]})"

    def __iter__(self):
        return iter(self._data)

    def __len__(self) -> int:
        return 3


# ── Simulation bindings ───────────────────────────────────────────────────

_bind("fcpp_sim_state_size",    _i4)
_bind("fcpp_sim_max_devices",   _i4)
_bind("fcpp_sim_dimension",     _i4)

_bind("fcpp_sim_create",        _i4)
_bind("fcpp_sim_set_callback",  None, ctypes.c_void_p)
_bind("fcpp_sim_run",           None, _cd)
_bind("fcpp_sim_step",          _cd)
_bind("fcpp_sim_next_time",     _cd)
_bind("fcpp_sim_device_count",  _i4)
_bind("fcpp_sim_get_ids",       _i4, ctypes.POINTER(_i4), _i4)
_bind("fcpp_sim_get_state",     _i4, _i4, _dp)
_bind("fcpp_sim_get_all_states", _i4, ctypes.POINTER(_i4), _dp, _i4)
_bind("fcpp_sim_destroy",       None)


class Simulation:
    """fcpp aggregate computing simulator with Python per-round callbacks."""

    def __init__(self, state_size: int = 8, max_devices: int = 100, dimension: int = 3) -> None:
        """
        Create new simulation.

        Args:
            state_size: device state array length (must match compile-time FCPP_PY_STATE_SIZE)
            max_devices: max device count (must match compile-time FCPP_PY_DEVICES)
            dimension: spatial dimension (must match compile-time FCPP_PY_DIM)
        """
        if _lib.fcpp_sim_create() != 0:
            raise RuntimeError("fcpp_sim_create failed")
        self._state_size = _lib.fcpp_sim_state_size()
        self._max_devices = _lib.fcpp_sim_max_devices()
        self._dimension = _lib.fcpp_sim_dimension()
        self._callback = None

    def set_callback(self, fn) -> None:
        """
        Set per-round callback. fn(device_id: int, time: float, self_state: list[float],
        neighbor_ids: list[int], neighbor_states: list[list[float]]) -> list[float]
        """
        if not callable(fn):
            raise TypeError("callback must be callable")

        def c_callback(dev_id, t, self_prev_ptr, nbr_ids_ptr, nbr_states_ptr, nbr_cnt, result_ptr):
            self_prev = [self_prev_ptr[i] for i in range(self._state_size)]
            nbr_ids = [nbr_ids_ptr[i] for i in range(nbr_cnt)]
            nbr_states = [
                [nbr_states_ptr[i * self._state_size + j]
                    for j in range(self._state_size)]
                for i in range(nbr_cnt)
            ]
            result = fn(dev_id, t, self_prev, nbr_ids, nbr_states)
            for i, v in enumerate(result):
                result_ptr[i] = v

        self._callback_c_type = ctypes.CFUNCTYPE(
            None, _i4, _cd, _dp, ctypes.POINTER(_i4), _dp, _i4, _dp
        )
        self._callback = self._callback_c_type(c_callback)
        _lib.fcpp_sim_set_callback(
            ctypes.cast(self._callback, ctypes.c_void_p))

    def run(self, end_time: float) -> None:
        """Run simulation until time >= end_time."""
        _lib.fcpp_sim_run(end_time)

    def step(self) -> float:
        """Advance one scheduled event. Returns next event time, -1 if done."""
        return _lib.fcpp_sim_step()

    def next_time(self) -> float:
        """Get next scheduled event time (-1 if done)."""
        return _lib.fcpp_sim_next_time()

    def device_count(self) -> int:
        """Current device count."""
        devices_count = _lib.fcpp_sim_device_count()
        MAX_DEICES_COUNT = 1024
        if devices_count > MAX_DEICES_COUNT:
            print(f"MAX devices_count reached: {devices_count}")
            devices_count = MAX_DEICES_COUNT
        return devices_count

    def get_ids(self) -> list[int]:
        """Get all device IDs."""
        cnt = self.device_count()
        ids = (_i4 * cnt)()
        n = _lib.fcpp_sim_get_ids(ids, cnt)
        return list(ids[:n])

    def get_state(self, device_id: int) -> list[float] | None:
        """Get device exported state. Returns None if not found."""
        state = (_cd * self._state_size)()
        if _lib.fcpp_sim_get_state(device_id, state) == 0:
            return None
        return list(state)

    def get_all_states(self) -> tuple[list[int], list[list[float]]]:
        """Get all device states. Returns (ids, states_rows)."""
        cnt = self.device_count()
        ids = (_i4 * cnt)()
        states = (_cd * (cnt * self._state_size))()
        n = _lib.fcpp_sim_get_all_states(ids, states, cnt)
        ids_list = list(ids[:n])
        states_list = [
            list(states[i * self._state_size:(i + 1) * self._state_size])
            for i in range(n)
        ]
        return ids_list, states_list

    def destroy(self) -> None:
        """Destroy simulation and free memory."""
        _lib.fcpp_sim_destroy()

    def __enter__(self) -> "Simulation":
        return self

    def __exit__(self, *_) -> None:
        self.destroy()

    @staticmethod
    def compile_info() -> dict:
        """Get compile-time constants."""
        return {
            "state_size": _lib.fcpp_sim_state_size(),
            "max_devices": _lib.fcpp_sim_max_devices(),
            "dimension": _lib.fcpp_sim_dimension(),
        }
