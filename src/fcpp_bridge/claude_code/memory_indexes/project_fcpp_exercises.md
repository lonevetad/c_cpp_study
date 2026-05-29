---
name: project-fcpp-exercises
description: State and key facts about the fcpp-exercises C++ project the user is working on
metadata: 
  node_type: memory
  type: project
  originSessionId: 3bbcec65-fb79-4f48-bf88-dc1ba62b0b6a
---

Project lives at: `src/fcpp_py_porting/fcpp_clone_GITIGNORE_ME/fcpp-exercises/`

- Source files go in `run/`, registered in `CMakeLists.txt` via `fcpp_target(./run/<name>.cpp ON)`.
- The CMakeLists.txt uses a `foreach` loop over a list `ALL_TARGETS` (stem names, no `.cpp`) to call `fcpp_target` for each.
- Build/run command: `./make.sh gui run -O <target_stem>` (e.g. `exercises`, `exercises_4`).
- The fcpp submodule is inside `fcpp/` (git submodule, read-only).

**Why:** User is working through FCPP aggregate-computing exercises, adding new `.cpp` files alongside the original `exercises.cpp`.

**How to apply:** When helping with new exercise files, remind user to add the stem to `ALL_TARGETS` in CMakeLists.txt.
