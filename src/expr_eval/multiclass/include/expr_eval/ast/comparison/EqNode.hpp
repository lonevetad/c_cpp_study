#pragma once

#include "expr_eval/ast/comparison/EqualityNode.hpp"

namespace ExprEval {

class EqNode final : public EqualityNode<EqNode> {
public:
    using EqualityNode<EqNode>::EqualityNode;
    static constexpr std::string_view kSymbol              = "==";
    static constexpr bool             kHeterogeneousResult = false;
    static bool compareBool(bool l, bool r)     { return l == r; }
    static bool compareNumber(double l, double r) { return l == r; }
};

} // namespace ExprEval
