---
name: start-ui
description: Pre-flight with Chrome. Runs /start then confirms Chrome DevTools tools are available for UI work. Use instead of /start when you need browser access.
allowed-tools: Bash(*), Read, Glob, Grep, ToolSearch, mcp__codegraph__codegraph_status, mcp__codegraph__codegraph_search, mcp__codegraph__codegraph_files, mcp__chrome-devtools__take_screenshot, mcp__chrome-devtools__list_pages, mcp__chrome-devtools__navigate_page
---

# Start UI - Pre-Flight with Chrome

## Purpose

Run the standard `/start` pre-flight, then verify Chrome DevTools tools are loaded and navigate to the frontend.

## Instructions

### Step 1 - Run /start

Invoke the `start` skill to do the normal pre-flight (CodeGraph, branch check, tool loading).

### Step 2 - Verify Chrome tools

Run `ToolSearch` to load Chrome DevTools tools:

```
ToolSearch: "+chrome-devtools screenshot"
ToolSearch: "+chrome-devtools navigate"
```

Then try `mcp__chrome-devtools__list_pages` to confirm the connection is live.

If Chrome tools are not available, tell the user:

> "Chrome tools not available. Run `claude mcp list` to verify the `chrome-devtools` MCP server is registered."

### Step 3 - Navigate to the frontend

Once Chrome is confirmed connected, navigate to the frontend app:

```
mcp__chrome-devtools__navigate_page(url: "http://localhost:3000")
```

Take a screenshot to confirm the app loaded.

### Step 4 - Output

Append to the `/start` output:

```
**Chrome:** ✅ Connected — navigated to localhost:3000 / ❌ Not available
```

## Constraints

- DO NOT read project docs — `/start` already handles that.
- Keep output under 5 extra lines beyond `/start`.
