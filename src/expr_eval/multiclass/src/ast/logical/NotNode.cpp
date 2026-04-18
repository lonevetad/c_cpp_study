#include "expr_eval/ast/logical/NotNode.hpp"
#include "expr_eval/errors.hpp"
#include "expr_eval/types/ValueType.hpp"

#include <format>

namespace ExprEval {

Value NotNode::evaluate(const Variables& vars) const {
    Value v = child_->evaluate(vars);
    if (v.type() != ValueType::BOOLEAN)
        throw EvaluationError(
            std::format("Node (ID: {}) NOT expects BOOLEAN operand", id));
    return Value{!v.getBool()};
}

void NotNode::print(std::ostream& out) const {
    printTabs(out, depth);
    out << "! (d.: " << depth << " ; ID: " << id << ")\n";
    if (child_) child_->print(out);
}

std::unique_ptr<AstNode> NotNode::optimize(std::unique_ptr<AstNode> self) {
    child_ = optimizeNode(std::move(child_));
    if (auto* inner = dynamic_cast<NotNode*>(child_.get())) {
        // NOT(NOT(x)) = x — remove two levels, promote grandchild
        auto grandchild = std::move(inner->child_);
        grandchild->adjustDepthRecursive(-2);
        return optimizeNode(std::move(grandchild));
    }
    return self;
}

} // namespace ExprEval
