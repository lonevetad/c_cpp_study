#include <cstdint>
#include <cstring>
#include <type_traits>

#include "vec_vararg.hpp"

static_assert(std::is_same_v<fcpp::real_t, double>,
    "Bridge requires fcpp::real_t == double; compile without custom FCPP_REAL_TYPE");
static_assert(sizeof(fcpp::vec<2>) == 2 * sizeof(double));
static_assert(sizeof(fcpp::vec<3>) == 3 * sizeof(double));

template <size_t N>
static fcpp::vec<N> load(const double* p) noexcept {
    fcpp::vec<N> v;
    std::memcpy(v.data, p, N * sizeof(double));
    return v;
}

template <size_t N>
static void store(const fcpp::vec<N>& v, double* out) noexcept {
    std::memcpy(out, v.data, N * sizeof(double));
}

extern "C" {

const char* fcpp_py_version() { return "1.0.0"; }

// ── Vec2 ──────────────────────────────────────────────────────────────

double fcpp_vec2_norm    (const double* v)                   { return fcpp::norm(load<2>(v)); }
double fcpp_vec2_distance(const double* a, const double* b)  { return fcpp::distance(load<2>(a), load<2>(b)); }
double fcpp_vec2_dot     (const double* a, const double* b)  { return load<2>(a) * load<2>(b); }

void fcpp_vec2_add (const double* a, const double* b, double* o) { store<2>(load<2>(a) + load<2>(b), o); }
void fcpp_vec2_sub (const double* a, const double* b, double* o) { store<2>(load<2>(a) - load<2>(b), o); }
void fcpp_vec2_mul (const double* a, double s,         double* o) { store<2>(load<2>(a) * s,          o); }
void fcpp_vec2_div (const double* a, double s,         double* o) { store<2>(load<2>(a) / s,          o); }
void fcpp_vec2_neg (const double* a,                   double* o) { store<2>(-load<2>(a),              o); }
void fcpp_vec2_unit(const double* a,                   double* o) { store<2>(fcpp::unit(load<2>(a)),   o); }

int32_t fcpp_vec2_eq(const double* a, const double* b) { return load<2>(a) == load<2>(b) ? 1 : 0; }

// ── Vec3 ──────────────────────────────────────────────────────────────

double fcpp_vec3_norm    (const double* v)                   { return fcpp::norm(load<3>(v)); }
double fcpp_vec3_distance(const double* a, const double* b)  { return fcpp::distance(load<3>(a), load<3>(b)); }
double fcpp_vec3_dot     (const double* a, const double* b)  { return load<3>(a) * load<3>(b); }

void fcpp_vec3_add (const double* a, const double* b, double* o) { store<3>(load<3>(a) + load<3>(b), o); }
void fcpp_vec3_sub (const double* a, const double* b, double* o) { store<3>(load<3>(a) - load<3>(b), o); }
void fcpp_vec3_mul (const double* a, double s,         double* o) { store<3>(load<3>(a) * s,          o); }
void fcpp_vec3_div (const double* a, double s,         double* o) { store<3>(load<3>(a) / s,          o); }
void fcpp_vec3_neg (const double* a,                   double* o) { store<3>(-load<3>(a),              o); }
void fcpp_vec3_unit(const double* a,                   double* o) { store<3>(fcpp::unit(load<3>(a)),   o); }

int32_t fcpp_vec3_eq(const double* a, const double* b) { return load<3>(a) == load<3>(b) ? 1 : 0; }

} // extern "C"
