#pragma once
#include <cstdint>
#include <sstream>
#include <string>

/**
 * A struct designed for dynamic allocation — always created with 'new' and
 * stored in std::map as a raw Point2* pointer.
 *
 * This is the heap-allocated counterpart to Point (simple_struct.h), which
 * is stored by value inside map nodes. The two types are structurally
 * identical (same fields, same to_string()) but differ in their intended
 * ownership and allocation model:
 *
 *   Point   — value type; sits inline inside the tree node; RAII-safe.
 *   Point2  — pointer type; lives in a separate heap block; requires explicit
 *             delete before or after erasing the map entry.
 *
 * The non-copyable constraint enforces pointer semantics: you cannot
 * accidentally copy a Point2 into a local variable and end up with two
 * objects that both think they own the same data. Only move is permitted
 * (analogous to Person in simple_class.h).
 *
 * Memory notes:
 *   - Point2 itself performs no internal dynamic allocation (no std::string
 *     members), so every entry in a map<K, Point2*> involves exactly two
 *     heap blocks: the tree node and the Point2 object.
 *   - The map destructor frees tree nodes but does NOT follow Point2*
 *     pointers. Explicit delete is mandatory to avoid memory leaks.
 */
struct Point2 {
    int32_t x{ 0 };
    int32_t y{ 0 };

    Point2() = default;
    Point2(int32_t x_, int32_t y_) : x(x_), y(y_) {}

    ~Point2() = default;

    // Non-copyable: enforces explicit ownership via raw pointer in maps.
    Point2(const Point2&)            = delete;
    Point2& operator=(const Point2&) = delete;

    // Movable (symmetry with Person; not required by the map examples).
    Point2(Point2&&)            = default;
    Point2& operator=(Point2&&) = default;

    /** Returns a compact, human-readable representation. */
    std::string to_string() const {
        std::ostringstream oss;
        oss << "{ x: " << x << ", y: " << y << " }";
        return oss.str();
    }
};
