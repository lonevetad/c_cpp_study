# C++ Modern Standards Reference

You are helping with C++ code. Apply the modern C++ standards below as guidelines.
This skill covers C++11 through C++23, with special emphasis on **C++14** (the target
used in FCPP and related projects in this workspace).

---

## Core Language — C++11/14 Baseline

### Auto and Type Deduction
```cpp
auto x = 42;                    // int
auto& ref = container;          // reference
const auto* ptr = &val;         // const pointer
auto lambda = [](int x){ return x * 2; };
```

### Lambda Expressions
```cpp
// C++11: capture by value/reference
auto f = [x, &y](int z) -> double { return x + y + z; };

// C++14: generic lambdas (auto parameters → template expansion)
auto g = [](auto a, auto b) { return a + b; };

// C++14: init-capture (move into lambda)
auto h = [val = std::move(expensive)](){ return val.compute(); };

// Mutable lambda (modifies captured copies)
auto counter = [n = 0]() mutable { return ++n; };
```

### Smart Pointers (prefer over raw owning pointers)
```cpp
#include <memory>
auto p  = std::make_unique<T>(args...);   // unique ownership (C++14)
auto sp = std::make_shared<T>(args...);   // shared ownership
std::weak_ptr<T> wp = sp;                 // non-owning observer

// Transfer ownership
auto p2 = std::move(p);   // p is now null
```

### Move Semantics and Perfect Forwarding
```cpp
// Move constructor / assignment — steal resources instead of copying
class Foo {
    Foo(Foo&& other) noexcept : data_(std::move(other.data_)) {}
    Foo& operator=(Foo&&) noexcept = default;
};

// Perfect forwarding — preserve value category
template<typename T>
void wrap(T&& arg) { target(std::forward<T>(arg)); }

// std::move: cast to rvalue reference (enables move)
auto v2 = std::move(v1);  // v1 is "valid but unspecified" afterwards
```

### RAII — Resource Acquisition Is Initialization
```cpp
// Wrap any resource in a class; destructor releases it
struct FileHandle {
    explicit FileHandle(const char* path) : f_(fopen(path, "r")) {}
    ~FileHandle() { if (f_) fclose(f_); }
    FileHandle(const FileHandle&) = delete;
    FileHandle& operator=(const FileHandle&) = delete;
    FILE* f_;
};
```

### Rule of Zero / Three / Five
```cpp
// Rule of Zero (preferred): use RAII members; don't declare any special member.
struct Good { std::string name; std::vector<int> data; };

// Rule of Five: if you declare any of the 5, declare all 5:
//   destructor, copy ctor, copy assign, move ctor, move assign
class Resource {
public:
    ~Resource();
    Resource(const Resource&);
    Resource& operator=(const Resource&);
    Resource(Resource&&) noexcept;
    Resource& operator=(Resource&&) noexcept;
};
```

---

## Templates and Generic Programming

### Function Templates
```cpp
template<typename T>
T clamp(T val, T lo, T hi) { return std::max(lo, std::min(val, hi)); }

// C++14: return type deduction
template<typename T, typename U>
auto add(T a, U b) { return a + b; }   // return type deduced
```

### Class Templates and Specialization
```cpp
template<typename T, std::size_t N>
struct Array { T data[N]; };

// Full specialization
template<>
struct Array<bool, 8> { uint8_t bits; };

// Partial specialization
template<typename T>
struct Array<T*, 0> { /* pointer specialization */ };
```

### Variadic Templates (C++11)
```cpp
template<typename... Args>
void log(Args&&... args) {
    (std::cout << ... << args) << '\n';  // C++17 fold
    // C++14 alternative: use initializer_list trick
}

// Expand pack into tuple
template<typename... Ts>
auto make_tuple_of(Ts&&... vs) {
    return std::make_tuple(std::forward<Ts>(vs)...);
}
```

### SFINAE and `enable_if` (C++11/14)
```cpp
// Enable only for arithmetic types
template<typename T,
         typename = std::enable_if_t<std::is_arithmetic<T>::value>>
T square(T x) { return x * x; }
```

### `constexpr` Functions
```cpp
// C++11: single return statement
constexpr int factorial(int n) { return n <= 1 ? 1 : n * factorial(n-1); }

// C++14: full function body allowed
constexpr int fibonacci(int n) {
    if (n <= 1) return n;
    int a = 0, b = 1;
    for (int i = 2; i <= n; ++i) { int t = a + b; a = b; b = t; }
    return b;
}
```

---

## STL Containers and Algorithms

### Container Selection Guide
```
std::vector<T>       — default sequence container; cache-friendly
std::array<T, N>     — fixed-size stack array; zero overhead
std::deque<T>        — fast push/pop front and back
std::list<T>         — only if many middle insertions; poor cache
std::unordered_map   — O(1) avg lookup; default for key-value maps
std::map<K,V>        — O(log n); sorted; use when order matters
std::set<T>          — sorted unique elements
std::unordered_set   — O(1) avg; default for membership tests
```

### Algorithms (prefer over manual loops)
```cpp
#include <algorithm>
#include <numeric>

std::sort(v.begin(), v.end());
std::sort(v.begin(), v.end(), std::greater<int>{});

auto it = std::find_if(v.begin(), v.end(), [](int x){ return x > 10; });

std::transform(src.begin(), src.end(), dst.begin(),
               [](auto x){ return x * 2; });

int total = std::accumulate(v.begin(), v.end(), 0);

// C++17 parallel policies
std::sort(std::execution::par, v.begin(), v.end());
```

---

## C++17 Key Additions

```cpp
// Structured bindings
auto [key, val] = *map.find("x");
auto [x, y, z]  = std::tuple{1, 2.0, "hi"};

// if constexpr — compile-time branch (no SFINAE needed)
template<typename T>
void process(T val) {
    if constexpr (std::is_integral_v<T>) { /* int path */ }
    else                                 { /* float path */ }
}

// std::optional
std::optional<int> maybe_parse(const std::string& s) {
    if (s.empty()) return std::nullopt;
    return std::stoi(s);
}
auto v = maybe_parse("42").value_or(0);

// std::variant (type-safe union)
std::variant<int, double, std::string> var = "hello";
std::visit([](auto& v){ std::cout << v; }, var);

// std::string_view — non-owning string reference
void log(std::string_view msg);   // accepts string, char*, string_view

// Fold expressions
template<typename... Ts>
auto sum(Ts... vs) { return (vs + ...); }   // (v0 + (v1 + ... + vn))
```

---

## C++20 Key Additions

```cpp
// Concepts — readable constraints
template<typename T>
concept Numeric = std::is_arithmetic_v<T>;

template<Numeric T>
T abs_val(T x) { return x < 0 ? -x : x; }

// Ranges
#include <ranges>
auto evens = v | std::views::filter([](int x){ return x % 2 == 0; })
               | std::views::transform([](int x){ return x * x; });

// Coroutines (co_yield, co_await, co_return)
// Three-way comparison (spaceship operator)
auto cmp = (a <=> b);  // std::strong_ordering / partial_ordering / weak_ordering

// std::span — non-owning view over contiguous data
void print(std::span<const int> data);
```

---

## Modern C++ Best Practices

### Prefer
- `auto` for variables when type is obvious from context
- `const` by default; add `mutable` only when needed
- `noexcept` on move operations and destructors
- `[[nodiscard]]` on functions whose return value must be used
- `std::array` over C arrays; `std::string` over `char*`
- Range-based `for (auto& x : container)`
- Scoped enums: `enum class Color { Red, Green, Blue };`
- `nullptr` over `NULL` or `0`
- `= delete` to explicitly forbid operations
- `= default` to explicitly request compiler-generated operations

### Avoid
- Raw owning pointers (`new` / `delete`)
- `reinterpret_cast` / `const_cast` (prefer `static_cast`)
- `std::endl` (flushes buffer; use `'\n'`)
- Uninitialized variables
- Magic numbers without named constants
- `using namespace std;` in headers
- Premature optimization before profiling

### Include Order (Google style)
```cpp
// 1. Related header
// 2. Blank line
// 3. System headers (<vector>, <string>...)
// 4. Blank line
// 5. Third-party headers
// 6. Project headers
```

---

## C++14 Specifically (FCPP target version)

FCPP is compiled with **C++14**. Key C++14 features used:

```cpp
// Generic lambdas (most important for FCPP aggregate functions)
auto acc = [](auto a, auto b) { return a + b; };

// Return type deduction
auto compute() { return std::make_tuple(1, 2.0); }

// Variable templates
template<typename T>
constexpr T pi = T(3.14159265358979323846);

// std::make_unique (missing from C++11)
auto p = std::make_unique<MyType>(arg1, arg2);

// Aggregate member initialization
struct Point { double x = 0.0; double y = 0.0; };
```

When writing code targeting C++14, avoid:
- `if constexpr` (C++17)
- structured bindings (C++17)
- `std::optional` / `std::variant` (C++17)
- Concepts (C++20)
- Ranges (C++20)
