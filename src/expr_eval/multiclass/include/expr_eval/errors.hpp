#pragma once

#include <stdexcept>
#include <string>

namespace ExprEval {

class ParseError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

class EvaluationError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

} // namespace ExprEval
