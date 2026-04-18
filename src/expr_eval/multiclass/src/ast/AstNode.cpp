#include "expr_eval/ast/AstNode.hpp"

namespace ExprEval {

std::unique_ptr<AstNode> optimizeNode(std::unique_ptr<AstNode> node) {
    if (!node) return nullptr;
    return node->optimize(std::move(node));
}

} // namespace ExprEval
