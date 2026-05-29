"""FCPP Bridge — Python-to-C++ DSL and transpiler."""

__version__ = "0.1.0"
__description__ = "Dynamic transpilation pipeline for FCPP aggregate programs"

from .python_dsl import (
    Field,
    Neighborhood,
    OldValue,
    aggregate_function,
    AggregateType,
)
from .transpiler import Transpiler

__all__ = [
    "Field",
    "Neighborhood",
    "OldValue",
    "aggregate_function",
    "AggregateType",
    "Transpiler",
]
