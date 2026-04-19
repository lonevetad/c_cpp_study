# Deep Explanation — C++ Features Used in the `expr_eval` Refactor

This document explains every non-trivial C++ feature that appears in the
`multiclass/` project: what it is, why it exists, and concretely where it is
used here.  Ordered from "you will see this everywhere" to "more advanced".

---

## 1. `virtual`, `override`, `final`, and `= 0`

### The problem they solve

Without `virtual`, calling a method through a base-class pointer always runs
the **base class version**, regardless of the actual object type:

```cpp
AstNode* node = new AndNode(...);
node->evaluate(vars); // Without virtual: calls AstNode::evaluate — wrong!
                      // With virtual:    calls AndNode::evaluate — correct!
```

### How `virtual` works internally

The compiler adds a hidden pointer — the **vtable pointer** — to every object
of a class that has at least one `virtual` method.  That pointer points to a
table of function pointers (the vtable), one entry per virtual method.  At
runtime, `node->evaluate(vars)` reads the vtable pointer, looks up the slot
for `evaluate`, and calls whatever is there.  This is called **dynamic dispatch**
or **virtual dispatch**.

### `= 0` — pure virtual, abstract class

```cpp
// In AstNode.hpp:
[[nodiscard]] virtual Value evaluate(const Variables& vars) const = 0;
```

`= 0` means "I declare this method but provide no body".  Any class with at
least one pure virtual method is **abstract** — you cannot create an instance
of it directly.  Concrete subclasses (`AndNode`, `TerminalNode`, …) *must*
override every pure virtual method or they are abstract too.

This is how the design enforces that every node in the tree has its own
`evaluate()` and `print()` — the compiler rejects any class that forgets.

### `override`

```cpp
[[nodiscard]] Value evaluate(const Variables& vars) const override final;
```

`override` is optional but valuable.  It tells the compiler: "this method is
intentionally overriding a virtual method in a base class."  The compiler then
verifies that the signature matches exactly.  Without `override`, a typo
(`evalute` instead of `evaluate`) silently creates a *new* unrelated method
instead of overriding the base — a common bug.

### `final`

`final` on a method means "no further subclass may override this".
`final` on a class (e.g. `class AndNode final`) means "no class may inherit
from this".

In `LogicalBinaryNode.hpp`:
```cpp
[[nodiscard]] Value evaluate(...) const override final { ... }
```
`override final` says: "I override the base, and I am the last override".
This matters for the CRTP templates (see section 7) because `AndNode` and
`OrNode` inherit from `LogicalBinaryNode<Derived>` — we want them to use the
template's implementation, not accidentally override it again.

### `virtual ~AstNode() = default`

```cpp
virtual ~AstNode() = default;
```

If the destructor is *not* virtual and you `delete` through a base pointer,
only the base destructor runs — the derived class's destructor is silently
skipped, leaking all children.

```cpp
std::unique_ptr<AstNode> node = std::make_unique<AndNode>(...);
// When node goes out of scope, unique_ptr calls delete on an AstNode*.
// With virtual ~AstNode(): AndNode::~AndNode() runs first, then ~AstNode().
// Without virtual:          only ~AstNode() runs — AndNode's children leak!
```

`= default` means "generate the default implementation (do nothing special)".

---

## 2. `[[nodiscard]]`

`[[nodiscard]]` is a C++17 **attribute** (the `[[...]]` syntax).  It tells the
compiler to emit a warning if a caller ignores the return value.

```cpp
[[nodiscard]] Value evaluate(const Variables& vars) const = 0;
[[nodiscard]] std::unique_ptr<AstNode> optimize(std::unique_ptr<AstNode> self) = 0;
[[nodiscard]] static std::optional<Value> fromString(std::string_view s);
```

Why it matters here:

- `evaluate()` returns a `Value`.  If you forget to use it, you computed
  something for nothing — likely a logic error.
- `optimize()` returns the *replacement* node (which might not be `this`).
  Ignoring the return value means the optimized tree is immediately destroyed.
  The ownership-transfer pattern (section 9) makes this especially dangerous.
- `fromString()` returns `std::optional<Value>`.  Ignoring it means you silently
  discard whether parsing succeeded.

Without `[[nodiscard]]`, these mistakes compile silently and produce subtle bugs.
With it, the compiler warns on every call site that ignores the return value.

---

## 3. `friend`

`friend` grants a specific function or class access to the `private` and
`protected` members of a class.

In `Value.hpp`:
```cpp
class Value {
    // ...
private:
    std::variant<bool, double> data_;   // private!

public:
    friend std::ostream& operator<<(std::ostream& os, const Value& v);
};
```

`operator<<` needs to read `data_` to print the value.  But `data_` is private —
no external code should be able to modify or even read the internal representation
directly.  `friend` punches a named, controlled hole: only this specific function
gets access.  The rest of the world still can't touch `data_`.

Why not just make `operator<<` a member method?  Because `operator<<` must be
called as `os << v`, which means the left side (`os`) is the first argument.
Member methods have `this` as the hidden first argument, so `v.operator<<(os)`
would be required — the backwards syntax nobody uses.  A free function
with `friend` is the standard solution.

---

## 4. `std::string_view`

`std::string_view` (C++17) is a **non-owning, read-only window** into a string.
It stores just two things: a pointer to the first character and a length.  It
does not own the memory and never copies it.

```cpp
[[nodiscard]] static std::optional<Value> fromString(std::string_view s);
[[nodiscard]] bool evaluate(std::string_view expression, const Variables& variables);
```

Why not `const std::string&`?

| `const std::string&` | `std::string_view` |
|---|---|
| Works with `std::string` objects | Works with `std::string`, string literals, `char*`, substrings — anything |
| If caller passes a literal like `"true"`, compiler may create a temporary `std::string` (allocation!) | Never allocates; just takes the pointer and length |
| Cannot view a *slice* of a string | Can view `s.substr(...)` without a copy |

**The critical rule:** `string_view` does not extend the lifetime of its source.
If the string it points to is destroyed while the view still exists, you have
undefined behaviour.  In this project, every `string_view` parameter is used
only during the call — no view is stored past its source's lifetime — so it
is safe.

---

## 5. `explicit`

```cpp
explicit Value(bool b) noexcept : data_{b} {}
explicit Value(double d) noexcept : data_{d} {}
```

Without `explicit`, a single-argument constructor acts as an **implicit
conversion**.  The compiler may then call it automatically without you asking:

```cpp
void foo(Value v);
foo(true);   // Without explicit: silently calls Value(bool) — surprise!
foo(3.14);   // Without explicit: silently calls Value(double) — surprise!
```

`explicit` disables that.  You must write `Value{true}` or `Value{3.14}`
intentionally.  This prevents accidental conversions and makes code clearer
about what is happening.

---

## 6. `noexcept`

```cpp
explicit Value(bool b) noexcept : data_{b} {}
virtual void adjustDepthRecursive(int delta) noexcept { depth += delta; }
```

`noexcept` is a promise: "this function will never throw an exception".
If it does throw despite the promise, `std::terminate` is called immediately
(the program crashes rather than propagating the exception).

Two benefits:
1. **Optimizer**: knowing a function cannot throw lets the compiler generate
   slightly faster code (no need to set up exception-handling infrastructure
   around the call).
2. **Move semantics**: the standard library uses `noexcept` to decide whether
   to move or copy objects in containers.  A `noexcept` move constructor allows
   `std::vector` to move elements instead of copying during reallocation.

Use `noexcept` only when you are certain the function cannot throw.
Constructors that just store a value into a `variant` and integer arithmetic
cannot throw — they are correct candidates.

---

## 7. `constexpr` and `if constexpr`

### `constexpr` variables and functions

`constexpr` means "evaluate this at compile time".  A `constexpr` variable
is computed once by the compiler and baked into the binary as a constant —
no runtime computation needed.

```cpp
// config.hpp:
inline constexpr int  kMaxRecursionDepth           = 10000;
inline constexpr bool kAllowHeterogeneousComparisons = true;
```

`inline constexpr` is the correct way to define a `constexpr` variable in a
header file that is included in multiple `.cpp` files.  Without `inline`, each
translation unit would have its own copy — violating the One Definition Rule
and causing linker errors.

The `kUnallowedCharsTerminal` array is initialized with a **constexpr lambda**:

```cpp
inline constexpr std::array<bool, 256> kUnallowedCharsTerminal = []() {
    std::array<bool, 256> result{};
    for (char c : chars) result[static_cast<unsigned char>(c)] = true;
    return result;
}();
```

The entire table is built by the compiler.  At runtime, checking whether a
character is allowed is a single array lookup — zero computation.

### `if constexpr`

```cpp
// EqualityNode.hpp:
if constexpr (kAllowHeterogeneousComparisons) {
    return Value{Derived::kHeterogeneousResult};
} else {
    throw EvaluationError(...);
}
```

`if constexpr` (C++17) evaluates the condition **at compile time** and
discards the branch that is not taken — it is never compiled into the binary.
This differs from a regular `if` where both branches are compiled and the
condition is evaluated at runtime.

Here it means: if `kAllowHeterogeneousComparisons` is `true`, the `throw`
branch does not exist in the compiled binary at all.  Zero overhead.

---

## 8. `= delete` and `= default` — controlling special members

C++ automatically generates six "special member functions" for any class:
default constructor, destructor, copy constructor, copy assignment, move
constructor, move assignment.  You can explicitly control each:

```cpp
// AstNode.hpp:
AstNode(const AstNode&)            = delete;   // no copy
AstNode& operator=(const AstNode&) = delete;   // no copy assignment
AstNode(AstNode&&)                 = default;  // move OK (generated by compiler)
AstNode& operator=(AstNode&&)      = default;  // move assignment OK
```

Why delete copy for `AstNode`?

An AST node owns its children via `unique_ptr`.  A copy would require deep-copying
the entire subtree — complex, error-prone, and not needed in this project.
Deleting copy forces the programmer to use `std::move` intentionally and prevents
accidental expensive copies.

Move is left enabled (`= default`) because moving a `unique_ptr`-owning object is
cheap (just transfers the pointer) and needed for the ownership-transfer patterns.

---

## 9. `std::unique_ptr` and RAII

**RAII** stands for *Resource Acquisition Is Initialization*.  The idea: tie the
lifetime of a resource (heap memory, file handle, …) to the lifetime of a C++
object.  When the object is destroyed (goes out of scope, is overwritten, etc.),
its destructor runs and releases the resource automatically.

`std::unique_ptr<T>` is a RAII wrapper for a heap-allocated `T`.  It has exactly
one owner at a time.  When the `unique_ptr` is destroyed, it calls `delete` on the
managed pointer.  When it is moved, ownership transfers and the source becomes null.

```cpp
// Parser returns a unique_ptr<AstNode>.
// The whole tree is owned by this one pointer.
std::unique_ptr<AstNode> root = parser.parse();
// root goes out of scope → ~AstNode() called recursively on entire tree.
// No manual delete anywhere.
```

Before the refactor, the original code used raw `new`/`delete`.  If an exception
was thrown during parsing, the `delete` call at the end was skipped — memory leak.
With `unique_ptr`, exception or not, the destructor always runs.

`std::move` is required to transfer ownership:
```cpp
auto node = std::make_unique<AndNode>(std::move(left), std::move(right));
//                                    ↑                  ↑
// left and right unique_ptrs are moved into AndNode's constructor.
// After this, left and right are null — AndNode owns the children.
```

---

## 10. `std::variant` — type-safe union

The original code used a C-style union:
```c
union { bool boolValue; double numValue; }; // C style — no type safety
```

A C union stores multiple types in the same memory.  There is no built-in way to
know which type is currently active.  If you write a `double` then read a `bool`,
the behaviour is undefined.

`std::variant<bool, double>` (C++17) is a type-safe replacement:
```cpp
std::variant<bool, double> data_;
```

It still stores only one of its types at a time, but it tracks *which* one.
Access is safe:

```cpp
// Value.cpp:
if (std::holds_alternative<bool>(data_))
    return ValueType::BOOLEAN;
if (std::holds_alternative<double>(data_))
    return ValueType::NUMBER;

// Accessing the value:
return std::get<bool>(data_);   // throws std::bad_variant_access if wrong type
```

This replaces the original pattern of separate enum + raw union with a single
object that enforces consistency — impossible to read the wrong type silently.

---

## 11. `std::optional` — a value that may not exist

`std::optional<T>` (C++17) holds either a value of type `T` or nothing
(`std::nullopt`).  It represents the concept "this result might not exist",
without heap allocation and without exceptions.

```cpp
// Value.hpp:
[[nodiscard]] static std::optional<Value> fromString(std::string_view s);
```

`fromString("true")` → `std::optional<Value>` containing `Value{true}`.
`fromString("xyz")`  → `std::nullopt` (not a bool or number).

The caller checks:
```cpp
// TerminalNode.cpp:
if (auto v = Value::fromString(value_)) return *v;
//           ↑ evaluates to true if a value is present
//                                   ↑ dereference extracts the Value
```

Before `std::optional`, common alternatives were:
- Return a sentinel value (`-1`, `nullptr`) — requires agreement on what sentinel means, no type safety.
- Throw an exception — expensive, semantically wrong for "expected failure" cases.
- Output parameter `bool* ok` — ugly, two-step.

`std::optional` is the modern, zero-overhead, self-documenting answer.

---

## 12. The exception hierarchy — why errors are defined that way

```cpp
// errors.hpp:
class ParseError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

class EvaluationError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};
```

### Why inherit from `std::runtime_error`?

`std::runtime_error` is a standard exception class that holds a `std::string`
message (accessible via `.what()`).  By inheriting from it, our exceptions:
- Are caught by `catch (const std::exception&)` — standard catch-all for library users.
- Carry a human-readable message automatically.
- Fit into the standard C++ exception hierarchy.

### Why not use `std::runtime_error` directly?

Using two distinct types allows callers to distinguish them:
```cpp
try {
    evaluate(expr, vars);
} catch (const ParseError& e) {
    // The expression string is malformed — user input error.
    std::cerr << "Parse error: " << e.what();
} catch (const EvaluationError& e) {
    // The expression parsed fine but evaluation failed — type mismatch, etc.
    std::cerr << "Evaluation error: " << e.what();
}
```

If both were `std::runtime_error`, a caller could not tell the difference.

### `using std::runtime_error::runtime_error`

This is **constructor inheritance** (C++11).  Without it, `ParseError` would have
no constructor — you could not write `throw ParseError("message")`.  You would
need to write the forwarding constructor manually:
```cpp
// Without using: must write this boilerplate
ParseError(const std::string& msg) : std::runtime_error(msg) {}
```
`using Base::Base` inherits all constructors from the base class automatically,
eliminating the boilerplate.

---

## 13. CRTP — Curiously Recurring Template Pattern

### The problem

`AndNode` and `OrNode` have identical logic — they differ only in two constants
(`kShortCircuitValue` and `kSymbol`).  Options:

1. Copy-paste the code into both classes — duplication, maintenance nightmare.
2. Runtime polymorphism (virtual method returning the constant) — adds a vtable
   call just to read a constant that is known at compile time.
3. CRTP — zero runtime overhead, zero code duplication.

### How CRTP works

```cpp
// LogicalBinaryNode.hpp:
template<typename Derived>
class LogicalBinaryNode : public BinaryNode {
public:
    [[nodiscard]] Value evaluate(...) const override final {
        // ...
        if (l.getBool() == Derived::kShortCircuitValue)  // ← reads Derived's constant
            return Value{Derived::kShortCircuitValue};
        // ...
    }
};

// AndNode.hpp:
class AndNode final : public LogicalBinaryNode<AndNode> {
//                                             ↑ Derived = AndNode
public:
    using LogicalBinaryNode<AndNode>::LogicalBinaryNode;  // inherit constructor
    static constexpr bool             kShortCircuitValue = false;
    static constexpr std::string_view kSymbol            = "&&";
};
```

When the compiler instantiates `LogicalBinaryNode<AndNode>`, it knows `Derived`
is `AndNode` at compile time.  `Derived::kShortCircuitValue` is resolved at
compile time to `false` — no virtual call, no runtime lookup, no overhead.

The "curiously recurring" part: `AndNode` passes *itself* as the template
argument to its own base class.  The base class then calls methods/reads
constants from the derived class — without virtual dispatch.

### CRTP in this project

| Template base | Concrete classes | What is shared | What differs |
|---|---|---|---|
| `LogicalBinaryNode<D>` | `AndNode`, `OrNode` | `evaluate()`, `print()` | `kShortCircuitValue`, `kSymbol` |
| `EqualityNode<D>` | `EqNode`, `NeqNode` | `evaluate()`, `print()`, hetero policy | `compareBool`, `compareNumber`, `kHeterogeneousResult`, `kSymbol` |
| `OrderComparisonNode<D>` | `LtNode`, `GtNode`, `LteNode`, `GteNode` | `evaluate()`, `print()` | `compare(double,double)`, `kSymbol` |

Six comparison operators share zero duplicated logic.

### Why CRTP bodies live in headers

Templates are not compiled until they are instantiated.  The compiler needs to
see the full template body at the point of instantiation.  That instantiation
happens in headers like `AndNode.hpp` that include `LogicalBinaryNode.hpp`.
Therefore the entire template body must be in the header — no `.cpp` file.

---

## 14. The `optimize()` ownership-transfer pattern

```cpp
virtual std::unique_ptr<AstNode> optimize(std::unique_ptr<AstNode> self) = 0;
```

This is a bespoke pattern designed for safe node replacement during optimization.

**The challenge:** a node needs to be able to replace itself with one of its
children (e.g. `ExprNode` collapses parentheses by returning its child instead
of itself).  But a node cannot destroy itself — it is forbidden to `delete this`
while code in `this` is still running.

**The solution:** transfer ownership *into* the method.  `self` is a `unique_ptr`
that owns `this`.  The method can then:

```cpp
// Option A: return self unchanged — caller keeps the same node.
return self;

// Option B: return a child — self drops at function exit, destroying this cleanly.
auto child = std::move(child_);  // extract the child
// self still holds `this`, but we are about to return child.
return child;
// ← function exits here.  `self` is not returned, so it is destroyed.
//   ~ExprNode() runs.  `this` is now dead.  The child lives on in the caller.
```

**Why `optimizeNode()` is the only safe call site:**

```cpp
// AstNode.hpp:
[[nodiscard]] std::unique_ptr<AstNode> optimizeNode(std::unique_ptr<AstNode> node);

// AstNode.cpp:
std::unique_ptr<AstNode> optimizeNode(std::unique_ptr<AstNode> node) {
    if (!node) return nullptr;
    return node->optimize(std::move(node));
}
```

You cannot write `node->optimize(node)` directly.  `std::move(node)` on the right
side of `->` evaluates *after* the pointer lookup but *before* the call, leaving
`node` null.  The free function wraps this safely.  Everywhere else in the code,
`optimizeNode(std::move(ptr))` is called — never the method directly.

---

## 15. `#pragma once`

```cpp
#pragma once
```

This is a **non-standard but universally supported** alternative to traditional
include guards:

```cpp
// Traditional include guard (standard but verbose):
#ifndef EXPR_EVAL_AST_NODE_HPP
#define EXPR_EVAL_AST_NODE_HPP
// ... header content ...
#endif
```

`#pragma once` tells the preprocessor: "include this file only once per
compilation unit, no matter how many times `#include` is written".  It has
the same effect but with one line instead of three.  GCC, Clang, and MSVC all
support it.  It was chosen here for brevity.

---

## 16. `using BinaryNode::BinaryNode` — inheriting constructors

```cpp
class AndNode final : public LogicalBinaryNode<AndNode> {
public:
    using LogicalBinaryNode<AndNode>::LogicalBinaryNode;
    // ...
};
```

`AndNode` adds no new data members.  It needs the same constructor as
`LogicalBinaryNode<AndNode>`, which inherits from `BinaryNode`, which takes
`(unique_ptr<AstNode> left, unique_ptr<AstNode> right)`.

Without `using`, `AndNode` would have no constructor — you could not write
`std::make_unique<AndNode>(std::move(left), std::move(right))`.

`using Base::Base` makes all base constructors available in the derived class
with no extra code.

---

## 17. `namespace ExprEval`

All project code lives inside `namespace ExprEval`.  Without it, names like
`Value`, `Parser`, `evaluate` would be in the global namespace and could clash
with names from other libraries or future standard additions.

The public API header `ExpressionEvaluator.hpp` exposes only:
```cpp
namespace ExprEval {
    bool evaluate(std::string_view expression, const Variables& variables);
}
```

The caller writes `ExprEval::evaluate(...)`.  This makes clear which `evaluate`
is being called and prevents accidental name collision.

---

## 18. Standards followed

| Standard / guideline | Applied where |
|---|---|
| **C++26** (`-std=c++26`) | Entire project; uses `std::format`, `std::optional`, `std::variant`, CTAD, `if constexpr` |
| **C++ Core Guidelines (CG)** | RAII (C.31), `unique_ptr` (R.20), `[[nodiscard]]` (F.48), `explicit` (C.46), `= delete` copy (C.81) |
| **Rule of Zero / Five** | `AstNode` deletes copy, defaults move; leaf nodes use `= default` dtor |
| **Open/Closed Principle (OCP)** | Adding an operator = new class; existing classes untouched |
| **Single Responsibility** | One class per node type, one header per class |
| **DRY (Don't Repeat Yourself)** | CRTP eliminates duplication across node families |
| **Google C++ Style (naming)** | `kConstantName` for `constexpr` constants; `snake_case_` for private members |
| **Incremental compilation** | `-MMD -MP` in Makefile; headers tracked automatically |

---

## 19. Summary — why each feature was chosen over alternatives

| Feature used | Alternative not used | Reason |
|---|---|---|
| `virtual` dispatch | `switch(op)` enum | Adding operator = 1 new file, 0 changed files |
| `std::unique_ptr` | raw `new`/`delete` | Exception-safe, no leak, self-documenting ownership |
| `std::variant<bool,double>` | C union + enum | Type-safe, cannot read wrong type silently |
| `std::optional<Value>` | sentinel / exception for "not parsed" | Zero allocation, expressive, no exception overhead |
| `std::string_view` | `const std::string&` | No allocation for literals, works with any string-like source |
| CRTP templates | copy-paste or virtual constants | Zero overhead, zero duplication |
| `[[nodiscard]]` | nothing | Catches "forget to use return value" bugs at compile time |
| `explicit` constructors | implicit constructors | Prevents accidental `Value{someInt}` conversions |
| `if constexpr` | runtime `if` | Branch resolved at compile time; unused branch not compiled |
| `= delete` copy | allow copy | Nodes own subtrees; deep-copy is complex and unneeded |
| `friend operator<<` | public getter for `data_` | Keeps `data_` private; only printing gets access |
| Separate `ParseError`/`EvaluationError` | single exception type | Callers can handle parse vs. runtime failures differently |
