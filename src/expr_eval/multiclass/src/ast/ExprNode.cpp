#include "expr_eval/ast/ExprNode.hpp"

namespace ExprEval {

Value ExprNode::evaluate(const Variables& vars) const {
    return child_->evaluate(vars);
}

void ExprNode::print(std::ostream& out) const {
    printTabs(out, depth);
    out << "( (d.: " << depth << " ; ID: " << id << ")\n";
    if (child_) child_->print(out);
    printTabs(out, depth);
    out << ")\n";
}

std::unique_ptr<AstNode> ExprNode::optimize(std::unique_ptr<AstNode> self) {
    child_ = optimizeNode(std::move(child_));
    if (!child_) return self;
    // Collapse: remove the EXPR wrapper — child steps up one level.
    child_->adjustDepthRecursive(-1);
    auto inlined = std::move(child_);
    return optimizeNode(std::move(inlined));
}

} // namespace ExprEval
