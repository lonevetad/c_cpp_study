# ─────────────────────────────────────────────────────────────────────────────
# Makefile — expr_eval_py   (C ABI bridge → Python ctypes)
# Targets:  all    build the shared library + copy runtime deps (default)
#           test   run pytest unit tests
#           clean  remove generated files
#
# Supports: Windows 11 (MSYS2 UCRT64)  and  Linux (Mint / Ubuntu, GCC ≥ 15)
# ─────────────────────────────────────────────────────────────────────────────

# ── Compiler & base flags ─────────────────────────────────────────────────────
CXX      := g++
CXXFLAGS := -std=c++26 -O2 -Wall -Wextra

# ── Platform detection ────────────────────────────────────────────────────────
# $(OS) == 'Windows_NT' on all Windows hosts (MSYS2, Cygwin, native shell);
# unset or empty on Linux / macOS.
ifeq ($(OS),Windows_NT)
    # Windows: produce a DLL; embed GCC runtime statically.
    # libwinpthread-1.dll cannot be embedded (libstdc++ references it internally);
    # copy it next to the DLL so Python finds it via os.add_dll_directory().
    LIB_SUFFIX    := .dll
    LDFLAGS       := -shared -static-libgcc -static-libstdc++
    WINPTHREAD_SRC := /c/msys64/ucrt64/bin/libwinpthread-1.dll
    WINPTHREAD_DST := expr_eval_py/libwinpthread-1.dll
    COPY_RUNTIME   = cp -f "$(WINPTHREAD_SRC)" "$(WINPTHREAD_DST)" \
                     && echo "Copied runtime: $(WINPTHREAD_DST)"
    CLEAN_RUNTIME  = rm -f "$(WINPTHREAD_DST)"
    PYTHON        := $(shell py -c "import sys; print(sys.executable)")
    # $(shell where.exe python 2>/dev/null || where.exe python3 2>/dev/null)
else
    # Linux: produce a .so; -fPIC is mandatory for position-independent shared libs.
    # -static-libgcc / -static-libstdc++ embed the GCC runtime so the .so is
    # portable across distros without requiring a matching libstdc++ version.
    LIB_SUFFIX    := .so
    CXXFLAGS      += -fPIC
    LDFLAGS       := -shared -static-libgcc -static-libstdc++
    COPY_RUNTIME   = :
    CLEAN_RUNTIME  = :
    PYTHON        := $(shell which python 2>/dev/null || which python3 2>/dev/null)
endif
ifeq ($(PYTHON),)
    $(error Python not found on PATH. Install Python and ensure 'python' or 'python3' is accessible.)
endif

# ── Path to the C++ library (sibling directory) ───────────────────────────────
EXPR_EVAL_ROOT := ../expr_eval/multiclass
INC := -I $(EXPR_EVAL_ROOT)/include

# ── C++ library source files (same set as multiclass/Makefile) ───────────────
LIB_SRCS := \
    $(EXPR_EVAL_ROOT)/src/types/Value.cpp               \
    $(EXPR_EVAL_ROOT)/src/ast/AstNode.cpp               \
    $(EXPR_EVAL_ROOT)/src/ast/BinaryNode.cpp            \
    $(EXPR_EVAL_ROOT)/src/ast/UnaryNode.cpp             \
    $(EXPR_EVAL_ROOT)/src/ast/TerminalNode.cpp          \
    $(EXPR_EVAL_ROOT)/src/ast/ExprNode.cpp              \
    $(EXPR_EVAL_ROOT)/src/ast/logical/NotNode.cpp       \
    $(EXPR_EVAL_ROOT)/src/ast/arithmetic/NegateNode.cpp \
    $(EXPR_EVAL_ROOT)/src/parser/Parser.cpp             \
    $(EXPR_EVAL_ROOT)/src/ExpressionEvaluator.cpp

# ── Output: shared library lands inside the Python package directory ──────────
# __init__.py detects the correct suffix at import time via sys.platform.
LIB := expr_eval_py/_expr_eval_core$(LIB_SUFFIX)

# ─────────────────────────────────────────────────────────────────────────────

.PHONY: all test clean

all: $(LIB)
	@$(COPY_RUNTIME)

$(LIB): bridge/bridge.cpp $(LIB_SRCS)
	$(CXX) $(CXXFLAGS) $(LDFLAGS) $(INC) $^ -o $@
	@echo "Built: $@"

# Run pytest from this directory so expr_eval_py/ is found as a package.
test: all
	$(PYTHON) -m pytest tests/ -v

# Remove the shared library and (on Windows) the copied runtime.
clean:
	rm -f $(LIB)
	@$(CLEAN_RUNTIME)
