---
description: Cross-verify docs vs code vs data vs tests, report drift with minimal diffs
argument-hint: Optional scope (default: whole repo)
---

# Audit

Scope: $ARGUMENTS (default: whole repo). Evidence-based audit across 4 nodes. Never accept a doc claim without executing a verification command.

## Phase 1: Collect claims

- **Docs**: quantitative claims (counts, percentages, schemas), API contracts, query/config examples.
- **Code**: actual logic, models, safety guards.
- **Data/state**: real DB/files (row counts, columns, distinct values) via read-only commands.
- **Tests/benchmarks**: suites, fixtures, golden sets (counts computed by parsing, never estimated).

## Phase 2: Triangulate

Delta matrix: data drift (stale numbers) · schema desync (doc vs real) · blindspots (patterns failing on real edge cases) · benchmark mismatch · cross-doc contradictions.

## Phase 3: Report

Per finding: file + line, current claim, ground-truth reality (with command proof), exact replacement diff. Prioritize by impact. No fix without proof; no proof without a command that anyone can re-run.
