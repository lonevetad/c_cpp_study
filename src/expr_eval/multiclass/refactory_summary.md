# Refactoring Summary: `expr_eval` — mono-file → multiclass

## Goal

Decompose `mono_file/expr_eval.cpp` into a properly structured C++26 multi-file project
following modern C++ best practices: RAII, CRTP templates, polymorphism, and clear
separation of concerns. The original file was **not modified**.

---

## Original Structure (`mono_file/expr_eval.cpp`)

| Element                      | Kind                                  |
| ---------------------------- | ------------------------------------- |
| `Operators` enum class       | Grammar token type                    |
| `ValueType` enum class       | Runtime value type                    |
| `ParserNode` struct          | Raw-pointer AST node (manual memory)  |
| `EvaluationContext` struct   | C-style union (bool/double)           |
| `ParserContext` struct       | Mutable parsing state                 |
| `parse*` free functions      | Recursive-descent parser via switch   |
| `evaluateTree` free function | Evaluator via switch (partially TODO) |
| `evaluate` free function     | Public entry point                    |
| `main`                       | Test harness                          |

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
├── Makefile
├── test/
│   └── test_expr_eval.cpp          self-contained unit tests (no external framework)
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

**Build commands (via Makefile):**

```bash
make          # compile demo  → build/expr_eval_multi.exe
make test     # compile + run → build/expr_eval_test.exe
make clean    # remove build/
```

**Manual compilation (without make):**

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

## Quick Start — step-by-step commands

Open a terminal (MSYS2 UCRT64 shell) in the `multiclass/` directory, then run each
command in order. Every command redirects both stdout and stderr (`2>&1`) to a text
file so you can inspect the output later with any editor.

> **Note:** the `make` executable on this machine is `mingw32-make`.  
> Substitute `make` if yours is on PATH.

```bash
# 1. Compile the demo program (main.cpp + all library sources).
#    Compiler messages go to build_log.txt.
mingw32-make all > build_log.txt 2>&1

# 2. Compile the test executable (reuses the .o files from step 1).
#    Appended to the same build_log.txt so all compilation output is together.
mingw32-make build/expr_eval_test.exe >> build_log.txt 2>&1

# 3. Run the unit tests.
#    PASS/FAIL lines and the final summary go to test_output.txt.
./build/expr_eval_test.exe > test_output.txt 2>&1

# 4. Run the demo (main.cpp).
#    Parsed tree and "Good job!" / "Uhm, please retry!" go to main_output.txt.
./build/expr_eval_multi.exe > main_output.txt 2>&1
```

After running, you have three log files:

| File              | Contents                                               |
| ----------------- | ------------------------------------------------------ |
| `build_log.txt`   | Compiler invocations (or errors if something is wrong) |
| `test_output.txt` | 75 PASS/FAIL lines + summary line                      |
| `main_output.txt` | Parsed AST trees for e1-e7 + "Good job!"               |

To rebuild from scratch (clean slate):

```bash
# Remove all generated files, then redo steps 1-4.
mingw32-make clean > build_log.txt 2>&1
mingw32-make all  >> build_log.txt 2>&1
mingw32-make build/expr_eval_test.exe >> build_log.txt 2>&1
./build/expr_eval_test.exe  > test_output.txt 2>&1
./build/expr_eval_multi.exe > main_output.txt 2>&1
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

---

## Build System (`Makefile`)

`Makefile` sits at `multiclass/` root. Key design points:

- **`BUILD_DIR := build/`** — all artefacts (`.o`, `.d`, `.exe`) go under `build/`; source tree stays clean.
- **Incremental builds** — `-MMD -MP` generates a `.d` dependency file alongside each `.o`; Make `-include`s them so header changes trigger the correct recompiles.
- **Shared library objects** — `LIB_OBJS` is compiled once and linked into both `expr_eval_multi.exe` and `expr_eval_test.exe`.
- **Pattern rule** — `$(BUILD_DIR)/%.o: %.cpp` with `@mkdir -p $(dir $@)` creates output directories on demand; no manual `mkdir` calls elsewhere.
- **`make test`** — builds the test executable then runs it; Make propagates a non-zero exit code as a build failure.
- **`make clean`** — `rm -rf build/` removes everything generated.

---

## Test Suite (`test/test_expr_eval.cpp`)

No external test framework — a minimal `check()` helper + two macros (`EXPECT_TRUE`, `EXPECT_FALSE`, `EXPECT_THROW`) keep the file self-contained.

`eval()` wrapper redirects `std::cout` to a sink during `ExprEval::evaluate()` calls so that parse-tree output does not obscure PASS/FAIL lines; exceptions are re-thrown correctly.

| Section                | What is tested                                                                                 |
| ---------------------- | ---------------------------------------------------------------------------------------------- |
| Literals               | `"true"` / `"false"` at root                                                                   |
| Variable lookup        | Variable resolves to bool via `Value::fromString`                                              |
| Equality `== / !=`     | Numbers, booleans, heterogeneous types                                                         |
| Numeric comparisons    | All four operators, boundary values, negative numbers                                          |
| Logical AND            | Truth table + false short-circuit (RHS skipped)                                                |
| Logical OR             | Truth table + true short-circuit (RHS skipped)                                                 |
| NOT / double-NOT       | `!`, `!!`, `!!!`; double-NOT optimization verified                                             |
| NEGATE / double-NEGATE | `-`, `--` collapse; sign of result verified                                                    |
| Parentheses            | Single and nested; `ExprNode` collapse is transparent                                          |
| Complex                | All six expressions from `main.cpp` (e1-e7)                                                    |
| `ParseError`           | Empty string, unclosed paren, trailing operators, bare `!`/`-`                                 |
| `EvaluationError`      | Bare number at root, unknown variable, non-literal variable, type mismatches in `>`, `&&`, `-` |

**Short-circuit tests** confirm that `false && <unknown>` and `true || <unknown>` return the correct value without throwing, proving the short-circuit implementation skips RHS evaluation.

---

## What was NOT changed

- Grammar / operator set: AND, OR, NOT, NEGATE, ==, !=, <, <=, >, >=, TERMINAL.
- Operator precedence: OR < AND < equality < comparison < NOT < NEGATE < atom.
- Right-associativity of OR, AND, equality chains.
- The depth / ID tracking on AST nodes.
- The `printTree` output format (now implemented as `print()` on each node).
- `kMaxRecursionDepth` guard.
