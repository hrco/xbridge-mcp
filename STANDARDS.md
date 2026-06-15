# Development Workflow Standards — xBridge MCP

This project follows the **Universal Development Workflow Core**, which is now
canonical in the forge library. This file does not duplicate it — it references
the pinned version.

## Canonical Core
- **Source:** `forge standards/STANDARDS.md` (repo: `git@github.com:hrco/forge.git`)
- **Local path:** `~/mylab/forge/standards/STANDARDS.md`
- **Pinned version:** v2.0.0

The core defines: tiered git standards, language-neutral code quality, subagent
& context rules, endpoint classification (HUMAN/AGENT/INTERNAL), the session
ritual, concurrency & long-running work, and identity precedence. Read it there;
do not re-optimize it per project.

## Project Overlay
xBridge-specific rules (Python + async, MCP surface, key patterns, local paths)
live in `.workflow-prompt.md`. The overlay extends the core and must never
contradict it.

## Live Shared State
`.agent-context.md` holds the live shared agent context, including the
"Current in-flight task / next step" section required by the core.

---
When the core bumps version in forge, re-pin the version above deliberately and
re-check the overlay for conflicts.
