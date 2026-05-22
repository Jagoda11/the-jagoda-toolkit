---
name: start
description: Pre-flight for a coding session. Loads CodeGraph, checks branch and recent changes, pre-loads core tools, and establishes session workflow rules.
allowed-tools: Bash(*), Read, Glob, Grep, ToolSearch, mcp__codegraph__codegraph_status, mcp__codegraph__codegraph_search, mcp__codegraph__codegraph_callers, mcp__codegraph__codegraph_callees, mcp__codegraph__codegraph_context, mcp__codegraph__codegraph_node, mcp__codegraph__codegraph_impact
---

# Start - Pre-Flight

## Purpose

Prime the session for tool-first navigation. Load CodeGraph, check project state, establish what's changed. This replaces "read everything and hope" with "load tools and discover."

## Principle

Do not create more nodes to avoid thinking.

Create nodes only when they reduce confusion.

## Instructions

### Step 0 — Read Permissions

Read the project settings files to know what tools are pre-approved and denied:

```
Read: .claude/settings.json
Read: .claude/settings.local.json  (optional — skip without error if missing)
```

`.claude/settings.json` is committed and always present. `.claude/settings.local.json` is per-developer and may not exist.

Internalize the `allow` and `deny` lists. Never ask permission for tools in the allow list. Never attempt tools in the deny list. Do not print the contents — just absorb them silently.

### Step 1 - Load CodeGraph

Run `ToolSearch` to load the codegraph tools:

```
ToolSearch: "+codegraph status"
```

Then call `codegraph_status` to verify the graph is available and check when it was last updated.

If `.codegraph/` does not exist or the graph is stale, tell the user:

> "CodeGraph is missing/stale. Run `codegraph init -i` to rebuild."

### Step 2 - Check Branch and Changes

Run:

```bash
git branch --show-current
git log --oneline -5
git status --short
```

Summarize: what branch, what recent work, anything uncommitted.

### Step 3 - Load Core Tools

Run `ToolSearch` to pre-load the tools you will most need:

```
ToolSearch: "select:mcp__codegraph__codegraph_search,mcp__codegraph__codegraph_callers,mcp__codegraph__codegraph_callees,mcp__codegraph__codegraph_context,mcp__codegraph__codegraph_node,mcp__codegraph__codegraph_impact"
```

### Step 4 - Establish Workflow Rules

State these out loud as a commitment for the session:

**Session workflow:**

1. **Find symbols** — `codegraph_search` over `Grep`
2. **Trace callers/callees** — `codegraph_callers`/`codegraph_callees` before editing
3. **Check impact** — `codegraph_impact` before changing a symbol
4. **Read whole** — `Read` (not partial) before edit
5. **Grep as fallback** — only for string literals, comments, or things outside the code graph

### Step 5 - Output

Produce a short status block:

```
## Session Ready

**Branch:** <branch name>
**Recent:** <last 2-3 commits, one line each>
**Uncommitted:** <list of changed files>
**CodeGraph:** <available + last updated / missing / stale>
**Tools loaded:** codegraph_search, codegraph_callers, codegraph_callees, codegraph_context, codegraph_node, codegraph_impact

Ready. What are we working on?
```

## Constraints

- Do NOT read MEMORY.md, CLAUDE.md, or large docs during pre-flight. Those are reference — read them only when a specific question needs them.
- Do NOT summarize the project or explain the architecture. The user knows.
- Keep output under 15 lines. This is a boot sequence, not a briefing.
- If CodeGraph is unavailable, still complete the other steps. Note it and move on.
