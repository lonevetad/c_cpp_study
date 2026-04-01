#pragma once
#include <cstdint>
#include <map>
#include <ostream>
#include <sstream>
#include <string>

#include "simple_class.h"
#include "simple_struct.h"

// =============================================================================
//  display() overloads
//
//  Each overload converts one concrete key/value type to a printable string.
//
//  C++ overload resolution always prefers a non-template function over a
//  function-template instantiation when both are equally good matches, so
//  the specialised non-template overloads below take priority over the
//  generic fallback template for all types they cover.
// =============================================================================

/** Generic fallback: works for any type that supports operator<<. */
template<typename T>
std::string display(const T& v) {
    std::ostringstream oss;
    oss << v;
    return oss.str();
}

/** int32_t — plain decimal, no quotes. */
inline std::string display(int32_t v) {
    return std::to_string(v);
}

/** std::string key or value — surrounded by double quotes. */
inline std::string display(const std::string& v) {
    return '"' + v + '"';
}

/**
 * Heap-allocated std::string* — dereferenced and quoted.
 * A null pointer is rendered as the literal token  null.
 */
inline std::string display(const std::string* v) {
    return v ? ('"' + *v + '"') : "null";
}

/** Point struct — delegates to Point::to_string(). */
inline std::string display(const Point& v) {
    return v.to_string();
}

/**
 * Heap-allocated Person* — delegates to Person::to_string().
 * A null pointer is rendered as the literal token  null.
 */
inline std::string display(const Person* v) {
    return v ? v->to_string() : "null";
}

// =============================================================================
//  print_map()
//
//  Serialises a std::map to an ostream using a 4-space-indented JSON-like
//  object format:
//
//      {
//          key1: value1,
//          key2: value2
//      }
//
//  Keys and values are converted via the display() overloads above, so
//  strings receive surrounding quotes automatically while numeric types and
//  structs/classes use their own textual representation.
// =============================================================================
template<typename K, typename V>
void print_map(const std::map<K, V>& m, std::ostream& out) {
    out << "{\n";
    const std::size_t total = m.size();
    std::size_t       i     = 0;
    for (const auto& [k, v] : m) {
        out << "    " << display(k) << ": " << display(v);
        if (++i < total)
            out << ',';
        out << '\n';
    }
    out << '}';
}
