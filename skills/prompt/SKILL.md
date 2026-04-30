---
name: prompt
description: 'Structured task handoff. Use when user wants to plan or set up a task before executing — asks 5 intake questions (mode, goal, context, format, unknown_ok) and confirms in one sentence before starting.'
---

# /prompt — Structured Task Handoff

Ask questions one at a time. User answers each. Skip on "skip" or blank.

1. `mode ∈ {research, debug, decision, planning, implement, review}` — "Mode?"
2. `goal: string` — "Goal?"
3. `context: string` — "Context? (or skip)"
4. `format ∈ {text, json, table, steps, code, short}` — "Format?"
5. `unknown_ok ∈ {yes, no}` — "Can I say 'I don't know'?"

After all answers, build internal seed and confirm in one sentence. Then start.

## Rules

```
P1: ∀ field(blank): skip ∨ ask — ¬guess
P2: mode ∈ {research, review} → I1 (edits=0)
P3: unknown_ok=yes → decision ∈ {execute, unknown, insufficient_evidence, refuse}
P4: unknown_ok=no → ∀ claim: verified
P5: post_parse → confirm(1 sentence) ∧ start
```
