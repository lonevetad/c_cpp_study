#pragma once

#include "expr_eval/ast/logical/LogicalBinaryNode.hpp"

namespace ExprEval {

class OrNode final : public LogicalBinaryNode<OrNode> {
public:
    using LogicalBinaryNode<OrNode>::LogicalBinaryNode;
    static constexpr bool             kShortCircuitValue = true;
    static constexpr std::string_view kSymbol            = "||";
};

} // namespace ExprEval
