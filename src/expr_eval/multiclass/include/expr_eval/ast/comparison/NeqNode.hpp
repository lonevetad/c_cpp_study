#pragma once

#include "expr_eval/ast/comparison/EqualityNode.hpp"

namespace ExprEval {

class NeqNode final : public EqualityNode<NeqNode> {
public:
    using EqualityNode<NeqNode>::EqualityNode;
    static constexpr std::string_view kSymbol              = "!=";
    static constexpr bool             kHeterogeneousResult = true;
    static bool compareBool(bool l, bool r)     { return l != r; }
    static bool compareNumber(double l, double r) { return l != r; }
};

} // namespace ExprEval
