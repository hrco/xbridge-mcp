#!/bin/bash
# xBridge gate: full pytest suite in the project venv (python3.11 -m venv .venv && .venv/bin/pip install -e ".[dev,cloud]")
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python -m pytest -q -p no:cacheprovider
