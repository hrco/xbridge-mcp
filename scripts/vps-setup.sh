#!/bin/bash
# xBridge MCP — Hostinger VPS Setup Script
# Run as root on fresh Ubuntu 22.04/24.04
# Usage: bash vps-setup.sh

set -e

echo "=== xBridge VPS Setup ==="

# ---- CONFIG — edit these before running ----
XBRDG_DOMAIN="xbrdg.com"
XBRIDGE_DOMAIN="xbridgemcp.com"
# -------------------------------------------

# 1. Update & install nginx + certbot
apt update && apt upgrade -y
apt install -y nginx certbot python3-certbot-nginx ufw

# 2. Firewall
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

# 3. Document roots
mkdir -p /var/www/xbrdg.com/html
mkdir -p /var/www/xbridgemcp.com/html
chown -R www-data:www-data /var/www/
chmod -R 755 /var/www/

# 4. Nginx vhost — xbrdg.com
cat > /etc/nginx/sites-available/xbrdg.com << 'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name xbrdg.com www.xbrdg.com;
    root /var/www/xbrdg.com/html;
    index index.html;
    location / {
        try_files $uri $uri/ =404;
    }
    # Cache static assets
    location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
        expires 7d;
        add_header Cache-Control "public";
    }
}
EOF

# 5. Nginx vhost — xbridgemcp.com
cat > /etc/nginx/sites-available/xbridgemcp.com << 'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name xbridgemcp.com www.xbridgemcp.com;
    root /var/www/xbridgemcp.com/html;
    index index.html;
    location / {
        try_files $uri $uri/ =404;
    }
    location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
        expires 7d;
        add_header Cache-Control "public";
    }
}
EOF

# 6. Enable sites
ln -sf /etc/nginx/sites-available/xbrdg.com /etc/nginx/sites-enabled/
ln -sf /etc/nginx/sites-available/xbridgemcp.com /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t && systemctl reload nginx

echo ""
echo "=== Setup complete ==="
echo "Document roots:"
echo "  xbrdg.com      → /var/www/xbrdg.com/html/"
echo "  xbridgemcp.com → /var/www/xbridgemcp.com/html/"
echo ""
echo "Next steps:"
echo "  1. Point DNS A records to this VPS IP"
echo "  2. Upload site files (run deploy.sh from your local machine)"
echo "  3. Run: certbot --nginx -d xbrdg.com -d www.xbrdg.com"
echo "  4. Run: certbot --nginx -d xbridgemcp.com -d www.xbridgemcp.com"
