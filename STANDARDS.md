# Universal Development Workflow Standards (Reusable v1)

Copy this file into every new project. Adapt only the project-specific sections.

## 1. Git Standards (Mandatory)
- Never work directly on main.
- Every piece of work starts on its own short-lived branch: feat/, fix/, or chore/.
- Before any change: `git checkout -b <branch-name>`
- Commit early and often with conventional commits.
- Parallel agents must each use their own branch.

## 2. Code Quality Standards
All code must be:
- Self-explanatory
- Reusable via object-oriented modular design (classes for stateful parts, composition over inheritance)
- Reliable (error handling, types, tests)
- Strictly modular (one responsibility per module)

## 3. Subagent Rules
- Always maintain a shared `.agent-context.md`
- Every delegation must include explicit paths to relevant files and directories
- Each subagent works only on its assigned branch

## 4. Endpoint Classification
Label every surface clearly:
- HUMAN (CLI, web UI)
- AGENT (MCP tools, function schemas)
- INTERNAL (pure modules)

Never mix concerns in the same file.

## 5. Session Start
Every session begins by reading STANDARDS.md and the project .agent-context.md.

This version is project-agnostic and ready to copy.