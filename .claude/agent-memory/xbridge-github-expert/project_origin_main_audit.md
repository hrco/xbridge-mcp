---
name: origin/main audit results
description: Full audit of origin/main branch before public launch — sensitive files, secrets scan, strategy exposure findings
type: project
---

Audit completed 2026-03-21. origin/main has 24 commits with full $XBRDG strategy exposure.

**Findings:**
- 9 XBRIDGE-* agent files tracked with full pump.fun launch strategy, community seeding, marketing playbooks
- site/launch-copy.md has token CA and pre-written tweet threads
- site/community-playbook.md has complete Telegram/X setup playbook
- PUBLIC-SAFE-MANIFEST.md reveals internal cleanup process
- /home/supremeleader paths exposed in diffs (5 occurrences)
- Commit messages reveal strategy pivots and monetization plans
- No real API keys found (all REDACTED/placeholder)
- No VPS IP hardcoded on origin/main
- No payment credentials found

**Clean release branch (local):** 1 orphan commit, 50 files, no sensitive content. Not yet pushed.

**Recommendation:** Delete-and-recreate repo (nuclear option) to avoid 90-day dangling commit risk, OR at minimum delete origin/main and push only release branch.

**Why:** The strategy documents are exactly what crypto competitors/speculators would search for. The 90-day GitHub object retention makes branch deletion alone insufficient for high-sensitivity content.

**How to apply:** Before making repo public, ensure origin/main is eliminated and only the clean release branch exists on the remote.
