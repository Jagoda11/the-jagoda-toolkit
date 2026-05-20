---
name: review
description: Smart router that detects branch changes and recommends which audit skill(s) to run. Use this when starting a review or when unsure which audit to run.
---

# Review — Smart Router

## Purpose

Detect what changed and recommend which audit skill(s) to run.
This skill does NOT perform the audit itself — it routes to the right one(s).

## Instructions

### Step 1 — Detect Changes

Detect the base branch (auto: `develop` for GitFlow, `main`/`master` for trunk-based, `release` if used as integration branch):

```bash
BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$BASE" ] && for b in develop main master release; do
  git show-ref --verify --quiet "refs/heads/$b" && BASE="$b" && break
done
[ -z "$BASE" ] && BASE=$(git rev-parse --abbrev-ref HEAD)
git diff "$BASE"...HEAD --name-only
```

Use three-dot diff (`BASE...HEAD`) to scope to this branch only. Avoid `git log BASE..HEAD` for file detection.

Classify every changed file into one or more categories:

| Category | Signals |
| --- | --- |
| Auth | `**/auth*/**`, `**/authn*/**`, `**/oauth*/**`, `**/oidc*/**`, `**/saml*/**`, `**/session*/**`, JWT/token issuance, auth middleware |
| Database | `**/migrations/**`, `**/*.sql`, `**/schema*.{ts,prisma}`, `**/*.queries.ts`, ORM model dirs, DB client config, DDL |
| Shared Package | `packages/**` (excluding `apps/**`), shared util/contract/UI/i18n packages, anything imported by ≥2 workspaces |
| CI/CD | Changes in `.github/workflows/**`, `.gitlab-ci.yml`, `.circleci/config.yml`, `.azure-pipelines.yml`, `cloudbuild.yaml`, `buildspec.yml`, `.deploy/`, `skaffold.yaml`, `Dockerfile*`, Kustomize overlays, Helm `Chart.yaml`, `docker-compose*.yml` |
| Test | Changes in `tests/**`, `__tests__/**`, `**/*.{test,spec}.{ts,tsx,jsx}`, `vitest.config.ts`, `playwright.config.*`, test utilities, fixtures, coverage config |
| Frontend | Changes in `apps/web/**`, `apps/frontend/**`, `apps/client/**`, `packages/ui*/**`, `**/*.{tsx,jsx}`, React components, hooks, routes |
| Backend | Changes in `apps/api/**`, `apps/server/**`, `apps/backend/**`, `services/**`, route handlers, controllers, service-layer files, domain modules |
| Contracts | Changes in `**/contracts/**`, `**/schemas/**`, `**/*.openapi.{yaml,json}`, zod/typebox schema files, route definition files |
| Config | Changes in `**/eslint.config.*`, `**/tsconfig*.json`, `package.json`, build tool config (`vite.config.*`, `tsup.config.*`), shared config packages |
| Docs | Changes in `*.md`, `docs/` |

### Step 2 — Route to Audits

Based on detected categories, recommend skill(s):

| Trigger | Run |
| --- | --- |
| Auth changes detected | `/review-auth` |
| DB schema or query changes | `/review-test-strategy` + `/audit` |
| Shared package changes | `/review-monorepo` |
| CI/CD pipeline changes | `/review-cicd` |
| New feature (backend + contracts + frontend) | `/audit` + `/review-design` |
| Schema or contract changes | `/review-design` |
| Refactor (structure changes, no new features) | `/review-ai-compat` + `/review-test-strategy` + `/review-design` |
| Test-only changes | `/review-test-strategy` |
| PR ready for merge | `/review-pr` |
| Config or lint rule changes | `/review-ai-compat` |
| Docs-only changes | No audit needed — verify links and accuracy only |

If multiple categories are detected, combine the recommended audits.
Deduplicate — never recommend the same skill twice.

### Step 3 — Output

Produce a structured recommendation:

```
## Review Router — Recommendation

### Changes Detected
- [ category ]: [ list of changed files ]

### Recommended Audits
1. `/skill-name` — reason
2. `/skill-name` — reason

### Priority
[ Which audit to run first and why ]

### Scope Note
[ Any context about the size or risk level of the changes ]
```

## Constraints

- Use `git` commands only — do NOT use `gh` CLI or GitHub API. No PR lookups needed.
- This skill works on branches, not pull requests.
- Do not perform the audit yourself — only recommend.
- If the change set is trivial (typo fix, comment update), say so explicitly.
- If the change set is ambiguous, list what additional context would help.
- If insufficient information to classify, state: "Insufficient information to conclude" instead of guessing.
- Separate facts from assumptions.
