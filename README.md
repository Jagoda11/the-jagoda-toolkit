# The Jagoda Toolkit

A Claude Code plugin — skills, hooks, and agents for TypeScript monorepo development.

> **New to Claude Code? Feeling lost?** Install this toolkit and you've got a working baseline — pre-flight checks, review skills, safety hooks, and agents — without having to wire it all up yourself.

## What it does

`jc` is a single Claude Code plugin bundling skills, commands, hooks, and agents for TypeScript monorepo development. It gives Claude:

- **Pre-flight skills** that load CodeGraph and set session workflow rules before you start coding
- **Review skills** that audit code, auth, CI/CD, monorepo boundaries, tests, design, and AI-agent compatibility — plus a smart router that picks which audit fits the change
- **Expert protocols** — fixed multi-persona panels (Brains for backend/architecture, Pinky for frontend) that review a task from many angles in parallel
- **Slash commands** for fast lint/typecheck/test on affected workspaces, and for lint-invisible tech-debt review
- **Agents** that write tests preserving harmonic constraints, and verify a page UI end-to-end in Chrome against a real DB
- **Hooks** that block commits to protected branches, prevent file overwrites, scan for credentials, auto-verify after writes, sync skills on session start, and rewrite shell commands through `rtk` for token savings

## Prerequisites

`jq` is required by the security hooks (`block-git-commit-protected`, `no-overwrite`, `scan-credentials`, `verify-on-write`).

```sh
# macOS
brew install jq

# Debian / Ubuntu
sudo apt install jq

# Fedora / RHEL
sudo dnf install jq
```

## Install

```sh
claude plugin marketplace add Jagoda11/the-jagoda-toolkit
claude plugin install jc@the-jagoda-toolkit
```

## Skills

| Skill | Purpose |
| --- | --- |
| `/jc:start` | Pre-flight: load CodeGraph, check branch and recent changes, pre-load core tools |
| `/jc:start-ui` | Same as `/jc:start` plus verify Chrome DevTools and navigate to the frontend |
| `/jc:prompt` | Structured task handoff — asks 5 intake questions before executing |
| `/jc:audit` | Deep architecture audit: failure modes, boundary audit, test gaps, data flow, risk prioritization |
| `/jc:protocol` | Router for named expert panels — `/jc:protocol <name> <task>` |
| `/jc:protocol-brains` | 11-expert backend/architecture panel (DB, TS, migration, monorepo, multiagent, orchestration) |
| `/jc:protocol-pinky` | 16-expert frontend panel with dynamic UI-lib routing |
| `/jc:review` | Smart router — detects branch changes and recommends which audit to run |
| `/jc:review-pr` | Full pre-merge gate — automated checks, governance, AI patch safety score |
| `/jc:review-auth` | Auth production-readiness audit (OIDC, sessions, tokens, route protection, secrets) |
| `/jc:review-ai-compat` | AI-agent compatibility — determinism, explicitness, complexity, boundary clarity |
| `/jc:review-cicd` | CI/CD reliability — pipelines, Dockerfiles, K8s, Skaffold, GitHub Actions |
| `/jc:review-design` | 24 structural design principles for agent-readable code |
| `/jc:review-monorepo` | Workspace boundaries, dependency direction, domain ownership, shared-package bloat |
| `/jc:review-test-strategy` | Test architecture, coverage, flakiness — produces scored JSON contract |

## Commands

| Command | Purpose |
| --- | --- |
| `/jc:verify` | Run lint, typecheck, and test on affected workspaces (auto-detects package manager) |
| `/jc:techdebt` | Review changed files for tech debt lint can't catch — duplication, dead code, naming drift |

## Agents

| Agent | Purpose |
| --- | --- |
| `jc:test-writer` | Writes tests for code changes, preserves harmonic constraints, verifies with format/lint/typecheck/test |
| `jc:ui-verifier` | Verifies a page UI end-to-end in Chrome via DevTools MCP; reports only, never fixes |

## Hooks

| Hook | When | What | Modifies | Can Block | Failure Behavior |
|------|------|------|----------|-----------|------------------|
| rtk-rewrite.sh | PreToolUse (Bash) | Rewrites shell commands through rtk for token savings | command only | no | falls back to original command |
| block-git-commit-protected.sh | PreToolUse (git commit) | Blocks commits on protected branches | no | yes | blocks commit |
| no-overwrite.sh | PreToolUse (Write) | Prevents accidental file overwrites | no | yes | blocks write |
| scan-credentials.sh | PostToolUse (Edit / Write / MultiEdit) | Scans newly written content for credentials | no | yes | flags and blocks if configured |
| verify-on-write.sh | PostToolUse (Edit / Write / MultiEdit) | Auto-runs verification after file writes | no | no | reports failures |
| sync-skills.sh | SessionStart | Syncs local skills | no | no | logs failure |

All hooks operate locally on Claude Code tool payloads and repository context.

- They do not make network calls
- They do not access files outside the working repository
- They do not execute arbitrary external code beyond defined commands
- They do not modify files unless explicitly part of the invoked tool action

The design is intentionally conservative: hooks either block unsafe actions or report issues, but do not silently alter repository state.

## Plugins

| Plugin | What |
| --- | --- |
| `jc` toolkit — skills, commands, hooks, agents |

## Companion Tools

### Required

- [CodeGraph](https://github.com/colbymchenry/codegraph) by colbymchenry (MIT) — pre-indexed code knowledge graph for Claude Code. **Required** by `start` and `start-ui` skills. Install globally (`npm install -g @colbymchenry/codegraph`), then run `codegraph init -i` in your project.

### Optional

- [typescript-lsp](https://github.com/anthropics/claude-plugins-official) by Anthropic — official Language Server Protocol plugin. Enables go-to-definition, find-references, and refactoring intelligence for Claude on TypeScript codebases. Recommended for this toolkit since it targets TS monorepos. Install:
  ```sh
  claude plugin marketplace add anthropics/claude-plugins-official
  claude plugin install typescript-lsp@claude-plugins-official
  ```
- [rtk](https://github.com/rtk-ai/rtk) by rtk-ai (Apache 2.0) — CLI proxy for token reduction. **Integrated** via the bundled `rtk-rewrite.sh` PreToolUse hook; no-op if `rtk` is not installed.
- [caveman](https://github.com/JuliusBrussee/caveman) by Julius Brussee (MIT) — token-saving communication mode.

All install separately. None bundled.

## Optional statusline

Claude Code plugins can't ship a main-thread statusline. If you want one, add to your `~/.claude/settings.json`:

```json
"statusLine": {
  "type": "command",
  "command": "bash ${CLAUDE_PROJECT_DIR}/.claude/statusline.sh"
}
```

Then save this as `.claude/statusline.sh` in your project (requires `jq`):

```sh
#!/bin/bash
input=$(cat)

used=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
remaining=$(echo "$input" | jq -r '.context_window.remaining_percentage // empty')
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // empty')
input_tokens=$(echo "$input" | jq -r '.context_window.total_input_tokens // 0')
output_tokens=$(echo "$input" | jq -r '.context_window.total_output_tokens // 0')
cost_usd=$(echo "$input" | jq -r '.cost.total_cost_usd // 0')
model_name=$(echo "$input" | jq -r '.model.display_name // .model.id // empty' | sed -E 's/ *\([^)]*\)//')
dir=$(basename "$cwd")
branch=$(git -C "$cwd" branch --show-current 2>/dev/null)

green=$'\033[32m'; yellow=$'\033[33m'; red=$'\033[31m'; cyan=$'\033[36m'; reset=$'\033[0m'

if [ -n "$used" ]; then
  used_int=$(printf "%.0f" "$used")
  remaining_int=$(printf "%.0f" "${remaining:-$((100 - used_int))}")
  if [ "$used_int" -lt 70 ]; then bar_color="$green"
  elif [ "$used_int" -lt 90 ]; then bar_color="$yellow"
  else bar_color="$red"; fi
  filled=$((used_int / 10)); empty=$((10 - filled)); bar=""
  [ "$filled" -gt 0 ] && printf -v f "%${filled}s" "" && bar="${f// /█}"
  [ "$empty" -gt 0 ] && printf -v p "%${empty}s" "" && bar="${bar}${p// /░}"
  ctx_info="${bar_color}${bar}${reset} ${used_int}% used / ${remaining_int}% left"
else
  ctx_info="ctx: --"
fi

total_tokens=$((input_tokens + output_tokens))
tokens_fmt=$(awk -v t="$total_tokens" 'BEGIN {if (t >= 1000) printf "%.1fk", t/1000; else print t}')
cost_fmt=$(awk -v c="$cost_usd" 'BEGIN { printf "$%.2f", c }')
branch_info=""; [ -n "$branch" ] && branch_info=" | 🌱 ${cyan}${branch}${reset}"

echo -e "${ctx_info}"
echo -e "📁 ${dir}${branch_info}"
model_info=""; [ -n "$model_name" ] && model_info=" | 🤖 ${model_name}"
echo -e "🎫 ${tokens_fmt} | 💰 ${cost_fmt}${model_info}"
```

Shows: context window usage bar, directory + branch, tokens + cost + model.

## Credits

Thanks to the projects this toolkit leans on:

- **[CodeGraph](https://github.com/colbymchenry/codegraph)** — colbymchenry's local code intelligence is what makes the pre-flight skills genuinely useful. Without it, `start` is just a status print.
- **[rtk](https://github.com/rtk-ai/rtk)** — rtk-ai's token-saving CLI proxy keeps long sessions affordable; the bundled hook is a thin wrapper around their work.
- **[caveman](https://github.com/JuliusBrussee/caveman)** — Julius Brussee's compression mode pairs naturally with terse review workflows.

## Changelog

Release notes are in [CHANGELOG.md](./CHANGELOG.md).

## License

MIT — see [LICENSE](./LICENSE).

## Author

Built by Jagoda Cubrilo ([@Jagoda11](https://github.com/Jagoda11)).

Source: <https://github.com/Jagoda11/the-jagoda-toolkit>
