#!/bin/bash
# xBridge MCP — Deploy sites to Hostinger VPS
# Usage: bash scripts/deploy.sh <VPS_IP>
# Example: bash scripts/deploy.sh 168.231.109.225

set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <VPS_IP>"
  echo "Example: $0 168.231.109.225"
  exit 1
fi

VPS_IP="$1"
VPS_USER="${VPS_USER:-root}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Deploying xBridge MCP sites to Hostinger VPS ($VPS_IP) ==="

# Deploy xbrdg.com (token landing page)
echo "→ Deploying xbrdg-site/ → /var/www/xbrdg.com/html/"
rsync -avz --delete \
  --exclude='.git' \
  "$REPO_ROOT/xbrdg-site/" \
  "$VPS_USER@$VPS_IP:/var/www/xbrdg.com/html/"

# Deploy xbridgemcp.com (product site)
echo "→ Deploying site/ → /var/www/xbridgemcp.com/html/"
rsync -avz --delete \
  --exclude='.git' \
  "$REPO_ROOT/site/" \
  "$VPS_USER@$VPS_IP:/var/www/xbridgemcp.com/html/"

echo ""
echo "=== Static sites deployed successfully ==="
echo "  https://xbrdg.com         → token landing page"
echo "  https://xbridgemcp.com    → product site"
echo ""
echo "For the MCP server (Python/Docker):"
echo "  1. Copy .env with XAI_API_KEY to VPS"
echo "  2. docker compose up -d   (or use systemd service)"
echo ""
