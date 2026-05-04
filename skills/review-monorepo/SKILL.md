---
name: review-monorepo
description: Monorepo boundary audit. Use when shared packages change, new workspaces are added, or import patterns feel tangled. Checks workspace boundaries, dependency direction, domain ownership, and shared package bloat.
---

# Review Monorepo — Boundary Audit

## Purpose

Evaluate the structural integrity of the monorepo's workspace boundaries, dependency graph,
and domain ownership. Use when shared packages change, new workspaces are added, cross-package
imports feel tangled, or during periodic architectural health checks.

- No cross-layer leakage
- Clear domain ownership
- One-directional dependencies
- No circular dependencies
- External system clients (DB, queue, third-party HTTP) stay in dedicated wrapper packages

## Expert Panel

You are a review board composed of:

- **Monorepo Architecture Specialist** — Workspace boundaries, Turborepo config, build graph
- **TypeScript Module System Expert** — Import paths, barrel exports, type-only imports, path aliases
- **Domain-Driven Design Expert** — Bounded contexts, domain ownership, shared kernel boundaries
- **Dependency Graph Analyst** — Circular dependencies, dependency direction, coupling metrics
- **Build & Deploy Engineer** — Turborepo pipelines, workspace isolation, build cache safety
- **AI-Agent Readability Specialist** — Can an agent navigate the structure without tribal knowledge?

Each expert must speak separately. No repetition between experts.

## Scoring Model

Five dimensions, each scored 0–100. Each dimension gets its own verdict.

| Dimension             | Key                    | What it measures                                         |
| --------------------- | ---------------------- | -------------------------------------------------------- |
| Dependency Direction  | `dependencyDirection`  | Imports flow downward, no upward/lateral violations      |
| Domain Ownership      | `domainOwnership`      | Single-domain ownership per workspace, no mixed concerns |
| Circular Dependencies | `circularDependencies` | No cycles at workspace or file level                     |
| Build Graph Integrity | `buildGraphIntegrity`  | Turborepo + tsconfig references match declared deps      |
| Package Bloat         | `packageBloat`         | Shared packages stay within their defined role           |

**Scoring per dimension:**

- ✅ **100** — No violations found
- ✅ **81–99** — Minor issues (warnings only, no structural risk)
- ⚠️ **60–80** — Moderate issues (violations exist but are contained)
- ⚠️ **40–59** — Significant issues (multiple violations, structural risk)
- ❌ **0–39** — Critical (systemic boundary failure)

**Deduction guide** — start at 100 and subtract:

- Each undeclared dependency: −10
- Each direction violation (upward/lateral import): −15
- Each circular dependency: −20
- Each orphaned or phantom workspace: −10
- Each tsconfig/turborepo mismatch: −10
- Each package bloat concern (content drifts from declared role): −10
- Each barrel re-export sprawl: −5

Floor at 0 — no negative scores.

## Instructions

### Step 0 — Scope Detection

**Step 0a — Verify monorepo:**
Check for any of: `workspaces` in root `package.json`, `pnpm-workspace.yaml`,
`turbo.json`, `nx.json`, `lerna.json`, or convention dirs `apps/`/`services/`/`packages/`.

```bash
HAS_MONOREPO=0
jq -e '.workspaces' package.json >/dev/null 2>&1 && HAS_MONOREPO=1
[ -f pnpm-workspace.yaml ] && HAS_MONOREPO=1
[ -f turbo.json ] && HAS_MONOREPO=1
[ -f nx.json ] && HAS_MONOREPO=1
[ -f lerna.json ] && HAS_MONOREPO=1
ls -d apps/ services/ packages/ 2>/dev/null | grep -q . && HAS_MONOREPO=1
echo "monorepo=$HAS_MONOREPO"
```

If `HAS_MONOREPO=0`, output:

> **Not a monorepo, skill stops.** This skill audits workspace boundaries
> across multiple packages. For single-package repos, run a code-quality
> or architecture review skill instead.

Stop. Do not proceed to Step 0b or later phases.

**Step 0b — Detect default branch:**

```bash
BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$BASE" ] && BASE=$(git rev-parse --abbrev-ref HEAD)
```

Run: `git diff $BASE...HEAD --name-only`

Focus on changes in:

- `packages/` — any shared package
- `services/` — any service workspace
- `apps/` — frontend workspace
- `package.json` files (root and workspace-level)
- `tsconfig.json` files
- `turbo.json`
- Import paths in changed `.ts` / `.tsx` files

If no structural files changed, run a baseline audit of the current dependency graph.

Use `git` commands only — do NOT use `gh` CLI or GitHub API.

### Phase 1 — Workspace Inventory

**Step 1a — Read every `package.json`:**
Read the root `package.json` to get the `workspaces` globs.
Then read the `package.json` in **every** directory under `apps/`, `services/`, and `packages/`.
Do not skip any. Build the dependency table from `dependencies` AND `devDependencies`.

**Step 1b — Find orphaned directories:**
List all immediate child directories under `apps/`, `services/`, and `packages/`:

```bash
ls -d apps/*/ services/*/ packages/*/
```

For each directory, check whether a `package.json` exists:

```bash
for dir in apps/*/ services/*/ packages/*/; do
  [ -f "$dir/package.json" ] && echo "✅ $dir" || echo "❌ $dir (orphaned)"
done
```

An orphaned directory (no `package.json`) matched by a workspace glob creates confusion
for agents and developers. Flag every one.

**Step 1c — Produce the inventory table:**

| Workspace | Type                    | Depends On | Depended On By |
| --------- | ----------------------- | ---------- | -------------- |
| _name_    | app / service / package | _list_     | _list_         |

Verify:

- Every workspace listed in root `package.json` `workspaces` actually exists.
- Every directory in `apps/`, `services/`, `packages/` that has a `package.json` is listed.
- No orphaned directories (directory exists but no `package.json`).
- No phantom workspaces (listed but directory missing).

### Phase 2 — Dependency Direction Audit

The allowed dependency flow is strictly one-directional: shared packages → services → apps.

**Actual dependency graph for this repo:**

```!
bash ${CLAUDE_SKILL_DIR}/scripts/build-dep-graph.sh
```

**Step 2a — Declared vs actual dependencies:**

First detect the npm scope used by workspace packages:

```bash
SCOPE=$(grep -h '"name":' packages/*/package.json apps/*/package.json services/*/package.json 2>/dev/null \
  | head -1 | sed -n 's/.*"\(@[^/]*\)\/.*/\1/p')
```

For every workspace, compare what is declared in `package.json` (`dependencies` + `devDependencies`)
against what is actually imported in source files. Run for each workspace:

```bash
grep -r "from '$SCOPE/" <workspace>/src/ --include="*.ts" --include="*.tsx" -h \
  | sed "s/.*from '//;s/'.*//" | sort -u
```

Compare this list against the workspace's `package.json`. Flag any import of a `$SCOPE/*`
package that is NOT declared as a dependency. These are **undeclared dependencies** — they work
by accident (workspace hoisting) but break build ordering in tools like Turborepo / Nx.

**Step 2b — Direction violations:**
For each changed file (or all files in baseline mode), verify:

- **No upward imports** — a package must never import from a service or app.
- **No lateral service imports** — services must never import from each other.
- **No frontend-to-service imports** — frontend consumes contracts, not service internals.
- **No bypass of shared schema/type packages** — if the repo has a shared contract/types/schemas package (e.g., `packages/contracts`, `packages/types`, `packages/schemas`), services must consume types from it rather than redefine request/response shapes locally.

Flag every violation with the exact import statement and file path.

### Phase 3 — Domain Ownership Check

For each workspace, verify single-domain ownership:

| Check                  | What to look for                                                               |
| ---------------------- | ------------------------------------------------------------------------------ |
| Mixed concerns         | Does a service handle multiple unrelated domains?                              |
| Leaking internals      | Does a package export implementation details?                                  |
| Shared package bloat   | Are shared packages (`common`/`shared`/`utils`/`core`/`lib`) growing beyond their declared role? |
| Duplicate definitions  | Are Zod schemas or types defined in multiple places?                           |
| Re-export sprawl       | Are barrel files re-exporting too many unrelated things?                       |

**Step 3a — Package bloat measurement:**

Detect shared/utility packages — those whose name suggests a generic role
(`common`, `shared`, `utils`, `core`, `lib`):

```bash
ls -d packages/*/ 2>/dev/null | grep -E '/(common|shared|utils?|core|lib)/?$'
```

For each detected package, read its `package.json` `description` field — that
is the declared role. Then count source files and inspect contents:

```bash
PKG="packages/common"   # repeat per detected package
find "$PKG/src" -name "*.ts" | head -30
wc -l "$PKG"/src/**/*.ts 2>/dev/null
```

Flag any module whose contents drift from the declared role:

- Business logic in a "types/constants/utilities" package
- Query building, DB access, or infrastructure code in a "shared" package
- Domain-specific code in a generic-named package
- Framework integration code (HTTP handlers, route definitions) in a "core" package

If `package.json` has no `description`, flag that as a separate finding —
shared packages must declare their role for boundary enforcement.

### Phase 4 — Circular Dependency Detection

Check for circular dependencies at two levels:

**Workspace level:**

- Inspect `package.json` dependencies across all workspaces.
- No workspace may depend on a workspace that depends back on it.

**File level (within changed files):**

- Look for import cycles within a single workspace.
- Flag any file that imports from a module that imports back from it.

For detected cycles, provide:

- The exact cycle path (A → B → C → A)
- Which direction to break
- Suggested refactor (extract shared type, introduce interface, etc.)

### Phase 5 — Build Graph Integrity

**Step 5a — TypeScript project references:**
Read `tsconfig.json` in every workspace that declares `composite: true`. Verify:

- `references` entries match `package.json` dependencies.
- Workspaces with internal dependencies use `composite: true` to enable `tsc --build`.

```bash
for dir in apps/*/ services/*/ packages/*/; do
  [ -f "$dir/tsconfig.json" ] && echo "--- $dir ---" && grep -A10 '"references"' "$dir/tsconfig.json"
done
```

Flag any workspace that has dependencies but no `references`, or `references` that
do not match `package.json`.

**Step 5b — Build isolation check:**

- Can each workspace build independently when its dependencies are built?
- Are there implicit build-order assumptions not captured in config?
- Do any undeclared dependencies (from Phase 2a) create race conditions in parallel builds?

### Phase 6 — Consolidated Boundary Map

Produce:

**Violation Summary:**

| Violation | Severity        | File   | Details        |
| --------- | --------------- | ------ | -------------- |
| _type_    | High/Medium/Low | _path_ | _what and why_ |

**Boundary Health Assessment:**

| Dimension             | Status   | Notes |
| --------------------- | -------- | ----- |
| Dependency direction  | ✅/⚠️/❌ |       |
| Domain ownership      | ✅/⚠️/❌ |       |
| Circular dependencies | ✅/⚠️/❌ |       |
| Build graph integrity | ✅/⚠️/❌ |       |
| Package bloat         | ✅/⚠️/❌ |       |

### Phase 7 — Improvements

If any violations are found, provide two strategies:

**Minimal Safe Fix** (short term, low disruption):

- Specific import corrections
- Dependency declarations to add or remove
- Files to move within the existing structure

**Structural Redesign** (if boundaries are systemically broken):

- Workspace splits or merges
- New shared package extraction
- Shared contract/schema package reorganization
- Build pipeline adjustments

Prioritize by: **Boundary risk x Blast radius x Fix effort**

## Output Constraints

- No vague "improve the structure" advice.
- Every finding must reference a specific file, import, or dependency declaration.
- Separate confirmed violations from assumptions from unknowns.
- If insufficient information to conclude, state: "Insufficient information to conclude".
- This audit measures structural boundaries — not code quality or test coverage.
- The JSON contract block is mandatory — never omit it.
- Every deduction must cite the exact violation that caused it.

## Contract

Append this JSON block to every audit output — it is the verifiable contract:

```json
{
  "agent": "review-monorepo",
  "branch": "<branch>",
  "date": "<today>",
  "verdictThresholds": { "✅": ">80", "⚠️": "60–80", "❌": "<60" },
  "scores": {
    "dependencyDirection": { "score": 0, "verdict": "✅|⚠️|❌" },
    "domainOwnership": { "score": 0, "verdict": "✅|⚠️|❌" },
    "circularDependencies": { "score": 0, "verdict": "✅|⚠️|❌" },
    "buildGraphIntegrity": { "score": 0, "verdict": "✅|⚠️|❌" },
    "packageBloat": { "score": 0, "verdict": "✅|⚠️|❌" }
  },
  "deductions": [
    { "dimension": "<key>", "points": 0, "reason": "specific finding" }
  ],
  "violations": { "high": 0, "medium": 0, "low": 0 },
  "findings": ["specific boundary violations"],
  "improvements": ["specific recommendations"]
}
```

## Optional: Self-Correction (Manual)

After reviewing the output, you may paste the findings into a new prompt:

> "Here are the findings from my monorepo audit. Which of these might be incorrect
> due to missing context? What additional data would increase confidence?"

IMPORTANT: This step must be human-initiated — never auto-dismiss findings.
The human decides what to act on.
