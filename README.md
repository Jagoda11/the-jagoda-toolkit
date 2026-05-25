# The Jagoda Toolkit

A Claude Code plugin — skills, hooks, and agents for TypeScript monorepo development.

## What it does

`jc` is a single Claude Code plugin bundling skills, commands, hooks, and agents for TypeScript monorepo development. It gives Claude:

- **Pre-flight skills** that load CodeGraph and set session workflow rules before you start coding
- **Review skills** that audit code, auth, CI/CD, monorepo boundaries, tests, design, and AI-agent compatibility — plus a smart router that picks which audit fits the change
- **Expert protocols** — fixed multi-persona panels (Brains for backend/architecture, Pinky for frontend) that review a task from many angles in parallel
- **Slash commands** for fast lint/typecheck/test on affected workspaces, and for lint-invisible tech-debt review
- **Agents** that write tests preserving harmonic constraints, and verify a page UI end-to-end in Chrome against a real DB
- **Hooks** that block commits to protected branches, prevent file overwrites, scan for credentials, auto-verify after writes, sync skills on session start, and rewrite shell commands through `rtk` for token savings

## Prerequisites

`jq` is required by the security hooks (`block-git-commit-protected`, `no-overwrite`, `scan-credentials`, `verify-on-write`). Without it those hooks silently no-op instead of blocking.

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

| Hook | When | What |
| --- | --- | --- |
| `rtk-rewrite.sh` | PreToolUse (Bash) | Rewrites shell commands through `rtk` for token savings |
| `block-git-commit-protected.sh` | PreToolUse (`git commit`) | Blocks commits on protected branches |
| `no-overwrite.sh` | PreToolUse (Write) | Prevents accidental file overwrites |
| `scan-credentials.sh` | PostToolUse (Edit / Write / MultiEdit) | Scans newly written content for credentials |
| `verify-on-write.sh` | PostToolUse (Edit / Write / MultiEdit) | Auto-runs verify after file writes |
| `sync-skills.sh` | SessionStart | Keeps local skills in sync at session start |

## Plugins

| Plugin | What |
| --- | --- |
| `jc` | Personal toolkit — skills, commands, hooks, agents |

## Companion Tools

### Required

- [CodeGraph](https://github.com/colbymchenry/codegraph) by colbymchenry (MIT) — pre-indexed code knowledge graph for Claude Code. **Required** by `start` and `start-ui` skills. Install globally (`npm install -g @colbymchenry/codegraph`), then run `codegraph init -i` in your project.

### Optional

- [rtk](https://github.com/rtk-ai/rtk) by rtk-ai (Apache 2.0) — CLI proxy for token reduction. **Integrated** via the bundled `rtk-rewrite.sh` PreToolUse hook; no-op if `rtk` is not installed.
- [caveman](https://github.com/JuliusBrussee/caveman) by Julius Brussee (MIT) — token-saving communication mode.

All install separately. None bundled.

## Credits

Thanks to the projects this toolkit leans on:

- **[CodeGraph](https://github.com/colbymchenry/codegraph)** — colbymchenry's local code intelligence is what makes the pre-flight skills genuinely useful. Without it, `start` is just a status print.
- **[rtk](https://github.com/rtk-ai/rtk)** — rtk-ai's token-saving CLI proxy keeps long sessions affordable; the bundled hook is a thin wrapper around their work.
- **[caveman](https://github.com/JuliusBrussee/caveman)** — Julius Brussee's compression mode pairs naturally with terse review workflows.

## License

MIT — see [LICENSE](./LICENSE).

## Author

Built by Jagoda Cubrilo ([@Jagoda11](https://github.com/Jagoda11)).

Source: <https://github.com/Jagoda11/the-jagoda-toolkit>
