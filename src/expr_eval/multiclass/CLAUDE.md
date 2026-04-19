# CLAUDE.md — expr_eval multiclass project

## What this project is

C++26 refactor of `../mono_file/expr_eval.cpp` (855 lines, single file) into a
multi-file, multi-class project.  The original file **must never be modified**.

Full design rationale: `refactory_summary.md` (same directory).

---

## Environment

### Windows 11 (MSYS2 UCRT64)
- Compiler: GCC 15.2.0 (MSYS2 UCRT64)
- Standard: C++26
- Make: `mingw32-make` (`make` is not on PATH in MSYS2 — always use `mingw32-make`)
- Shell: MSYS2 bash (Unix paths, forward slashes)

### Linux (Mint / Ubuntu)
- Compiler: GCC **≥ 15** required for `-std=c++26`; on Ubuntu 24.04 install via `sudo add-apt-repository ppa:ubuntu-toolchain-r/test && sudo apt install g++-15`
- Make: `make`
- Shell: bash

---

## Build

```bash
# Windows (MSYS2 bash) — from multiclass/ directory:
mingw32-make all             # → build/expr_eval_multi.exe  (demo)
mingw32-make test            # → build/expr_eval_test.exe   (compile + run)
mingw32-make clean           # rm -rf build/

# Linux — from multiclass/ directory:
make all                     # → build/expr_eval_multi  (demo)
make test                    # → build/expr_eval_test   (compile + run)
make clean                   # rm -rf build/
```

All `.o`, `.d`, and executable files go under `build/`; source tree is never written to.
`-MMD -MP` generates `.d` dependency files → headers tracked automatically.
Executables have `.exe` extension on Windows; no extension on Linux.

---

## Source layout

```
include/expr_eval/
  config.hpp            kMaxRecursionDepth, kAllowHeterogeneousComparisons,
                        kUnallowedCharsTerminal (constexpr lookup table)
  errors.hpp            ParseError, EvaluationError (both : std::runtime_error)
  types/
    ValueType.hpp       enum class { UNKNOWN, BOOLEAN, NUMBER }
    Value.hpp/cpp       std::variant<bool,double> wrapper; fromString() → optional<Value>
    Variables.hpp       using Variables = std::map<std::string,std::string>
  ast/
    AstNode.hpp/cpp     abstract base; optimizeNode() free function declared here
    BinaryNode.hpp/cpp  abstract; owns left_/right_ unique_ptr; optimize() recurses
    UnaryNode.hpp/cpp   abstract; owns child_ unique_ptr; optimize() recurses
    TerminalNode.hpp/cpp  leaf; evaluate() tries literal parse, then variable lookup
    ExprNode.hpp/cpp    parentheses wrapper; optimize() collapses self → child
    logical/
      LogicalBinaryNode.hpp   CRTP template; short-circuit evaluate + print
      AndNode.hpp             kShortCircuitValue=false, kSymbol="&&"
      OrNode.hpp              kShortCircuitValue=true,  kSymbol="||"
      NotNode.hpp/cpp         double-NOT elimination in optimize()
    arithmetic/
      NegateNode.hpp/cpp      double-NEGATE elimination in optimize()
    comparison/
      EqualityNode.hpp        CRTP template for == / !=; hetero policy via config flag
      EqNode.hpp              kHeterogeneousResult=false
      NeqNode.hpp             kHeterogeneousResult=true
      OrderComparisonNode.hpp CRTP template for < <= > >=; NUMBER-only enforcement
      LtNode/GtNode/LteNode/GteNode.hpp   each provides kSymbol + compare(double,double)
  parser/
    Parser.hpp/cpp      recursive-descent; returns unique_ptr<AstNode>; no manual delete
  ExpressionEvaluator.hpp/cpp   public API: evaluate(string_view, Variables) → bool

src/           mirrors include/ structure; .cpp files for non-template classes
test/
  test_expr_eval.cpp    75 self-contained unit tests; no external framework
main.cpp                demo: 7 expressions, variables v0–v5, expects "Good job!"
Makefile
refactory_summary.md
```

---

## Critical design patterns

### optimize() — ownership-transfer
```cpp
virtual unique_ptr<AstNode> optimize(unique_ptr<AstNode> self);
```
`self` is the caller's owning pointer to `this`.  Method returns either `self`
(no change) or a descendant (node removes itself).  When it returns a descendant,
`self` drops at function exit → `this` is destroyed cleanly.

**Safe call site only:** `optimizeNode(unique_ptr<AstNode>)` (declared in AstNode.hpp,
defined in AstNode.cpp).  Never call `node->optimize(node)` directly — move semantics
invalidate `node` before the call.

### CRTP node families
- `LogicalBinaryNode<Derived>` — AND/OR share all logic; derived supplies two constants.
- `EqualityNode<Derived>` — EQ/NEQ; dispatches `compareBool`/`compareNumber` to derived.
- `OrderComparisonNode<Derived>` — LT/GT/LTE/GTE; enforces NUMBER operands; dispatches `compare`.

CRTP bodies live entirely in headers (no `.cpp`). `AndNode`/`OrNode` and all four
order-comparison nodes are header-only.

### adjustDepthRecursive(int delta)
Called on the subtree that is about to become a *deeper* child (delta = +1 per level
gained) or shallower (delta = -1/-2 during optimization). Must be called **before**
the node is moved into its new parent.

---

## Non-obvious invariants / past bugs fixed

| Issue | Resolution |
|---|---|
| Ternary `?:` between `unique_ptr<GteNode>` and `unique_ptr<GtNode>` — GCC can't deduce common type | Replaced with explicit `if/else if` branches in `parseNumericComparison` |
| `parseEqual` had a spurious `current()=='<' \|\| current()=='>'` early-return guard | Removed; `<`/`>` are fully consumed by `parseNumericComparison` before `parseEqual` runs |
| `m["v2"] = "-10"` in original `main` made `v2 > 3` false → e5/e6 fail | Changed to `"5"`; original `main` never evaluated (always returned `true`) so the bug was hidden |
| All comparison operators marked `// TODO` in original `evaluateTree` | Fully implemented in the refactor |
| `ALLOW_ETHEROGENEOUS_COMPARISONS` typo in original macro | Fixed to `kAllowHeterogeneousComparisons` in `config.hpp` |

---

## Test suite quick reference

`test/test_expr_eval.cpp` — no Catch2/gtest.  Key helpers:
- `eval(expr, vars)` — calls `ExprEval::evaluate()` with `cout` suppressed (redirected
  to `ostringstream sink`); re-throws all exceptions.
- `EXPECT_THROW(ExcType, expr, label)` — catches only `ExcType`; fails if none thrown.

Sections (75 tests total):
`Literals` · `Terminal variable lookup` · `Equality` · `Numeric comparisons` ·
`Logical AND` (incl. short-circuit) · `Logical OR` (incl. short-circuit) ·
`NOT / double-NOT` · `NEGATE / double-NEGATE` · `Parentheses` · `Complex (e1–e7)` ·
`ParseError` · `EvaluationError`

Expected result: **75 passed, 0 failed**.

---

## Grammar / operator precedence (unchanged from original)

```
OR < AND < equality (==,!=) < comparison (<,<=,>,>=) < NOT(!) < NEGATE(-) < atom
```
OR and AND are **right-associative** (recursive call goes to the right operand).
Equality chains are also right-associative.

---

## What must never change

- `../mono_file/expr_eval.cpp` — read-only, never touch.
- Grammar and operator precedence above.
- Depth/ID tracking on AST nodes (used by `print()`).
- `kMaxRecursionDepth` guard in Parser.
