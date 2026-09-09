# Universal Agent + Skill Kit (portable)

Copy this `.claude/` directory into any repo to get the standard working set.
No repo code is touched; only additive files under `.claude/`.

## Contents

| Path | What |
|---|---|
| `agents/orchestrator.md` | Plans, delegates (Agent tool), verifies, synthesizes. Preloads 4 meta-skills |
| `agents/task.md` | Default implementation worker. Preloads `clean-code` |
| `agents/scout.md` | Read-only research (Read/Grep/Glob only) |
| `agents/reviewer.md` | Correctness review, P0–P3, patch-anchored. Preloads `clean-code` |
| `agents/security-reviewer.md` | Read-only vuln analysis, source→sink. No skills (deterministic) |
| `skills/task-decomposition/` | Break work into executable tasks |
| `skills/agent-routing/` | Which agent for which job |
| `skills/execution-planning/` | Order, parallelism, verification, failure handling |
| `skills/context-management/` | Budget, handoff, compaction |
| `skills/clean-code/` (+`references/`) | Code rules + smell table |
| `skills/software-architecture/` (+`references/`) | Architecture decisions + pattern table |
| `skills/ai-application/` | LLM/RAG/agent guidance + eval |
| `commands/plan.md` | Explore + ask → approved plan, no code |
| `commands/review.md` | reviewer [+ security-reviewer] → consolidated findings |
| `commands/audit.md` | Docs↔Code↔Data↔Tests drift audit |
| `hooks/block-dangerous.sh` | PreToolUse: blocks destructive Bash (exit 2) |
| `hooks/stop-checklist.sh` | Stop: surgical checklist reminder (advisory) |

## Wiring

- `orchestrator` preloads the 4 meta-skills via `skills:` frontmatter.
- `task`/`reviewer` preload `clean-code`; discover `software-architecture`/`ai-application` on demand via Skill tool.
- `scout`/`security-reviewer` are read-only by `tools:` restriction.
- Pattern: **Command → Agent → Skill**. What must always happen → hook; what model should know → skill.

## Verify after copying

1. `git status` shows only `.claude/` additions.
2. Each `SKILL.md` < 500 lines; each agent frontmatter has `name` + `description` ("Use this agent when…").
3. Test hooks: a `rm -rf` attempt is blocked; normal commands pass.
