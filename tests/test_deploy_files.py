from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_systemd_unit():
    unit = (ROOT / "deploy/xbridge-cloud.service").read_text()
    assert "ExecStart=/opt/xbridge-mcp/venv/bin/xbridge-cloud" in unit
    assert "EnvironmentFile=/opt/xbridge-mcp/cloud.env" in unit
    assert "XAI_API_KEY" not in unit


def test_nginx_streams_and_proxies():
    conf = (ROOT / "deploy/nginx-mcp.xbridgemcp.com.conf").read_text()
    assert "proxy_pass http://127.0.0.1:8787" in conf
    assert "proxy_buffering off" in conf
    assert "server_name mcp.xbridgemcp.com" in conf
    assert "access_log" in conf and "$http_x_xai_key" not in conf and "$http_authorization" not in conf


def test_runbook_lists_human_steps():
    rb = (ROOT / "docs/hosted-runbook.md").read_text()
    for needle in ("DNS", "certbot", "LS_SIGNING_SECRET", "XBRIDGE_SIGNING_KEY",
                   "subscription_cancelled", "subscription_expired", "claude mcp add --transport http"):
        assert needle in rb
