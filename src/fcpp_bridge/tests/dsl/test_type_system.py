"""Tests for C++ type inference — Tests 8 and extended type system (Test 11-ext)."""

import pytest
from dataclasses import dataclass as dc
from typing import Optional, Union
from typing import TypeVar as TypingTypeVar
from fcpp_bridge.python_dsl import (
    AggregateType, CppType, TemplateParam,
    CppVector, CppArray,
    CppSet, CppUnorderedSet, CppMultiSet,
    CppMap, CppUnorderedMap, CppMultiMap,
    CppPair, CppOptional, CppVariant, CppAny,
    CppSpan, CppExpected, CppMdSpan,
)


# ============================================================================
# Test 8: Type inference
# ============================================================================


def test_type_inference_float():
    cpp_type = AggregateType.infer(float)
    assert cpp_type.name == "double"
    assert cpp_type.is_primitive


def test_type_inference_int():
    cpp_type = AggregateType.infer(int)
    assert cpp_type.name == "int"
    assert cpp_type.is_primitive


def test_type_inference_list():
    cpp_type = AggregateType.infer(list[float])
    assert "vector" in cpp_type.name
    assert "double" in cpp_type.name


def test_type_inference_custom_struct():
    @dc
    class MyState:
        x: float
        y: int

    cpp_type = AggregateType.infer(MyState)
    assert cpp_type.name == "MyState"
    assert cpp_type.is_struct
    assert "x" in cpp_type.fields
    assert "y" in cpp_type.fields


# ============================================================================
# Test 11-ext: Extended C++ type system
# ============================================================================


# ---- scalar additions -------------------------------------------------------

def test_type_inference_str_includes():
    ct = AggregateType.infer(str)
    assert ct.name == "std::string"
    assert "<string>" in (ct.required_includes or [])


def test_type_inference_bytes():
    ct = AggregateType.infer(bytes)
    assert "uint8_t" in ct.name
    assert "<cstdint>" in (ct.required_includes or [])


# ---- set / frozenset --------------------------------------------------------

def test_type_inference_set():
    ct = AggregateType.infer(set[float])
    assert ct.name == "std::set<double>"
    assert "<set>" in (ct.required_includes or [])
    assert AggregateType.is_container(ct)


def test_type_inference_frozenset():
    ct = AggregateType.infer(frozenset[int])
    assert ct.name == "std::set<int>"
    assert "<set>" in (ct.required_includes or [])


def test_type_inference_set_no_args():
    ct = AggregateType.infer(set)
    assert "set" in ct.name


# ---- Optional / Union -------------------------------------------------------

def test_type_inference_optional():
    ct = AggregateType.infer(Optional[int])
    assert ct.name == "std::optional<int>"
    assert ct.cpp_std == "c++17"
    assert "<optional>" in (ct.required_includes or [])
    assert AggregateType.is_container(ct)


def test_type_inference_union_two():
    ct = AggregateType.infer(Union[int, float])
    assert ct.name == "std::variant<int, double>"
    assert ct.cpp_std == "c++17"
    assert "<variant>" in (ct.required_includes or [])


def test_type_inference_union_with_none_is_optional():
    ct = AggregateType.infer(Optional[float])
    assert ct.name == "std::optional<double>"
    assert ct.cpp_std == "c++17"


def test_type_inference_union_three():
    ct = AggregateType.infer(Union[int, float, bool])
    assert ct.name == "std::variant<int, double, bool>"
    assert "<variant>" in (ct.required_includes or [])


# ---- TypeVar / TemplateParam ------------------------------------------------

def test_type_inference_typevar():
    T = TypingTypeVar("T")
    ct = AggregateType.infer(T)
    assert ct.name == "T"
    assert ct.is_template is True
    assert ct.is_primitive is False


def test_template_param_to_cpp_type():
    tp = TemplateParam("State")
    ct = tp.to_cpp_type()
    assert ct.name == "State"
    assert ct.is_template is True


# ---- C++14 container proxies ------------------------------------------------

def test_cpp_vector_proxy():
    ct = AggregateType.infer(CppVector[int])
    assert ct.name == "std::vector<int>"
    assert "<vector>" in (ct.required_includes or [])


def test_cpp_array_proxy():
    ct = AggregateType.infer(CppArray[float, 3])
    assert ct.name == "std::array<double, 3>"
    assert "<array>" in (ct.required_includes or [])


def test_cpp_array_requires_two_args():
    with pytest.raises(TypeError):
        AggregateType.infer(CppArray[float])


def test_cpp_array_size_must_be_int():
    with pytest.raises(TypeError):
        AggregateType.infer(CppArray[float, 3.0])


def test_cpp_set_proxy():
    ct = AggregateType.infer(CppSet[int])
    assert ct.name == "std::set<int>"
    assert "<set>" in (ct.required_includes or [])


def test_cpp_unordered_set_proxy():
    ct = AggregateType.infer(CppUnorderedSet[str])
    assert ct.name == "std::unordered_set<std::string>"
    assert "<unordered_set>" in (ct.required_includes or [])


def test_cpp_multiset_proxy():
    ct = AggregateType.infer(CppMultiSet[float])
    assert ct.name == "std::multiset<double>"
    assert "<set>" in (ct.required_includes or [])


def test_cpp_map_proxy():
    ct = AggregateType.infer(CppMap[str, int])
    assert ct.name == "std::map<std::string, int>"
    assert "<map>" in (ct.required_includes or [])


def test_cpp_unordered_map_proxy():
    ct = AggregateType.infer(CppUnorderedMap[str, float])
    assert ct.name == "std::unordered_map<std::string, double>"
    assert "<unordered_map>" in (ct.required_includes or [])


def test_cpp_multimap_proxy():
    ct = AggregateType.infer(CppMultiMap[str, int])
    assert ct.name == "std::multimap<std::string, int>"
    assert "<map>" in (ct.required_includes or [])


def test_cpp_pair_proxy():
    ct = AggregateType.infer(CppPair[int, float])
    assert ct.name == "std::pair<int, double>"
    assert "<utility>" in (ct.required_includes or [])


# ---- C++17 proxies ----------------------------------------------------------

def test_cpp_optional_proxy():
    ct = AggregateType.infer(CppOptional[int])
    assert ct.name == "std::optional<int>"
    assert ct.cpp_std == "c++17"
    assert "<optional>" in (ct.required_includes or [])


def test_cpp_variant_proxy():
    ct = AggregateType.infer(CppVariant[int, float, bool])
    assert ct.name == "std::variant<int, double, bool>"
    assert ct.cpp_std == "c++17"
    assert "<variant>" in (ct.required_includes or [])


def test_cpp_variant_requires_two_args():
    with pytest.raises(TypeError):
        AggregateType.infer(CppVariant[int])


def test_cpp_any_direct():
    ct = AggregateType.infer(CppAny)
    assert ct.name == "std::any"
    assert ct.cpp_std == "c++17"
    assert "<any>" in (ct.required_includes or [])


def test_cpp_any_rejects_subscript():
    with pytest.raises(TypeError):
        AggregateType.infer(CppAny[int])


# ---- C++20 proxy ------------------------------------------------------------

def test_cpp_span_proxy():
    ct = AggregateType.infer(CppSpan[float])
    assert ct.name == "std::span<double>"
    assert ct.cpp_std == "c++20"
    assert "<span>" in (ct.required_includes or [])


# ---- C++23 proxies ----------------------------------------------------------

def test_cpp_expected_proxy():
    ct = AggregateType.infer(CppExpected[int, str])
    assert ct.name == "std::expected<int, std::string>"
    assert ct.cpp_std == "c++23"
    assert "<expected>" in (ct.required_includes or [])


def test_cpp_mdspan_proxy():
    ct = AggregateType.infer(CppMdSpan[float])
    assert ct.name == "std::mdspan<double>"
    assert ct.cpp_std == "c++23"
    assert "<mdspan>" in (ct.required_includes or [])


# ---- nested / composed types ------------------------------------------------

def test_nested_optional_in_list():
    ct = AggregateType.infer(list[CppOptional[int]])
    assert "std::vector" in ct.name
    assert "std::optional" in ct.name
    includes = ct.required_includes or []
    assert "<vector>" in includes
    assert "<optional>" in includes


def test_nested_set_in_optional():
    ct = AggregateType.infer(Optional[CppSet[float]])
    assert ct.name == "std::optional<std::set<double>>"
    includes = ct.required_includes or []
    assert "<optional>" in includes
    assert "<set>" in includes


def test_struct_collects_field_includes():
    @dc
    class Payload:
        ids: CppSet[int]
        score: CppOptional[float]

    ct = AggregateType.infer(Payload)
    assert ct.is_struct
    includes = ct.required_includes or []
    assert "<set>" in includes
    assert "<optional>" in includes


# ---- is_container coverage --------------------------------------------------

def test_is_container_all_new_types():
    cases = [
        "std::array<int, 4>",
        "std::set<double>",
        "std::multiset<int>",
        "std::unordered_set<int>",
        "std::multimap<std::string, int>",
        "std::unordered_map<std::string, double>",
        "std::pair<int, double>",
        "std::optional<int>",
        "std::variant<int, double>",
        "std::any",
        "std::span<double>",
        "std::expected<int, std::string>",
        "std::mdspan<float>",
    ]
    for name in cases:
        assert AggregateType.is_container(CppType(name, is_primitive=False)), \
            f"is_container should be True for {name}"
