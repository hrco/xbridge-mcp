#!/bin/bash
# xBridge MCP — VPS Setup Script
# WARNING: Sample bootstrap script. Review and customize for your environment before running.
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
mkdir -p /var/www/$XBRDG_DOMAIN/html
mkdir -p /var/www/$XBRIDGE_DOMAIN/html
chown -R www-data:www-data /var/www/
chmod -R 755 /var/www/

# 4. Nginx vhost — xbrdg.com
cat > /etc/nginx/sites-available/$XBRDG_DOMAIN << EOF
server {
    listen 80;
    listen [::]:80;
    server_name $XBRDG_DOMAIN www.$XBRDG_DOMAIN;
    root /var/www/$XBRDG_DOMAIN/html;
    index index.html;
    location / {
        try_files \$uri \$uri/ =404;
    }
    # Cache static assets
    location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
        expires 7d;
        add_header Cache-Control "public";
    }
}
EOF

# 5. Nginx vhost — xbridgemcp.com
cat > /etc/nginx/sites-available/$XBRIDGE_DOMAIN << EOF
server {
    listen 80;
    listen [::]:80;
    server_name $XBRIDGE_DOMAIN www.$XBRIDGE_DOMAIN;
    root /var/www/$XBRIDGE_DOMAIN/html;
    index index.html;
    location / {
        try_files \$uri \$uri/ =404;
    }
    location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
        expires 7d;
        add_header Cache-Control "public";
    }
}
EOF

# 6. Enable sites
ln -sf /etc/nginx/sites-available/$XBRDG_DOMAIN /etc/nginx/sites-enabled/
ln -sf /etc/nginx/sites-available/$XBRIDGE_DOMAIN /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t && systemctl reload nginx

echo ""
echo "=== Setup complete ==="
echo "Document roots:"
echo "  $XBRDG_DOMAIN      → /var/www/$XBRDG_DOMAIN/html/"
echo "  $XBRIDGE_DOMAIN → /var/www/$XBRIDGE_DOMAIN/html/"
echo ""
echo "Next steps:"
echo "  1. Point DNS A records to this VPS IP"
echo "  2. Upload site files (run deploy.sh from your local machine)"
echo "  3. Run: certbot --nginx -d $XBRDG_DOMAIN -d www.$XBRDG_DOMAIN"
echo "  4. Run: certbot --nginx -d $XBRIDGE_DOMAIN -d www.$XBRIDGE_DOMAIN"
