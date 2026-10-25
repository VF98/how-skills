---
name: compile-coordinator
description: Coordinate CPU- and memory-heavy builds across multiple Codex agents on one machine. Use whenever an agent needs to compile, link, package, run a build command, or execute build-heavy tests while other agents may work concurrently; serialize builds with a shared lock and default each build to three quarters of the CPU quota, within the memory limit.
---

# Compile Coordinator

Run every resource-heavy build through the bundled wrapper. The machine-wide lock permits one build at a time. The active build uses 75% of the CPU budget and no more jobs than fit in 75% of memory at 2 GiB each. On macOS, the wrapper reads the local CPU count and `sysctl hw.memsize`. On Linux it also respects CPU affinity and cgroup CPU/memory limits. The lock uses Python 3 standard-library `fcntl`, so GNU `flock` is not required on the Mac.

## Run a build

1. Remove explicit job flags such as `-j`, `--jobs`, or `--parallel` from the build command. Preserve a smaller user-requested limit by setting `COMPILE_JOBS` instead.
2. Run:

```bash
bash "${CODEX_HOME:-$HOME/.codex}/skills/compile-coordinator/scripts/with-compile-lock.sh" <command> [args...]
```

Examples:

```bash
bash "${CODEX_HOME:-$HOME/.codex}/skills/compile-coordinator/scripts/with-compile-lock.sh" cmake --build build
bash "${CODEX_HOME:-$HOME/.codex}/skills/compile-coordinator/scripts/with-compile-lock.sh" cargo test
COMPILE_JOBS=4 bash "${CODEX_HOME:-$HOME/.codex}/skills/compile-coordinator/scripts/with-compile-lock.sh" ninja -C build
```

Tell the user when waiting for another build. Do not bypass the wrapper because the lock is busy; waiting is the coordination mechanism.

The wrapper exports limits understood by GNU Make, CMake, CTest, Cargo, and pytest-xdist, and directly limits Ninja and Bazel (`--jobs` and `--local_resources` after the command, so a later `--config` still overrides them). Use `COMPILE_JOBS` to override the CPU budget and `COMPILE_JOB_MEMORY_MB` to change the per-job memory estimate. Use `COMPILE_LOCK_FILE` only when intentionally creating a separate resource pool.

Also run long, memory-heavy test topologies (for example a multi-process end-to-end gate) through the wrapper with `COMPILE_JOBS=1`, so no build competes with them.

Do not wrap lightweight commands such as formatting, linting, source generation, or test discovery unless they invoke a compiler.
