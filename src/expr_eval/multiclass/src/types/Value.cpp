#include "expr_eval/types/Value.hpp"
#include "expr_eval/errors.hpp"

#include <string>

namespace ExprEval {

std::optional<Value> Value::fromString(std::string_view s) {
    if (s == "true")  return Value{true};
    if (s == "false") return Value{false};
    std::string str{s};
    std::size_t pos{};
    try {
        double num = std::stod(str, &pos);
        if (pos == str.size()) return Value{num};
    } catch (...) {}
    return std::nullopt;
}

ValueType Value::type() const noexcept {
    if (std::holds_alternative<bool>(data_))   return ValueType::BOOLEAN;
    if (std::holds_alternative<double>(data_)) return ValueType::NUMBER;
    return ValueType::UNKNOWN;
}

bool Value::getBool() const {
    if (!std::holds_alternative<bool>(data_))
        throw EvaluationError("Value is not BOOLEAN");
    return std::get<bool>(data_);
}

double Value::getNumber() const {
    if (!std::holds_alternative<double>(data_))
        throw EvaluationError("Value is not NUMBER");
    return std::get<double>(data_);
}

std::ostream& operator<<(std::ostream& os, const Value& v) {
    if (std::holds_alternative<bool>(v.data_))
        os << (std::get<bool>(v.data_) ? "true" : "false");
    else
        os << std::get<double>(v.data_);
    return os;
}

} // namespace ExprEval
