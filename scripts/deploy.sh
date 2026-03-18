#!/bin/bash
# xBridge MCP — Deploy sites to Hostinger VPS
# Run from your LOCAL machine (not the VPS)
# Usage: bash deploy.sh <VPS_IP>

set -e

VPS_IP="${1:?Usage: bash deploy.sh <VPS_IP>}"
VPS_USER="root"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Deploying to $VPS_USER@$VPS_IP ==="

# Deploy xbrdg.com (token landing page)
echo "→ Uploading xbrdg-site/ to xbrdg.com..."
rsync -avz --delete \
  "$REPO_ROOT/xbrdg-site/" \
  "$VPS_USER@$VPS_IP:/var/www/xbrdg.com/html/"

# Deploy xbridgemcp.com (product site)
echo "→ Uploading site/ to xbridgemcp.com..."
rsync -avz --delete \
  --exclude="*.md" \
  --exclude="launch-copy.md" \
  --exclude="community-playbook.md" \
  "$REPO_ROOT/site/" \
  "$VPS_USER@$VPS_IP:/var/www/xbridgemcp.com/html/"

echo ""
echo "=== Deploy complete ==="
echo "  https://xbrdg.com         → token landing page"
echo "  https://xbridgemcp.com    → product site"
