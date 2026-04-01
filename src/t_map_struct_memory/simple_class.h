#pragma once
#include <cstdint>
#include <sstream>
#include <string>
#include <utility>

/**
 * A minimal class used as a heap-allocated map value (stored as Person*).
 *
 * Memory notes:
 *   - Every Person instance is created with 'new' and must be 'delete'd by
 *     the owning code. std::map stores the raw pointer only — it will NOT
 *     free the pointee when a node is erased or when the map is destroyed.
 *   - The name_ member (std::string) may itself perform an internal heap
 *     allocation when the name exceeds the Small String Optimisation (SSO)
 *     buffer (typically 15 chars on most standard-library implementations).
 *   - Person is intentionally non-copyable: only pointer (or move) semantics
 *     are allowed, mirroring the ownership model used in the examples.
 */
class Person {
public:
    Person() = default;

    Person(std::string name, int32_t age)
        : name_(std::move(name)), age_(age) {}

    ~Person() = default;

    // Non-copyable: enforces explicit ownership via raw pointer in maps.
    Person(const Person&)            = delete;
    Person& operator=(const Person&) = delete;

    // Movable (used internally, not needed by the map examples).
    Person(Person&&)            = default;
    Person& operator=(Person&&) = default;

    const std::string& name() const { return name_; }
    int32_t            age()  const { return age_;  }

    /** Returns a compact, human-readable representation. */
    std::string to_string() const {
        std::ostringstream oss;
        oss << "{ name: \"" << name_ << "\", age: " << age_ << " }";
        return oss.str();
    }

private:
    std::string name_;
    int32_t     age_{ 0 };
};
