# Memory Index

- [FCPP exercises project state](project_fcpp_exercises.md) — build system, file layout, run command, CMakeLists foreach pattern
- [FCPP export_list rule](project_fcpp_export_list_rule.md) — must add foo_t to main_t's export_list when foo uses nbr(); common compile error pattern
- [fcpp_bridge project state](project_fcpp_bridge.md) — 675 tests; standalone repo at ../fcpp_bridge/ (flat layout); FCPP_INCLUDE_PATH env var; compiler path bug fixed
- [fcpp_bridge import rule](feedback_fcpp_bridge_imports.md) — use relative/absolute imports in sub-packages; bare names break under PYTHONPATH=src
- [Clarification style](feedback_clarification_style.md) — ask questions for ambiguous parts; always offer "go autonomous + log decisions" as an option
- [User review 2026-05-28](feedback_user_review_2026-05-28.md) — positive review; autonomous multi-step approach validated; flag C++ API caveats for manual review
- [Cross-platform build patterns](project_build_cross_platform.md) — Makefile 3-way OS detection, .dylib/.so/.dll, macOS ld64 flags, CMake X11 guard
- [Python executable preference](feedback_python_executable.md) — use /usr/bin/python3; prefer `pip install -e .` over PYTHONPATH=src; venv path only for pytest
- [text_dashboard.py print→logging skipped](feedback_text_dashboard_untouched.md) — skipped for print→logging pass only; other refactorings are fair game
- [C++ modern standards reference](reference_cpp_modern.md) — C++14 focus; lambdas, RAII, smart ptrs, templates; skill: `/cpp-modern` (~/.claude/commands/cpp-modern.md)
- [FCPP library reference](reference_fcpp_library.md) — all primitives, CALL macro, export_list, Python DSL rules; skill: `/fcpp-library` (.claude/commands/fcpp-library.md)
