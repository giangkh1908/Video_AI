---
description: Guided planning with codebase understanding — ends with an approved plan, no implementation
argument-hint: Task to plan
---

# Plan

Request: $ARGUMENTS

Follow Command → Agent → Skill: this command explores and asks; implementation happens only after explicit approval.

## Phase 1: Discovery

State the objective, constraints, and success criteria (measurable). If unclear, ask now.

## Phase 2: Exploration

Launch `scout` agents in parallel on different aspects (similar features, architecture, relevant patterns). Read the key files they return. Summarize findings + patterns.

## Phase 3: Clarifying questions

List every ambiguity (edge cases, error handling, scope boundaries, compatibility). **Wait for answers. Do not skip.**

## Phase 4: Design

Present 2–3 approaches (minimal / clean / pragmatic) with trade-offs, your recommendation + reasoning. **Ask which to take. Stop here — no code until approved.**
