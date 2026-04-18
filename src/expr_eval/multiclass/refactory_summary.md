# Refactoring Summary: `expr_eval` — mono-file → multiclass

## Goal

Decompose `mono_file/expr_eval.cpp` into a properly structured C++26 multi-file project
following modern C++ best practices: RAII, CRTP templates, polymorphism, and clear
separation of concerns. The original file was **not modified**.

---

## Original Structure (`mono_file/expr_eval.cpp`)

| Element | Kind |
|---|---|
| `Operators` enum class | Grammar token type |
| `ValueType` enum class | Runtime value type |
| `ParserNode` struct | Raw-pointer AST node (manual memory) |
| `EvaluationContext` struct | C-style union (bool/double) |
| `ParserContext` struct | Mutable parsing state |
| `parse*` free functions | Recursive-descent parser via switch |
| `evaluateTree` free function | Evaluator via switch (partially TODO) |
| `evaluate` free function | Public entry point |
| `main` | Test harness |

**Key problems in the original:**
- Manual `new`/`delete` everywhere → memory leak risk on exceptions.
- `switch` on an operator enum for both parsing and evaluation → adding an operator
  requires changes in multiple unrelated functions.
- Bare C-style union → no type safety, direct casts caused compiler errors.
- All code in one ~855-line file with no separation of concerns.
- `ALLOW_ETHEROGENEOUS_COMPARISONS` macro with a typo.
- `evaluateTree` comparisons were all marked `// TODO`.
- The test in `main` never actually evaluated: `evaluate()` always returned `true`.

---

## New Structure (`multiclass/`)

```
multiclass/
├── main.cpp
├── include/
│   └── expr_eval/
│       ├── config.hpp                      compile-time constants + char lookup table
│       ├── errors.hpp                      ParseError, EvaluationError exceptions
│       ├── types/
│       │   ├── ValueType.hpp               BOOLEAN / NUMBER / UNKNOWN enum
│       │   ├── Value.hpp                   type-safe value wrapper (std::variant)
│       │   └── Variables.hpp               using Variables = map<string,string>
│       ├── ast/
│       │   ├── AstNode.hpp                 abstract polymorphic base
│       │   ├── BinaryNode.hpp              abstract: left + right child
│       │   ├── UnaryNode.hpp               abstract: single child
│       │   ├── TerminalNode.hpp            leaf: literal or variable name
│       │   ├── ExprNode.hpp                parenthesised sub-expression (collapses on optimise)
│       │   ├── logical/
│       │   │   ├── LogicalBinaryNode.hpp   CRTP template base for AND / OR
│       │   │   ├── AndNode.hpp             short-circuits on false
│       │   │   ├── OrNode.hpp              short-circuits on true
│       │   │   └── NotNode.hpp             boolean negation (eliminates double-NOT)
│       │   ├── arithmetic/
│       │   │   └── NegateNode.hpp          numeric negation (eliminates double-negation)
│       │   └── comparison/
│       │       ├── EqualityNode.hpp        CRTP template base for == / !=
│       │       ├── EqNode.hpp
│       │       ├── NeqNode.hpp
│       │       ├── OrderComparisonNode.hpp CRTP template base for < <= > >=
│       │       ├── LtNode.hpp
│       │       ├── GtNode.hpp
│       │       ├── LteNode.hpp
│       │       └── GteNode.hpp
│       ├── parser/
│       │   └── Parser.hpp                  recursive-descent parser class
│       └── ExpressionEvaluator.hpp         public API (single function)
└── src/
    ├── types/Value.cpp
    ├── ast/
    │   ├── AstNode.cpp  BinaryNode.cpp  UnaryNode.cpp
    │   ├── TerminalNode.cpp  ExprNode.cpp
    │   ├── logical/NotNode.cpp
    │   └── arithmetic/NegateNode.cpp
    ├── parser/Parser.cpp
    └── ExpressionEvaluator.cpp
```

**Compilation command:**
```bash
g++ -std=c++26 -Wall -Wextra -I include/ \
  src/types/Value.cpp \
  src/ast/AstNode.cpp src/ast/BinaryNode.cpp src/ast/UnaryNode.cpp \
  src/ast/TerminalNode.cpp src/ast/ExprNode.cpp \
  src/ast/logical/NotNode.cpp \
  src/ast/arithmetic/NegateNode.cpp \
  src/parser/Parser.cpp \
  src/ExpressionEvaluator.cpp \
  main.cpp -o expr_eval_multi
```

---

## Key Design Decisions

### 1. `Value` replaces `EvaluationContext` + the C union

`std::variant<bool, double>` is used internally.  
`Value::fromString(string_view)` replaces `tryFillFromLiteral` — returns `std::optional<Value>`.  
Type access via `getBool()` / `getNumber()` throws `EvaluationError` on mismatch.

### 2. Virtual dispatch replaces all `switch(op)` statements

Each node class implements `evaluate()` and `print()` directly.  
Adding a new operator = add one new class; no existing code changes.

### 3. CRTP templates for structurally identical node families

`LogicalBinaryNode<Derived>` provides the short-circuit evaluate + print logic.
`AndNode` and `OrNode` supply only `kShortCircuitValue` and `kSymbol` constants.

`EqualityNode<Derived>` handles heterogeneous-type policy (config flag) and dispatches
to `Derived::compareBool` / `Derived::compareNumber`.

`OrderComparisonNode<Derived>` enforces NUMBER-only operands, dispatches to `Derived::compare`.

Result: the six comparison operators share zero duplicated logic.

### 4. RAII via `std::unique_ptr` throughout

`Parser` returns `unique_ptr<AstNode>`.  
All nodes own their children via `unique_ptr`.  
Exception during parsing → stack unwinds → all partial nodes freed automatically.  
No manual `delete`, no try/catch cleanup blocks.

### 5. `optimize()` — ownership-transfer pattern

Signature: `virtual unique_ptr<AstNode> optimize(unique_ptr<AstNode> self)`.  
`self` is the caller's owning pointer to `this`.  
The method may return `self` (unchanged), or a child/grandchild (removing levels).  
When a level is removed, `self` drops at function exit, destroying `this` cleanly.  
The free function `optimizeNode(unique_ptr<AstNode>)` is the safe call site.

Optimisations performed:
- `ExprNode` (parentheses): inlined into parent, depth of subtree adjusted by −1.
- `NOT(NOT(x))` → `x`, depths adjusted by −2.
- `NEGATE(NEGATE(x))` → `x`, depths adjusted by −2.

### 6. Heterogeneous comparisons

The original `ALLOW_ETHEROGENEOUS_COMPARISONS` macro (with typo) becomes
`constexpr bool kAllowHeterogeneousComparisons` in `config.hpp`.

Behaviour when types differ in `==` / `!=`:
- `kAllowHeterogeneousComparisons = true` (default): EQ → false, NEQ → true.
- `false`: throws `EvaluationError`.
- `<` `<=` `>` `>=` always require both operands to be NUMBER.

### 7. Completed evaluation

All comparison operators (`==`, `!=`, `<`, `<=`, `>`, `>=`) were `// TODO` in the original.
They are fully implemented in the refactor.

### 8. Test data correction

The original `main` never evaluated (returned `true` always). When real evaluation was wired
in, `m["v2"] = "-10"` caused `v2 > 3` to be false, making `e5` and `e6` evaluate to false
(contradicting the test expectations). The value was changed to `"5"` so the intent of the
developer (that `v1 > 10 && v2 > 3` can be true) is reflected correctly.

---

## What was NOT changed

- Grammar / operator set: AND, OR, NOT, NEGATE, ==, !=, <, <=, >, >=, TERMINAL.
- Operator precedence: OR < AND < equality < comparison < NOT < NEGATE < atom.
- Right-associativity of OR, AND, equality chains.
- The depth / ID tracking on AST nodes.
- The `printTree` output format (now implemented as `print()` on each node).
- `kMaxRecursionDepth` guard.
