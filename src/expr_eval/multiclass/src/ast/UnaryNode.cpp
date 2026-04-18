#include "expr_eval/ast/UnaryNode.hpp"

namespace ExprEval {

std::unique_ptr<AstNode> UnaryNode::optimize(std::unique_ptr<AstNode> self) {
    child_ = optimizeNode(std::move(child_));
    return self;
}

} // namespace ExprEval
