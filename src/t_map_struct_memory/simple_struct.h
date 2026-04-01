#pragma once
#include <cstdint>
#include <sstream>
#include <string>

/**
 * A minimal value-type struct to be stored by value inside map nodes.
 *
 * Memory notes:
 *   - No dynamic allocation is performed by Point itself.
 *   - When stored in std::map, the Point object lives inline inside the
 *     tree node that std::allocator places on the heap — no extra pointer
 *     or indirection is involved.
 *   - The trivial destructor means no cleanup cost at erasure time.
 */
struct Point {
    int32_t x{ 0 };
    int32_t y{ 0 };

    /** Returns a compact, human-readable representation. */
    std::string to_string() const {
        std::ostringstream oss;
        oss << "{ x: " << x << ", y: " << y << " }";
        return oss.str();
    }
};
