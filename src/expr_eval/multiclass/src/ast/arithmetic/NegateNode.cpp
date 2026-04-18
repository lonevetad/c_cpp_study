#include "expr_eval/ast/arithmetic/NegateNode.hpp"
#include "expr_eval/errors.hpp"
#include "expr_eval/types/ValueType.hpp"

#include <format>

namespace ExprEval {

Value NegateNode::evaluate(const Variables& vars) const {
    Value v = child_->evaluate(vars);
    if (v.type() != ValueType::NUMBER)
        throw EvaluationError(
            std::format("Node (ID: {}) NEGATE expects NUMBER operand", id));
    return Value{-v.getNumber()};
}

void NegateNode::print(std::ostream& out) const {
    printTabs(out, depth);
    out << "- (d.: " << depth << " ; ID: " << id << ")\n";
    if (child_) child_->print(out);
}

std::unique_ptr<AstNode> NegateNode::optimize(std::unique_ptr<AstNode> self) {
    child_ = optimizeNode(std::move(child_));
    if (auto* inner = dynamic_cast<NegateNode*>(child_.get())) {
        // -(-(x)) = x — remove two levels, promote grandchild
        auto grandchild = std::move(inner->child_);
        grandchild->adjustDepthRecursive(-2);
        return optimizeNode(std::move(grandchild));
    }
    return self;
}

} // namespace ExprEval
