from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["site/index.html", "site/guide.html"]


def test_no_stale_prices():
    for p in PAGES:
        html = (ROOT / p).read_text()
        for stale in ("€9", "€3.69", "$0"):
            assert stale not in html, f"{stale} in {p}"


def test_hosted_is_what_pro_sells():
    html = (ROOT / "site/index.html").read_text()
    assert "Hosted" in html
    assert "Self-host" in html and "unlimited" in html.lower()
    assert "mcp.xbridgemcp.com/mcp" in html


def test_readme_hosted_snippet():
    md = (ROOT / "README.md").read_text()
    assert "## Hosted (no install)" in md
    assert "claude mcp add --transport http xbridge https://mcp.xbridgemcp.com/mcp" in md
    assert "X-XAI-Key" in md
