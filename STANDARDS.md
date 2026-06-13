# Universal Development Workflow Standards (Core v2.0.0)

This is the canonical, language-neutral core. Projects reference or vendor a pinned copy. Do not re-optimize per project.

Version: 2.0.0

## 1. Git Standards (Tiered)
- **Mandatory** (when >1 agent or shared remote): Never commit directly to main. Every logical change starts on its own short-lived branch.
- **Recommended** (solo work): Use branches for anything that may run in parallel or needs review.
- Always commit early with conventional messages.
- Rebase or merge cleanly to main before any handoff, end of session, or merge.
- Parallel/long-running work → use git worktree (not just branch) so agents do not fight over one working directory.

## 2. Code Quality Standards (Language-Neutral)
All code must be:
- Self-explanatory
- Modular with single responsibility
- Composition over inheritance
- Reliable (error handling, types where available, tests for core paths)

## 3. Subagent & Context Rules
- Maintain a shared `.agent-context.md` (main agent owns it).
- Workers write to `.agent-context.d/<agent>.md` fragments to avoid write races.
- Main agent consolidates fragments into `.agent-context.md` on worker completion.
- Every delegation must include explicit paths to relevant files and directories.
- `.agent-context.md` must contain a "Current in-flight task / next step" section for crash/resume.

## 4. Endpoint Classification (HUMAN / AGENT / INTERNAL)
Label every surface explicitly in code and docs:
- HUMAN: CLI, web dashboards, natural language interfaces
- AGENT: MCP tools, function schemas, structured machine interfaces
- INTERNAL: pure library modules with no network exposure

Never mix concerns in the same file or module.

## 5. Session Ritual
At the start of every session the main agent reads:
- This STANDARDS.md (pinned version)
- The project's `.agent-context.md`
- Any project overlay (see below)

## 6. Concurrency & Long-Running Work
- Parallel agents → separate branches + worktrees
- Rebase or merge cleanly to main before any handoff, end of session, or merge.
- Long-running agents must leave resumable state in `.agent-context.md`

## 7. Identity
Global `~/.claude/CLAUDE.md` is authoritative for commit/push identity (hrco account + signing). Project overlay may add project-specific identity rules but must never override the global source.

---

## Project Overlay (example for xBridge)
Language-specific rules, MCP details, and local paths live in the project's own `.workflow-prompt.md` or `CLAUDE.md`.

This core (v2.0.0) lives in ~/mylab/forge (pinned & versioned). Projects reference it.