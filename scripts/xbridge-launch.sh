#!/usr/bin/env bash
# Per-project xBridge MCP launcher.
#
# Reads XAI_API_KEY from the CALLING PROJECT's own .env so every project uses its
# own key (isolation + per-project cost/blast-radius). The .mcp.json that invokes
# this script holds NO secret and is safe to commit.
#
# Project dir resolution order:  $1 (explicit arg)  >  $XBRIDGE_PROJECT  >  $PWD
set -euo pipefail

GROK_HOME="/home/supremeleader/mylab/GROK"
PROJECT_DIR="${1:-${XBRIDGE_PROJECT:-$PWD}}"

if [ -f "$PROJECT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$PROJECT_DIR/.env"
  set +a
fi

if [ -z "${XAI_API_KEY:-}" ]; then
  echo "xbridge-launch: XAI_API_KEY not set. Add a per-project key to $PROJECT_DIR/.env" >&2
  exit 1
fi

# cwd = project dir so .grok_sessions/ stays isolated per project
cd "$PROJECT_DIR"
exec "$GROK_HOME/venv/bin/python" "$GROK_HOME/run_server.py"
