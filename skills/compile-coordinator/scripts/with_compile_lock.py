#!/usr/bin/env python3
"""Run one build at a time using the current Mac or Linux resource budget."""

import fcntl
import math
import os
from pathlib import Path
import signal
import subprocess
import sys


def read_text(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return ""


def budgets():
    online = os.cpu_count() or 1
    cpus = online
    if sys.platform == "darwin":
        memory = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True))
    else:
        if hasattr(os, "sched_getaffinity"):
            cpus = min(cpus, len(os.sched_getaffinity(0)))
        limits = read_text("/sys/fs/cgroup/cpu.max").split()
        if len(limits) != 2:
            limits = [read_text("/sys/fs/cgroup/cpu/cpu.cfs_quota_us"),
                      read_text("/sys/fs/cgroup/cpu/cpu.cfs_period_us")]
        if all(value.isdigit() and int(value) > 0 for value in limits):
            cpus = min(cpus, math.ceil(int(limits[0]) / int(limits[1])))
        memory = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
        for path in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
            limit = read_text(path)
            if limit.isdigit() and int(limit) > 0:
                memory = min(memory, int(limit))
                break
    return online, max(1, cpus), max(1, memory // 1048576)


def positive_integer(name, default):
    value = os.environ.get(name, str(default))
    if not value.isdigit() or int(value) <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def main():
    command = sys.argv[1:]
    if not command:
        print("usage: with-compile-lock.sh <build-command> [args...]", file=sys.stderr)
        return 2
    online, cpus, memory_mb = budgets()
    try:
        job_memory = positive_integer("COMPILE_JOB_MEMORY_MB", 2048)
        jobs = positive_integer("COMPILE_JOBS", max(1, min(cpus * 3 // 4, memory_mb * 3 // 4 // job_memory)))
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    env = os.environ.copy()
    for key in ("BUILD_JOBS", "CARGO_BUILD_JOBS", "CMAKE_BUILD_PARALLEL_LEVEL",
                "CTEST_PARALLEL_LEVEL", "PYTEST_XDIST_AUTO_NUM_WORKERS"):
        env[key] = str(jobs)
    env["MAKEFLAGS"] = f"{env.get('MAKEFLAGS', '')} -j{jobs}".strip()
    tool = Path(command[0]).name
    if tool == "ninja":
        command[1:1] = ["-j", str(jobs)]
    elif tool in ("bazel", "bazelisk"):
        for index, arg in enumerate(command[1:], 1):
            if not arg.startswith("-"):
                if arg in ("build", "test", "run", "coverage"):
                    command[index + 1:index + 1] = [f"--jobs={jobs}", f"--local_resources=cpu={jobs}",
                                                   f"--local_resources=memory={memory_mb // 2}"]
                break
    default_lock = Path(env.get("XDG_RUNTIME_DIR", "/tmp")) / f"codex-compile-{os.getuid()}.lock"
    lock_path = env.get("COMPILE_LOCK_FILE", str(default_lock))
    fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(f"compile-coordinator: another build is active; waiting for {lock_path}", file=sys.stderr)
            fcntl.flock(lock, fcntl.LOCK_EX)
        print(f"compile-coordinator: acquired lock; running with {jobs} jobs "
              f"(CPU budget {cpus} of {online} online, memory budget {memory_mb} MiB)", file=sys.stderr)
        try:
            child = subprocess.Popen(command, env=env, close_fds=True, start_new_session=True)
        except OSError as error:
            print(f"compile-coordinator: {error}", file=sys.stderr)
            return 127
        def forward(signum, _frame):
            try:
                os.killpg(child.pid, signum)
            except ProcessLookupError:
                pass
        original = {sig: signal.signal(sig, forward) for sig in (signal.SIGINT, signal.SIGTERM)}
        try:
            status = child.wait()
        finally:
            for sig, handler in original.items():
                signal.signal(sig, handler)
        return status if status >= 0 else 128 - status


if __name__ == "__main__":
    sys.exit(main())
