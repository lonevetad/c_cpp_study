#pragma once

#include "expr_eval/types/ValueType.hpp"

#include <optional>
#include <ostream>
#include <string_view>
#include <variant>

namespace ExprEval {

class Value {
public:
    explicit Value(bool b) noexcept : data_{b} {}
    explicit Value(double d) noexcept : data_{d} {}

    [[nodiscard]] static std::optional<Value> fromString(std::string_view s);

    [[nodiscard]] ValueType type() const noexcept;
    [[nodiscard]] bool getBool() const;
    [[nodiscard]] double getNumber() const;

    friend std::ostream& operator<<(std::ostream& os, const Value& v);

private:
    std::variant<bool, double> data_;
};

} // namespace ExprEval
