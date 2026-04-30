// Explicit specializations of fcpp::vec<N> (N=1,2,3) that restore
// element-wise construction.
//
// C++17: user-declared *defaulted* constructors still allowed aggregate init.
// C++20+: any user-declared constructor disqualifies a class as aggregate →
//         vec<N>{a, b, c} fails.  fcpp's own headers (sequence.hpp, make_vec,
//         gps_trace.hpp) rely on this pattern throughout.
//
// Fix: provide explicit specializations with matching constructors.
// Include this header BEFORE any other fcpp header in TUs compiled with
// -std=c++20 or later.
//
// ODR note: include this in EVERY TU that uses fcpp::vec so all translation
// units see identical class definitions.

#pragma once

#include "lib/data/vec.hpp"   // primary template + all free operators

namespace fcpp {

// ── vec<1> ────────────────────────────────────────────────────────────────
template <>
struct vec<1> {
    constexpr static size_t dimension = 1;

    vec()              = default;
    vec(vec<1> const&) = default;
    vec(vec<1>&&)      = default;
    vec<1>& operator=(vec<1> const&) & = default;
    vec<1>& operator=(vec<1>&&)      & = default;

    constexpr explicit vec(real_t a) noexcept : data{a} {}

    real_t*       begin()       noexcept { return data; }
    real_t const* begin() const noexcept { return data; }
    real_t*       end()         noexcept { return data + 1; }
    real_t const* end()   const noexcept { return data + 1; }

    real_t& operator[](size_t i)       { return data[i]; }
    real_t  operator[](size_t i) const { return data[i]; }

    template <typename S> S& serialize(S& s)       { return s & data; }
    template <typename S> S& serialize(S& s) const { return s << data; }

    real_t data[1];
};

// ── vec<2> ────────────────────────────────────────────────────────────────
template <>
struct vec<2> {
    constexpr static size_t dimension = 2;

    vec()              = default;
    vec(vec<2> const&) = default;
    vec(vec<2>&&)      = default;
    vec<2>& operator=(vec<2> const&) & = default;
    vec<2>& operator=(vec<2>&&)      & = default;

    constexpr vec(real_t a, real_t b) noexcept : data{a, b} {}

    real_t*       begin()       noexcept { return data; }
    real_t const* begin() const noexcept { return data; }
    real_t*       end()         noexcept { return data + 2; }
    real_t const* end()   const noexcept { return data + 2; }

    real_t& operator[](size_t i)       { return data[i]; }
    real_t  operator[](size_t i) const { return data[i]; }

    template <typename S> S& serialize(S& s)       { return s & data; }
    template <typename S> S& serialize(S& s) const { return s << data; }

    real_t data[2];
};

// ── vec<3> ────────────────────────────────────────────────────────────────
template <>
struct vec<3> {
    constexpr static size_t dimension = 3;

    vec()              = default;
    vec(vec<3> const&) = default;
    vec(vec<3>&&)      = default;
    vec<3>& operator=(vec<3> const&) & = default;
    vec<3>& operator=(vec<3>&&)      & = default;

    constexpr vec(real_t a, real_t b, real_t c) noexcept : data{a, b, c} {}

    real_t*       begin()       noexcept { return data; }
    real_t const* begin() const noexcept { return data; }
    real_t*       end()         noexcept { return data + 3; }
    real_t const* end()   const noexcept { return data + 3; }

    real_t& operator[](size_t i)       { return data[i]; }
    real_t  operator[](size_t i) const { return data[i]; }

    template <typename S> S& serialize(S& s)       { return s & data; }
    template <typename S> S& serialize(S& s) const { return s << data; }

    real_t data[3];
};

} // namespace fcpp
