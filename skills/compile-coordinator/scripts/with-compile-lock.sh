#!/usr/bin/env bash
set -euo pipefail
exec python3 "$(dirname "$0")/with_compile_lock.py" "$@"
