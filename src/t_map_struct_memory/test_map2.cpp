/**
 * test_map2.cpp
 *
 * Extended version of test_map.cpp.  All eight original examples are
 * preserved unchanged; two additional examples (5a and 5b) are appended
 * to demonstrate std::map with Point2* values.
 *
 * The purpose of the extension is to show that the C++ struct/class keyword
 * difference is irrelevant to map ownership semantics.  What matters is
 * whether a value is stored BY VALUE (inline in the node → RAII) or BY
 * POINTER (separately heap-allocated → manual delete required):
 *
 *   Point  (simple_struct.h)  — stored by value in examples 3a/3b → RAII.
 *   Point2 (simple_struct2.h) — stored as Point2* in examples 5a/5b →
 *                               identical ownership pattern to Person*.
 *
 * Value types covered (10 examples total, 2 key types each):
 *   1. int32_t                    (inline, RAII)
 *   2. std::string*               (heap, manual delete)
 *   3. Point                      (inline struct, RAII)
 *   4. Person*                    (heap class, manual delete)
 *   5. Point2*                    (heap struct, manual delete)  ← NEW
 *
 * Output is written to "test_map2_output.txt" in the current working
 * directory (run the executable from the TESTS/ folder).
 *
 * Requires C++17 (structured bindings, std::tuple deduction).
 */

#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <string>
#include <tuple>
#include <utility>

#include "map_printer.h"    // display() overloads for int32_t, std::string,
                            // std::string*, Point, Person*; + print_map<K,V>
#include "simple_struct2.h" // Point2

// display() overload for Point2*.
// Defined here (in the same translation unit as print_map instantiations for
// Point2*) so that two-phase ADL lookup finds it at instantiation time.
inline std::string display(const Point2* v) {
    return v ? v->to_string() : "null";
}

// =============================================================================
//  Internal helpers
// =============================================================================

static void section(std::ostream& out, const std::string& title) {
    const int         W   = 70;
    const std::string bar(W, '=');
    out << '\n' << bar << '\n'
        << "  " << title << '\n'
        << bar << '\n';
}

static void subsection(std::ostream& out, const std::string& label) {
    out << "\n  -- " << label << " --\n";
}

// =============================================================================
//  Example 1a — std::map<int32_t, int32_t>
// =============================================================================

static void ex1a_int_to_int(std::ostream& out) {
    section(out, "Example 1a: std::map<int32_t, int32_t>");

    out << R"(
[MEMORY MODEL]
  Stack : The 'map' variable itself is a small fixed-size object (~48 B on
          most 64-bit implementations). It lives on the caller's stack frame
          and holds: a pointer to the root tree node, the element count, the
          comparator, and the allocator state.
  Heap  : Every call to insert()/emplace()/operator[] causes std::allocator
          to allocate one red-black tree node on the heap. Each node contains
          the key (int32_t, 4 B) and the value (int32_t, 4 B) stored inline —
          there is no extra indirection or secondary allocation.
  RAII  : When the map goes out of scope its destructor walks the entire tree
          and deallocates every node. The caller needs to do nothing.
)";

    std::map<int32_t, int32_t> m;

    subsection(out, "Insertions");
    const std::pair<int32_t, int32_t> inserts[] = {
        {3, 300}, {1, 100}, {5, 500}, {2, 200}, {4, 400}
    };
    for (const auto& [k, v] : inserts) {
        out << "  [ADD]    key=" << k << "  value=" << v
            << "  => 1 heap node allocated (key + value inline)\n";
        m.emplace(k, v);
    }

    out << "\n[MAP STATE — ordered by key]\n";
    print_map(m, out);
    out << '\n';

    subsection(out, "Removals");
    const int32_t removes[] = {5, 2};
    for (int32_t k : removes) {
        out << "  [REMOVE] key=" << k << "  (stored value=" << m.at(k) << ")"
            << "  => heap node deallocated by std::allocator\n";
        m.erase(k);
    }

    out << "\n[MAP STATE — after removals]\n";
    print_map(m, out);
    out << '\n';

    out << "\n[MEMORY] 'map' leaves scope => remaining " << m.size()
        << " node(s) freed automatically by the destructor.\n";
}

// =============================================================================
//  Example 1b — std::map<std::string, int32_t>
// =============================================================================

static void ex1b_str_to_int(std::ostream& out) {
    section(out, "Example 1b: std::map<std::string, int32_t>");

    out << R"(
[MEMORY MODEL]
  Stack : Same as 1a — the map object lives on the caller's stack.
  Heap  : Each tree node stores a std::string key. std::string uses Small
          String Optimisation (SSO): keys up to ~15 chars are stored inside
          the string object itself (no extra heap allocation); longer keys
          trigger an additional heap allocation for the character buffer.
          The int32_t value is stored inline in the node — no extra pointer.
  RAII  : The map destructor calls ~std::string() for every key (freeing any
          SSO-overflow heap buffers) and then frees each node. Zero manual
          cleanup is required.
)";

    std::map<std::string, int32_t> m;

    subsection(out, "Insertions");
    const std::pair<const char*, int32_t> inserts[] = {
        {"delta", 40}, {"alpha", 10}, {"echo", 50}, {"beta", 20}, {"gamma", 30}
    };
    for (const auto& [k, v] : inserts) {
        out << "  [ADD]    key=\"" << k << "\"  value=" << v << '\n';
        m.emplace(k, v);
    }

    out << "\n[MAP STATE — ordered lexicographically]\n";
    print_map(m, out);
    out << '\n';

    subsection(out, "Removals");
    const char* removes[] = {"echo", "alpha"};
    for (const char* k : removes) {
        out << "  [REMOVE] key=\"" << k
            << "\"  (stored value=" << m.at(k) << ")\n";
        m.erase(k);
    }

    out << "\n[MAP STATE — after removals]\n";
    print_map(m, out);
    out << '\n';

    out << "\n[MEMORY] 'map' leaves scope => all key strings and nodes freed "
           "automatically.\n";
}

// =============================================================================
//  Example 2a — std::map<int32_t, std::string*>   (heap-allocated values)
// =============================================================================

static void ex2a_int_to_dynstr(std::ostream& out) {
    section(out, "Example 2a: std::map<int32_t, std::string*>"
                 "  [dynamically allocated string values]");

    out << R"(
[MEMORY MODEL]
  Stack : The map object lives on the caller's stack.
  Heap  : Two separate heap allocations per entry:
            (1) The tree node (via std::allocator) — stores the int32_t key
                and a raw pointer (std::string*, 8 B on 64-bit systems).
            (2) The std::string object created with 'new std::string(...)'.
                The pointer stored in the node points to this object.
  !!! RAII DOES NOT COVER THE POINTEE !!!
          The map destructor frees tree nodes but does NOT follow raw pointers.
          If you erase a node without first deleting the pointed-to string you
          get a memory leak. The pointer stored in the node is overwritten —
          the string's heap block is silently lost.
  Rule  : Always 'delete' the std::string* AFTER (or before) calling erase().
          Best practice for production code: replace std::string* with
          std::unique_ptr<std::string> to automate the cleanup.
)";

    std::map<int32_t, std::string*> m;

    subsection(out, "Insertions");
    const std::pair<int32_t, const char*> inserts[] = {
        {10, "ten"}, {30, "thirty"}, {20, "twenty"}, {40, "forty"}, {50, "fifty"}
    };
    for (const auto& [k, sv] : inserts) {
        std::string* p = new std::string(sv);
        out << "  [ADD]    key=" << k
            << "  value=new std::string(\"" << sv << "\")"
            << "  @" << static_cast<const void*>(p)
            << "  => 2 heap allocations (node + std::string)\n";
        m.emplace(k, p);
    }

    out << "\n[MAP STATE]\n";
    print_map(m, out);
    out << '\n';

    subsection(out, "Removals");
    const int32_t removes[] = {30, 10};
    for (int32_t k : removes) {
        auto it = m.find(k);
        if (it == m.end()) continue;
        std::string* p = it->second;
        out << "  [REMOVE] key=" << k
            << "  value=\"" << *p << "\""
            << "  @" << static_cast<const void*>(p) << '\n'
            << "           Step 1 — erase map iterator  => node freed by "
               "std::allocator\n"
            << "           Step 2 — delete std::string* => string heap block "
               "freed\n";
        m.erase(it);
        delete p;
    }

    out << "\n[MAP STATE — after removals]\n";
    print_map(m, out);
    out << '\n';

    out << "[MEMORY] Manually cleaning up the remaining " << m.size()
        << " string pointer(s) before 'map' goes out of scope:\n";
    for (auto& [k, p] : m) {
        out << "  delete std::string* @" << static_cast<const void*>(p)
            << "  (\"" << *p << "\")\n";
        delete p;
    }
    out << "  'map' leaves scope => remaining nodes freed automatically.\n";
}

// =============================================================================
//  Example 2b — std::map<std::string, std::string*>
// =============================================================================

static void ex2b_str_to_dynstr(std::ostream& out) {
    section(out, "Example 2b: std::map<std::string, std::string*>"
                 "  [dynamically allocated string values]");

    out << R"(
[MEMORY MODEL]
  Stack : The map object lives on the caller's stack.
  Heap  : Up to three distinct heap allocations per entry:
            (1) The tree node (std::allocator).
            (2) The key std::string's internal character buffer, if the key
                string is longer than the SSO threshold (~15 chars).
            (3) The value std::string object created with 'new std::string'.
  !!! SAME OWNERSHIP CAVEAT AS EXAMPLE 2a !!!
          The map destructor frees nodes and key strings (via ~std::string)
          but does NOT follow value pointers. You must delete every value
          std::string* explicitly before (or after) erasing the corresponding
          entry, or before the map is destroyed.
)";

    std::map<std::string, std::string*> m;

    subsection(out, "Insertions");
    const std::pair<const char*, const char*> inserts[] = {
        {"color",  "blue"},
        {"shape",  "circle"},
        {"weight", "heavy"},
        {"size",   "large"},
        {"speed",  "fast"}
    };
    for (const auto& [k, sv] : inserts) {
        std::string* p = new std::string(sv);
        out << "  [ADD]    key=\"" << k
            << "\"  value=new std::string(\"" << sv << "\")"
            << "  @" << static_cast<const void*>(p) << '\n';
        m.emplace(k, p);
    }

    out << "\n[MAP STATE]\n";
    print_map(m, out);
    out << '\n';

    subsection(out, "Removals");
    const char* removes[] = {"shape", "color"};
    for (const char* k : removes) {
        auto it = m.find(k);
        if (it == m.end()) continue;
        std::string* p = it->second;
        out << "  [REMOVE] key=\"" << k
            << "\"  value=\"" << *p << "\""
            << "  @" << static_cast<const void*>(p) << '\n'
            << "           Step 1 — erase map iterator  => node + key string "
               "freed\n"
            << "           Step 2 — delete std::string* => value string freed\n";
        m.erase(it);
        delete p;
    }

    out << "\n[MAP STATE — after removals]\n";
    print_map(m, out);
    out << '\n';

    out << "[MEMORY] Manually cleaning up the remaining " << m.size()
        << " string pointer(s):\n";
    for (auto& [k, p] : m) {
        out << "  delete std::string* @" << static_cast<const void*>(p)
            << "  (\"" << *p << "\")\n";
        delete p;
    }
    out << "  'map' leaves scope => nodes and key strings freed automatically.\n";
}

// =============================================================================
//  Example 3a — std::map<int32_t, Point>   (struct by value)
// =============================================================================

static void ex3a_int_to_point(std::ostream& out) {
    section(out, "Example 3a: std::map<int32_t, Point>  [struct by value]");

    out << R"(
[MEMORY MODEL]
  Stack : The map object lives on the caller's stack.
  Heap  : One heap allocation per entry: the tree node. The Point value
          (two int32_t members = 8 B) is stored inline inside the node —
          no extra pointer or secondary allocation. This keeps every
          key-value pair contiguous in a single heap block per node, which
          is more cache-friendly than a pointer-based approach.
  RAII  : The map destructor calls ~Point() for each stored value.  Point's
          destructor is trivial (compiler-generated, empty body), so the cost
          at erasure time is just the node deallocation. No manual cleanup.
)";

    std::map<int32_t, Point> m;

    subsection(out, "Insertions");
    const std::pair<int32_t, Point> inserts[] = {
        {3, {30, 31}}, {1, {10, 11}}, {5, {50, 51}}, {2, {20, 21}}, {4, {40, 41}}
    };
    for (const auto& [k, v] : inserts) {
        out << "  [ADD]    key=" << k
            << "  value=" << v.to_string()
            << "  => 1 node allocated; Point stored inline (no extra heap)\n";
        m.emplace(k, v);
    }

    out << "\n[MAP STATE]\n";
    print_map(m, out);
    out << '\n';

    subsection(out, "Removals");
    const int32_t removes[] = {3, 5};
    for (int32_t k : removes) {
        out << "  [REMOVE] key=" << k
            << "  value=" << m.at(k).to_string()
            << "  => ~Point() called (trivial), node freed\n";
        m.erase(k);
    }

    out << "\n[MAP STATE — after removals]\n";
    print_map(m, out);
    out << '\n';

    out << "\n[MEMORY] 'map' leaves scope => remaining " << m.size()
        << " node(s) freed by destructor (trivial ~Point() per node).\n";
}

// =============================================================================
//  Example 3b — std::map<std::string, Point>
// =============================================================================

static void ex3b_str_to_point(std::ostream& out) {
    section(out, "Example 3b: std::map<std::string, Point>  [struct by value]");

    out << R"(
[MEMORY MODEL]
  Stack : The map object lives on the caller's stack.
  Heap  : One node per entry. The node holds:
            - The std::string key (possibly with its own internal heap buffer
              when the key length exceeds the SSO threshold).
            - The Point value inline (8 B, no extra pointer).
          ~std::string() cleans up the key's heap buffer if one exists.
          ~Point() is trivial. Both are invoked by the map destructor.
  RAII  : No manual cleanup is required for either keys or values.
)";

    std::map<std::string, Point> m;

    subsection(out, "Insertions");
    const std::pair<const char*, Point> inserts[] = {
        {"origin",    {  0,   0}},
        {"top_left",  {  0, 100}},
        {"top_right", {100, 100}},
        {"bot_left",  {  0,   0}},
        {"bot_right", {100,   0}}
    };
    for (const auto& [k, v] : inserts) {
        out << "  [ADD]    key=\"" << k
            << "\"  value=" << v.to_string() << '\n';
        m.emplace(k, v);
    }

    out << "\n[MAP STATE — ordered lexicographically]\n";
    print_map(m, out);
    out << '\n';

    subsection(out, "Removals");
    const char* removes[] = {"origin", "top_right"};
    for (const char* k : removes) {
        out << "  [REMOVE] key=\"" << k
            << "\"  value=" << m.at(k).to_string() << '\n';
        m.erase(k);
    }

    out << "\n[MAP STATE — after removals]\n";
    print_map(m, out);
    out << '\n';

    out << "\n[MEMORY] 'map' leaves scope => all nodes, key strings, and "
           "inline Points freed automatically.\n";
}

// =============================================================================
//  Example 4a — std::map<int32_t, Person*>   (heap-allocated class)
// =============================================================================

static void ex4a_int_to_person(std::ostream& out) {
    section(out, "Example 4a: std::map<int32_t, Person*>"
                 "  [heap-allocated class]");

    out << R"(
[MEMORY MODEL]
  Stack : The map object lives on the caller's stack.
  Heap  : Two separate heap allocations per entry:
            (1) The tree node (std::allocator) — stores the int32_t key and
                a raw Person* pointer (8 B on 64-bit).
            (2) The Person object itself, created with 'new Person(...)'.
                Person holds a std::string member (name_) which may itself
                allocate a heap buffer when the name exceeds the SSO limit.
  !!! SAME OWNERSHIP CAVEAT AS EXAMPLES 2a/2b !!!
          The map destructor frees tree nodes only. It does NOT call delete
          on any Person*. Failing to delete each Person* before or after
          erasing results in memory leaks and suppresses ~Person() calls.
  Rule  : Erase the iterator first (frees the node), then delete the Person*
          (calls ~Person(), which calls ~std::string() on name_).
          Production alternative: std::unique_ptr<Person> as the value type.
  Note  : Person is intentionally non-copyable. Only pointer (or move)
          semantics are allowed, which matches the map<int32_t,Person*> model.
)";

    std::map<int32_t, Person*> m;

    subsection(out, "Insertions");
    using Row = std::tuple<int32_t, const char*, int32_t>;
    const Row inserts[] = {
        {3, "Charlie", 35}, {1, "Alice", 30}, {5, "Eve",   28},
        {2, "Bob",     25}, {4, "Dave",  40}
    };
    for (const auto& [k, name, age] : inserts) {
        Person* p = new Person(name, age);
        out << "  [ADD]    key=" << k
            << "  value=new Person(\"" << name << "\", " << age << ")"
            << "  @" << static_cast<const void*>(p)
            << "  => 2+ heap allocations (node + Person + possible name_ buf)\n";
        m.emplace(k, p);
    }

    out << "\n[MAP STATE]\n";
    print_map(m, out);
    out << '\n';

    subsection(out, "Removals");
    const int32_t removes[] = {5, 1};
    for (int32_t k : removes) {
        auto it = m.find(k);
        if (it == m.end()) continue;
        Person* p = it->second;
        out << "  [REMOVE] key=" << k
            << "  person=" << p->to_string()
            << "  @" << static_cast<const void*>(p) << '\n'
            << "           Step 1 — erase map iterator  => node freed\n"
            << "           Step 2 — delete Person*      => ~Person() called,\n"
            << "                                           name_ string freed,\n"
            << "                                           Person block freed\n";
        m.erase(it);
        delete p;
    }

    out << "\n[MAP STATE — after removals]\n";
    print_map(m, out);
    out << '\n';

    out << "[MEMORY] Manually cleaning up the remaining " << m.size()
        << " Person pointer(s) before 'map' goes out of scope:\n";
    for (auto& [k, p] : m) {
        out << "  delete Person* key=" << k
            << "  @" << static_cast<const void*>(p)
            << "  (name=\"" << p->name() << "\")\n";
        delete p;
    }
    out << "  'map' leaves scope => remaining nodes freed automatically.\n";
}

// =============================================================================
//  Example 4b — std::map<std::string, Person*>
// =============================================================================

static void ex4b_str_to_person(std::ostream& out) {
    section(out, "Example 4b: std::map<std::string, Person*>"
                 "  [heap-allocated class]");

    out << R"(
[MEMORY MODEL]
  Stack : The map object lives on the caller's stack.
  Heap  : Up to four distinct heap allocations per entry:
            (1) The tree node (std::allocator).
            (2) The key std::string's internal character buffer (when the key
                is longer than the SSO threshold, typically ~15 chars).
            (3) The Person object created with 'new Person(...)'.
            (4) The Person::name_ std::string's internal buffer (again, only
                when the name is longer than the SSO threshold).
  !!! SAME OWNERSHIP CAVEAT AS EXAMPLE 4a !!!
          The map destructor frees nodes and key strings automatically but
          does NOT delete any Person*. Explicit cleanup is required.
)";

    std::map<std::string, Person*> m;

    subsection(out, "Insertions");
    using Row = std::tuple<const char*, const char*, int32_t>;
    const Row inserts[] = {
        {"charlie", "Charlie", 35}, {"alice",   "Alice", 30},
        {"eve",     "Eve",     28}, {"bob",     "Bob",   25},
        {"dave",    "Dave",    40}
    };
    for (const auto& [k, name, age] : inserts) {
        Person* p = new Person(name, age);
        out << "  [ADD]    key=\"" << k
            << "\"  value=new Person(\"" << name << "\", " << age << ")"
            << "  @" << static_cast<const void*>(p) << '\n';
        m.emplace(k, p);
    }

    out << "\n[MAP STATE — ordered lexicographically]\n";
    print_map(m, out);
    out << '\n';

    subsection(out, "Removals");
    const char* removes[] = {"eve", "charlie"};
    for (const char* k : removes) {
        auto it = m.find(k);
        if (it == m.end()) continue;
        Person* p = it->second;
        out << "  [REMOVE] key=\"" << k
            << "\"  person=" << p->to_string()
            << "  @" << static_cast<const void*>(p) << '\n'
            << "           Step 1 — erase map iterator  => node + key string "
               "freed\n"
            << "           Step 2 — delete Person*      => ~Person() called,\n"
            << "                                           name_ freed, "
               "Person block freed\n";
        m.erase(it);
        delete p;
    }

    out << "\n[MAP STATE — after removals]\n";
    print_map(m, out);
    out << '\n';

    out << "[MEMORY] Manually cleaning up the remaining " << m.size()
        << " Person pointer(s):\n";
    for (auto& [k, p] : m) {
        out << "  delete Person* key=\"" << k
            << "\"  @" << static_cast<const void*>(p)
            << "  (name=\"" << p->name() << "\")\n";
        delete p;
    }
    out << "  'map' leaves scope => remaining nodes and key strings freed "
           "automatically.\n";
}

// =============================================================================
//  Example 5a — std::map<int32_t, Point2*>   (heap-allocated struct)
//
//  Demonstrates that a struct used via pointer follows the EXACT SAME
//  ownership pattern as a class (Person*).  The struct/class distinction
//  in C++ is purely syntactic (default access specifier); it has no effect
//  on allocation or ownership semantics.
// =============================================================================

static void ex5a_int_to_point2(std::ostream& out) {
    section(out, "Example 5a: std::map<int32_t, Point2*>"
                 "  [heap-allocated struct — compare with 4a]");

    out << R"(
[MEMORY MODEL — identical pattern to Example 4a (Person*)]
  Stack : The map object lives on the caller's stack.
  Heap  : Exactly two heap allocations per entry — no more, no less:
            (1) The tree node (std::allocator) — stores the int32_t key and
                a raw Point2* pointer (8 B on 64-bit).
            (2) The Point2 object created with 'new Point2(x, y)'.
                Point2 has no std::string member, so there is no tertiary
                allocation — unlike Person* where name_ may add one more.
  !!! RAII DOES NOT COVER THE POINTEE !!!
          struct vs. class makes no difference here: the map destructor
          frees tree nodes but does NOT call delete on stored Point2*
          pointers.  The same two-step removal pattern is mandatory:
            Step 1 — erase the iterator      => node freed
            Step 2 — delete the Point2*      => Point2 object freed
  Comparison with Point (examples 3a/3b):
          Point  is stored BY VALUE inside the node → 1 allocation, RAII.
          Point2 is stored BY POINTER separately   → 2 allocations, manual.
          The struct keyword is the same in both cases; the allocation model
          is entirely determined by how the type is used, not what it is.
)";

    std::map<int32_t, Point2*> m;

    subsection(out, "Insertions");
    const std::pair<int32_t, Point2*> inserts[] = {
        {3, new Point2(30, 31)},
        {1, new Point2(10, 11)},
        {5, new Point2(50, 51)},
        {2, new Point2(20, 21)},
        {4, new Point2(40, 41)}
    };
    for (const auto& [k, p] : inserts) {
        out << "  [ADD]    key=" << k
            << "  value=new Point2" << p->to_string()
            << "  @" << static_cast<const void*>(p)
            << "  => 2 heap allocations (node + Point2)\n";
        m.emplace(k, p);
    }

    out << "\n[MAP STATE]\n";
    print_map(m, out);
    out << '\n';

    subsection(out, "Removals");
    const int32_t removes[] = {5, 1};
    for (int32_t k : removes) {
        auto it = m.find(k);
        if (it == m.end()) continue;
        Point2* p = it->second;
        out << "  [REMOVE] key=" << k
            << "  point=" << p->to_string()
            << "  @" << static_cast<const void*>(p) << '\n'
            << "           Step 1 — erase map iterator  => node freed\n"
            << "           Step 2 — delete Point2*      => ~Point2() called "
               "(trivial), Point2 block freed\n";
        m.erase(it);
        delete p;
    }

    out << "\n[MAP STATE — after removals]\n";
    print_map(m, out);
    out << '\n';

    out << "[MEMORY] Manually cleaning up the remaining " << m.size()
        << " Point2 pointer(s) before 'map' goes out of scope:\n";
    for (auto& [k, p] : m) {
        out << "  delete Point2* key=" << k
            << "  @" << static_cast<const void*>(p)
            << "  " << p->to_string() << '\n';
        delete p;
    }
    out << "  'map' leaves scope => remaining nodes freed automatically.\n";
}

// =============================================================================
//  Example 5b — std::map<std::string, Point2*>
// =============================================================================

static void ex5b_str_to_point2(std::ostream& out) {
    section(out, "Example 5b: std::map<std::string, Point2*>"
                 "  [heap-allocated struct — compare with 4b]");

    out << R"(
[MEMORY MODEL — identical pattern to Example 4b (Person*)]
  Stack : The map object lives on the caller's stack.
  Heap  : Up to three distinct heap allocations per entry:
            (1) The tree node (std::allocator).
            (2) The key std::string's internal character buffer (SSO overflow,
                for keys longer than ~15 chars — these keys are short enough
                that SSO likely covers them, so allocation (2) may not occur).
            (3) The Point2 object created with 'new Point2(x, y)'.
                Point2 holds no std::string member, so exactly one allocation
                for the object itself — simpler than Person* (which may have
                an additional name_ buffer).
  !!! SAME OWNERSHIP CAVEAT AS ALL PREVIOUS POINTER EXAMPLES !!!
          The map destructor frees nodes and key strings automatically but
          does NOT delete stored Point2* values. Explicit cleanup is required.
  Key takeaway:
          Whether the value type is declared with 'struct' or 'class' has
          zero impact on how it must be managed in a map.  Point2 and Person
          are both non-copyable types with pointer ownership — their maps
          are written and cleaned up in exactly the same way.
)";

    std::map<std::string, Point2*> m;

    subsection(out, "Insertions");
    const std::pair<const char*, Point2*> inserts[] = {
        {"origin",    new Point2(  0,   0)},
        {"top_left",  new Point2(  0, 100)},
        {"top_right", new Point2(100, 100)},
        {"bot_left",  new Point2(  0,   0)},
        {"bot_right", new Point2(100,   0)}
    };
    for (const auto& [k, p] : inserts) {
        out << "  [ADD]    key=\"" << k
            << "\"  value=new Point2" << p->to_string()
            << "  @" << static_cast<const void*>(p) << '\n';
        m.emplace(k, p);
    }

    out << "\n[MAP STATE — ordered lexicographically]\n";
    print_map(m, out);
    out << '\n';

    subsection(out, "Removals");
    const char* removes[] = {"origin", "top_right"};
    for (const char* k : removes) {
        auto it = m.find(k);
        if (it == m.end()) continue;
        Point2* p = it->second;
        out << "  [REMOVE] key=\"" << k
            << "\"  point=" << p->to_string()
            << "  @" << static_cast<const void*>(p) << '\n'
            << "           Step 1 — erase map iterator  => node + key string "
               "freed\n"
            << "           Step 2 — delete Point2*      => ~Point2() called "
               "(trivial), Point2 block freed\n";
        m.erase(it);
        delete p;
    }

    out << "\n[MAP STATE — after removals]\n";
    print_map(m, out);
    out << '\n';

    out << "[MEMORY] Manually cleaning up the remaining " << m.size()
        << " Point2 pointer(s):\n";
    for (auto& [k, p] : m) {
        out << "  delete Point2* key=\"" << k
            << "\"  @" << static_cast<const void*>(p)
            << "  " << p->to_string() << '\n';
        delete p;
    }
    out << "  'map' leaves scope => remaining nodes and key strings freed "
           "automatically.\n";
}

// =============================================================================
//  main
// =============================================================================

int main() {
    const std::string output_path = "test_map2_output.txt";
    std::ofstream out(output_path);
    if (!out.is_open()) {
        std::cerr << "ERROR: cannot open '" << output_path
                  << "' for writing. Run the executable from the TESTS/ "
                     "directory.\n";
        return 1;
    }

    out << "std::map test suite (extended)\n"
        << "===============================\n"
        << "Ten examples: 5 value types x 2 key types (int32_t, std::string).\n"
        << "Examples 1-4 are identical to test_map.cpp.\n"
        << "Examples 5a/5b add Point2* (heap-allocated struct) to demonstrate\n"
        << "that struct vs. class is irrelevant to map ownership semantics:\n"
        << "what matters is BY VALUE (inline, RAII) vs. BY POINTER (heap,\n"
        << "manual delete).\n"
        << "Map states are printed as 4-space-indented JSON-like objects.\n";

    ex1a_int_to_int(out);
    ex1b_str_to_int(out);
    ex2a_int_to_dynstr(out);
    ex2b_str_to_dynstr(out);
    ex3a_int_to_point(out);
    ex3b_str_to_point(out);
    ex4a_int_to_person(out);
    ex4b_str_to_person(out);
    ex5a_int_to_point2(out);
    ex5b_str_to_point2(out);

    out << "\n\n[DONE] All 10 examples completed successfully.\n";
    std::cout << "Output written to: " << output_path << '\n';
    return 0;
}
