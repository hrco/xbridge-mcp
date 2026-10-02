# Hosted MCP runbook — `mcp.xbridgemcp.com`

Human-in-the-loop steps for standing up the hosted xBridge MCP endpoint on a VPS.
Every command below is meant to be run by a human on the target host; the agent
never touches the server directly.

Deploy artifacts in this repo:

- `deploy/xbridge-cloud.service` — systemd unit (binds `127.0.0.1:8787`)
- `deploy/nginx-mcp.xbridgemcp.com.conf` — nginx site (TLS added by certbot)

---

## 1. Prereqs

- A reachable Ubuntu host. Hostinger `76.13.48.186` timed out on 2026-10-02; the
  fallback is Oracle `92.5.184.225`. Confirm with `ping <host>` / `ssh claude@<host>`
  before anything else.
- DNS: an `A` record for `mcp.xbridgemcp.com` pointing at the host IP. Wait for it
  to resolve before requesting a certificate:

  ```bash
  dig +short mcp.xbridgemcp.com
  ```

- Ports 80/443 reachable from the internet (certbot needs both).

## 2. Install

```bash
sudo useradd -r -s /usr/sbin/nologin xbridge
sudo mkdir -p /opt/xbridge-mcp/data && sudo chown -R xbridge /opt/xbridge-mcp
sudo -u xbridge python3 -m venv /opt/xbridge-mcp/venv
sudo -u xbridge /opt/xbridge-mcp/venv/bin/pip install "xbridge-mcp[cloud] @ git+https://github.com/hrco/xbridge-mcp@release"
```

## 3. Secrets

Create `/opt/xbridge-mcp/cloud.env`, mode `600`, owner `xbridge`. Never commit these.

| Variable | Value |
|----------|-------|
| `LS_SIGNING_SECRET` | LemonSqueezy webhook signing secret (Settings → Webhooks) |
| `XBRIDGE_SIGNING_KEY` | base64 Ed25519 **private** key; its public half must equal `tokenizer.ED25519_PUBLIC_KEY_B64` |
| `XBRIDGE_DB_PATH` | `/opt/xbridge-mcp/data` (set by the unit file) |

```bash
sudo touch /opt/xbridge-mcp/cloud.env
sudo chown xbridge:xbridge /opt/xbridge-mcp/cloud.env
sudo chmod 600 /opt/xbridge-mcp/cloud.env
sudo -u xbridge $EDITOR /opt/xbridge-mcp/cloud.env
```

## 4. Service

```bash
sudo cp deploy/xbridge-cloud.service /etc/systemd/system/xbridge-cloud.service
sudo systemctl daemon-reload && sudo systemctl enable --now xbridge-cloud
curl -s 127.0.0.1:8787/health
```

## 5. nginx + TLS

```bash
sudo cp deploy/nginx-mcp.xbridgemcp.com.conf /etc/nginx/sites-available/mcp.xbridgemcp.com.conf
sudo ln -s /etc/nginx/sites-available/mcp.xbridgemcp.com.conf /etc/nginx/sites-enabled/mcp.xbridgemcp.com.conf
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d mcp.xbridgemcp.com
```

The site is HTTP-only on purpose: certbot rewrites it to add the `443 ssl`
listener and the certificate paths. `proxy_buffering off` is required so MCP
streamable-HTTP responses are not held in a proxy buffer.

The access log records method/path/status only. Never add `$http_x_xai_key` or
`$http_authorization` to a log format — that writes customers' keys to disk.

## 6. LemonSqueezy

- Webhook URL: `https://mcp.xbridgemcp.com/webhooks/ls`
- Sign the webhook with the same secret as `LS_SIGNING_SECRET`.
- Subscribe to events: `subscription_created`, `subscription_cancelled`,
  `subscription_expired`. Cancel/expire revoke the issued key; a later
  re-subscribe issues a working key again.
- Product description: "Hosted xBridge: no install, unlimited calls".

## 7. Smoke test (customer view)

```bash
claude mcp add --transport http xbridge https://mcp.xbridgemcp.com/mcp --header "Authorization: Bearer $XBRIDGE_KEY" --header "X-XAI-Key: $XAI_API_KEY"
```

Then ask Claude to run `grok-models`. Handshake traffic (`initialize`,
`tools/list`, notifications) is free; only real calls consume the daily
allowance, and the customer's own xAI key is what bills Grok usage.
