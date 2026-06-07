#!/bin/bash
# xBridge MCP — Deploy sites to Cloudflare Pages
# Requires: wrangler (npx wrangler) + CF_API_TOKEN env var
# First-time setup: create Pages projects in CF dashboard, then run this script.
# Usage: bash scripts/deploy.sh

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Deploying to Cloudflare Pages ==="

# Deploy xbrdg.com (token landing page)
echo "→ Deploying xbrdg-site/ → xbrdg-com (Cloudflare Pages)"
npx --yes wrangler pages deploy "$REPO_ROOT/xbrdg-site/" \
  --project-name xbrdg-com \
  --commit-dirty=true

# Deploy xbridgemcp.com (product site)
echo "→ Deploying site/ → xbridgemcp-com (Cloudflare Pages)"
npx --yes wrangler pages deploy "$REPO_ROOT/site/" \
  --project-name xbridgemcp-com \
  --commit-dirty=true

echo ""
echo "=== Deploy complete ==="
echo "  https://xbrdg.com         → token landing page"
echo "  https://xbridgemcp.com    → product site"
echo ""
echo "  Custom domains must be configured once in Cloudflare Pages dashboard."
