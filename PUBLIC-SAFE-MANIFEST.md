# PUBLIC-SAFE-MANIFEST

This file defines what is safe to publish if this repository is ever made public.

## Safe to publish
- `README.md`
- `LICENSE`
- `CONTRIBUTING.md`
- `CHANGELOG.md`
- `Dockerfile`
- `docker-compose.yml` (without real secrets)
- `pyproject.toml`
- `run_server.py`
- `xbridge_mcp/`
- `tests/`
- `docs/conneXt-mcp-config.example.json`
- `docs/marketing/LAUNCH-KIT.md`
- `docs/monetization/OFFER.md`

## Never publish
- `.env` and any secret-bearing files
- `.claude/`
- `CLAUDE.md`
- `GROK-DEV-CONTEXT.md`
- `docs/plans/`
- `docs/marketing/archive/`
- `docs/marketing/generated/`
- `docs/monetization/DM-POSTS.md`
- `docs/monetization/LAUNCH-CHECKLIST.md`
- `docs/monetization/metrics.csv`

## Pre-push checklist
1. Confirm repo visibility is **Private**.
2. Run secret scan:
   - `git grep -nE "xai-|sk-or-v1-|OPENROUTER_API_KEY|MORPH_API_KEY|SUDO_AUTH_PSW"`
3. Check tracked files:
   - `git ls-files`
4. Ensure no internal docs are tracked.
