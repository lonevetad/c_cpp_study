PYTHON := $(shell command -v python3 2>/dev/null || command -v python 2>/dev/null)

FCPP_ROOT := fcpp_clone_GITIGNORE_ME

PKG_DIR  := fcpp_py
LIB_NAME := _fcpp_core
OBJ_DIR  := build

# ── Platform detection ────────────────────────────────────────────────────────
# $(OS) is set to Windows_NT by Windows (including MSYS2).
# uname -s gives Darwin on macOS, Linux on Linux.
UNAME_S := $(shell uname -s 2>/dev/null)

ifeq ($(OS),Windows_NT)
    # Windows (MSYS2 / MinGW): produce DLL; LLD required (BFD crashes on fcpp COMDAT tables)
    LIB            := $(PKG_DIR)/$(LIB_NAME).dll
    LDFLAGS        := -shared -static-libgcc -static-libstdc++ -Wl,--gc-sections -fuse-ld=lld
    WINPTHREAD_DST := $(PKG_DIR)/libwinpthread-1.dll
    PREFIX         := $(if $(MSYSTEM_PREFIX),$(MSYSTEM_PREFIX),/ucrt64)
    RUNTIME_TARGET := $(WINPTHREAD_DST)
    CLEAN_RUNTIME   = rm -f "$(WINPTHREAD_DST)"
else ifeq ($(UNAME_S),Darwin)
    # macOS: produce dylib; Apple ld64 (no --gc-sections, no -static-libgcc)
    LIB            := $(PKG_DIR)/$(LIB_NAME).dylib
    LDFLAGS        := -dynamiclib -Wl,-dead_strip
    RUNTIME_TARGET :=
    CLEAN_RUNTIME   = :
else
    # Linux / other POSIX: produce .so; embed GCC runtime statically.
    # Use LLD when available (recommended for large fcpp template stacks).
    LIB            := $(PKG_DIR)/$(LIB_NAME).so
    _LLD           := $(shell command -v lld 2>/dev/null)
    ifneq ($(_LLD),)
        LDFLAGS    := -shared -static-libgcc -static-libstdc++ -Wl,--gc-sections -fuse-ld=lld
    else
        LDFLAGS    := -shared -static-libgcc -static-libstdc++ -Wl,--gc-sections
    endif
    RUNTIME_TARGET :=
    CLEAN_RUNTIME   = :
endif

# Simulation compile-time parameters (override: make DEVICES=50 all)
DEVICES ?= 100
SIDE    ?= 200
HEIGHT  ?= 10
COMM    ?= 50
DIM     ?= 3
STATES  ?= 8

SIM_DEFINES := \
    -DFCPP_PY_DEVICES=$(DEVICES) \
    -DFCPP_PY_SIDE=$(SIDE) \
    -DFCPP_PY_HEIGHT=$(HEIGHT) \
    -DFCPP_PY_COMM=$(COMM) \
    -DFCPP_PY_DIM=$(DIM) \
    -DFCPP_PY_STATE_SIZE=$(STATES)
CXXSTD     ?= c++26
CXXSTD_SIM ?= c++26

CXXFLAGS     := -std=$(CXXSTD) -O2 -Wall -Wextra -fPIC
CXXFLAGS_SIM := -std=$(CXXSTD_SIM) -O2 -fPIC -ffunction-sections -fdata-sections
CPPFLAGS     := -MMD -MP \
                -I $(FCPP_ROOT)/src \
                -I $(FCPP_ROOT)/src/external

# Sources: bridge.cpp is fast; simulation.cpp is slow (full fcpp template stack)
SRCS_FAST := src/bridge.cpp
SRCS_SIM  := src/simulation.cpp
SRCS      := $(SRCS_FAST) $(SRCS_SIM)

OBJS_FAST := $(patsubst src/%.cpp, $(OBJ_DIR)/%.o, $(SRCS_FAST))
OBJS_SIM  := $(patsubst src/%.cpp, $(OBJ_DIR)/%.o, $(SRCS_SIM))
OBJS      := $(OBJS_FAST) $(OBJS_SIM)
DEPS      := $(OBJS:.o=.d)

.PHONY: all test clean

all: $(LIB) $(RUNTIME_TARGET)

$(LIB): $(OBJS)
	@mkdir -p $(dir $@)
	$(CXX) $(LDFLAGS) -o $@ $^

# Fast sources: full warnings
$(OBJS_FAST): $(OBJ_DIR)/%.o: src/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) -c $< -o $@

# Simulation source: no warnings (fcpp template noise), plus SIM_DEFINES
$(OBJS_SIM): $(OBJ_DIR)/%.o: src/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS_SIM) $(CPPFLAGS) $(SIM_DEFINES) -c $< -o $@

ifeq ($(OS),Windows_NT)
$(WINPTHREAD_DST): $(LIB)
	@dll=$$(command -v libwinpthread-1.dll 2>/dev/null \
	       || find "$(PREFIX)/bin" 2>/dev/null -name libwinpthread-1.dll | head -1); \
	 if [ -n "$$dll" ]; then mkdir -p "$(dir $@)"; cp -f "$$dll" "$@"; \
	 else echo "Warning: libwinpthread-1.dll not found — add MSYS2 bin to PATH"; fi
endif

-include $(DEPS)

test: all
	"$(PYTHON)" -m pytest tests/ -v

clean:
	rm -rf $(OBJ_DIR) $(LIB)
	$(CLEAN_RUNTIME)
