#include "expr_eval/ast/BinaryNode.hpp"

namespace ExprEval {

std::unique_ptr<AstNode> BinaryNode::optimize(std::unique_ptr<AstNode> self) {
    left_  = optimizeNode(std::move(left_));
    right_ = optimizeNode(std::move(right_));
    return self;
}

void BinaryNode::printBinary(std::ostream& out, std::string_view symbol) const {
    if (left_)  left_->print(out);
    printTabs(out, depth);
    out << symbol << " (d.: " << depth << " ; ID: " << id << ")\n";
    if (right_) right_->print(out);
}

} // namespace ExprEval
