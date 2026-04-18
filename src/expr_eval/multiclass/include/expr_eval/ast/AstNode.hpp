#pragma once

#include "expr_eval/types/Value.hpp"
#include "expr_eval/types/Variables.hpp"

#include <memory>
#include <ostream>

namespace ExprEval {

class AstNode {
public:
    int id{};
    int depth{};

    virtual ~AstNode() = default;

    AstNode(const AstNode&)            = delete;
    AstNode& operator=(const AstNode&) = delete;
    AstNode(AstNode&&)                 = default;
    AstNode& operator=(AstNode&&)      = default;

    [[nodiscard]] virtual Value evaluate(const Variables& vars) const = 0;
    virtual void print(std::ostream& out) const = 0;

    // Returns optimized replacement for this node (may return self or a child).
    // Caller passes ownership via `self`; the method returns the new owner.
    [[nodiscard]] virtual std::unique_ptr<AstNode> optimize(std::unique_ptr<AstNode> self) = 0;

    virtual void adjustDepthRecursive(int delta) noexcept { depth += delta; }

protected:
    AstNode() = default;
};

// Free function: calls node->optimize(move(node)). Safe to use on any node.
[[nodiscard]] std::unique_ptr<AstNode> optimizeNode(std::unique_ptr<AstNode> node);

inline void printTabs(std::ostream& out, int d) {
    for (int i = 0; i < d; ++i) out << "  ";
}

} // namespace ExprEval
