#!/bin/bash
# xBridge gate: full pytest suite against this checkout's code.
# Venv: ./.venv, else the main checkout's (worktrees share it). Create with:
#   python3.11 -m venv .venv && .venv/bin/pip install -e ".[dev,cloud]"
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
if [ ! -x "$PY" ]; then
  main="$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"
  PY="$main/.venv/bin/python"
fi
PYTHONPATH="$PWD" "$PY" -m pytest -q -p no:cacheprovider
