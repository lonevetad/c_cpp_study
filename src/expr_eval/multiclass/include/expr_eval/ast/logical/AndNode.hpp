#pragma once

#include "expr_eval/ast/logical/LogicalBinaryNode.hpp"

namespace ExprEval {

class AndNode final : public LogicalBinaryNode<AndNode> {
public:
    using LogicalBinaryNode<AndNode>::LogicalBinaryNode;
    static constexpr bool             kShortCircuitValue = false;
    static constexpr std::string_view kSymbol            = "&&";
};

} // namespace ExprEval
