---
description: Independent correctness + security review of pending changes
argument-hint: Optional scope (default: git diff)
---

# Review

Scope: $ARGUMENTS (default: `git diff`).

1. Launch `reviewer` on the scope for correctness (P0–P3, patch-anchored findings + verdict).
2. If the scope touches auth, user input, secrets, network, or dependencies, also launch `security-reviewer` in parallel.
3. Consolidate: keep only findings meeting ALL criteria (provable, actionable, unintentional, introduced here). Drop pre-existing issues, nits, and anything a linter would catch.
4. Present highest-severity items first with file:lines + suggested fix. Ask: fix now, fix later, or proceed.
