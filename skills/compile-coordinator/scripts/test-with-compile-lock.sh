#!/usr/bin/env bash
set -euo pipefail

dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT
wrapper=${1:-"$(dirname "$0")/with-compile-lock.sh"}

COMPILE_LOCK_FILE="$dir/lock" COMPILE_JOBS=2 bash "$wrapper" \
  bash -c '[[ $BUILD_JOBS == 2 && $CARGO_BUILD_JOBS == 2 && $CMAKE_BUILD_PARALLEL_LEVEL == 2 && $CTEST_PARALLEL_LEVEL == 2 && $MAKEFLAGS == *-j2* ]]'
! COMPILE_JOBS=invalid bash "$wrapper" true 2>/dev/null

# The default never exceeds the cgroup CPU quota.
if [[ -r /sys/fs/cgroup/cpu.max ]] && read -r quota period < /sys/fs/cgroup/cpu.max && [[ $quota =~ ^[0-9]+$ ]]; then
  limit=$(( (quota + period - 1) / period ))
  COMPILE_LOCK_FILE="$dir/lock" bash "$wrapper" bash -c '(( BUILD_JOBS <= $1 ))' _ "$limit" 2>/dev/null
fi

# Bazel gets the limits right after its command, before the caller's own flags.
mkdir "$dir/bin"
printf '#!/usr/bin/env bash\nprintf "%%s\\n" "$@" > "%s/bazel-args"\n' "$dir" > "$dir/bin/bazel"
chmod +x "$dir/bin/bazel"
COMPILE_LOCK_FILE="$dir/lock" COMPILE_JOBS=3 bash "$wrapper" "$dir/bin/bazel" --output_base=/x build --config=a //t 2>/dev/null
[[ $(sed -n '1,3p' "$dir/bazel-args") == $'--output_base=/x\nbuild\n--jobs=3' ]]
grep -qx -- '--local_resources=cpu=3' "$dir/bazel-args"
[[ $(tail -2 "$dir/bazel-args") == $'--config=a\n//t' ]]
COMPILE_LOCK_FILE="$dir/lock" COMPILE_JOBS=3 bash "$wrapper" "$dir/bin/bazel" info 2>/dev/null
[[ $(cat "$dir/bazel-args") == info ]]

COMPILE_LOCK_FILE="$dir/lock" bash "$wrapper" bash -c 'echo a-start >> "$1"; sleep 0.2; echo a-end >> "$1"' _ "$dir/events" 2>/dev/null &
first=$!
sleep 0.05
COMPILE_LOCK_FILE="$dir/lock" bash "$wrapper" bash -c 'echo b-start >> "$1"; echo b-end >> "$1"' _ "$dir/events" 2>/dev/null &
second=$!
wait "$first" "$second"
[[ $(cat "$dir/events") == $'a-start\na-end\nb-start\nb-end' ]]
echo "compile-coordinator self-test passed"
