---
name: review-design
description: Design principles audit. Use when evaluating whether code changes follow the 24 structural design principles for agent-readable code. Checks file design, separation of concerns, schema integrity, agent reliability, and safety.
---

# Review Design — Design Principles Audit

## Purpose

Evaluate whether code changes follow the 24 structural design principles. This skill
activates only the relevant principle groups based on what changed — not all 24 on every file.

This audit complements `/review-ai-compat` (which checks agent readability and structural
coding rules). This skill checks **design quality** — whether the code is composed correctly,
whether schemas are the source of truth, whether layers respect their boundaries, and whether
the code is anchored to concrete examples.

## Expert Panel

You are a review board composed of:

- **Software Architect** — File cohesion, module boundaries, dependency direction
- **Schema & Type Expert** — Zod as source of truth, type derivation, contract compliance
- **Agent Reliability Specialist** — Constraints as infrastructure, golden examples, concrete terms
- **Safety & Verification Lead** — Error handling, evidence gates, test coverage, pre-flight checks
- **Frontend State Specialist** — State lifecycle routing, component composition (conditional)
- **Protocol Engineer** — MCP validation, critical path ownership (conditional)

Each expert speaks separately. No repetition between experts.

## Principle Groups

| Group                      | Principles             | Activates when...                               |
| -------------------------- | ---------------------- | ----------------------------------------------- |
| A: File & Module Design    | P1, P12, P13, P14, P16 | Any `.ts`/`.tsx` source file changed            |
| B: Separation of Concerns  | P2, P3, P21            | Service, route, or dbhandler files changed      |
| C: Schema & Type Integrity | P15, P25, P26          | Contract, schema, or type files changed         |
| D: Agent Reliability       | P4, P5, P8, P9, P17    | New files created or config changed             |
| E: Safety & Verification   | P7, P10, P20, P23, P24 | Error handling, tests, or pipeline code changed |
| +P22                       | State lifecycle        | Frontend `.tsx` components changed              |
| +P18, P19                  | MCP principles         | MCP server code changed                         |

## Instructions

### Step 0 — Scope Detection + Group Selection

Detect the base branch (auto: `develop` for GitFlow, `main`/`master` for trunk-based,
`release` if used as integration branch):

```bash
BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$BASE" ] && for b in develop main master release; do
  git show-ref --verify --quiet "refs/heads/$b" && BASE="$b" && break
done
[ -z "$BASE" ] && BASE=$(git rev-parse --abbrev-ref HEAD)
echo "base=$BASE"
```

Run: `git diff $BASE...HEAD --name-only`

Use `git` commands only — do NOT use `gh` CLI or GitHub API.

Classify changed files and activate principle groups:

```bash
# Get changed files
CHANGED=$(git diff $BASE...HEAD --name-only)

# Check for new files (Group D trigger)
NEW_FILES=$(git diff $BASE...HEAD --diff-filter=A --name-only)
```

**Activation rules:**

- **Group A**: activated if ANY `.ts` or `.tsx` source file changed (excluding test files)
- **Group B**: activated if files match `**/services/**`, `**/routes/**`, `**/repositories/**`, or `**/data-access/**`
- **Group C**: activated if files match `**/contracts/**`, `**/schemas/**`, `**/types/**`, or `**/interfaces/**`
- **Group D**: activated if new files were created OR `*config*`, `eslint*`, `tsconfig*` changed
- **Group E**: activated if `*/tests/*`, `*error*`, `*AppError*`, or pipeline files changed
- **+P22**: activated if any `.tsx` or `.jsx` file changed
- **+P18, P19**: activated if MCP server code changed (any file matching `**/mcp-*/**` or files importing `@modelcontextprotocol/*`)

List which groups are active and which are skipped. Skip inactive groups entirely.

### Phase 1 — File & Module Design (Group A)

**Skip if Group A is not active.**

For each changed source file, evaluate:

| Principle                       | Diagnostic Question                                  | Evidence Command                                                        |
| ------------------------------- | ---------------------------------------------------- | ----------------------------------------------------------------------- |
| P1: One responsibility per file | Can you name what this file does in 3 words?         | Read the file — if you cannot summarize in 3 words, flag it             |
| P12: Design for deletion        | Can you delete this without editing ten other files? | `codegraph_callers` for each exported symbol — if callers > 10, flag it |
| P13: Leaf modules, zero deps    | How deep is the import chain to reach this?          | `codegraph_callees` to measure dependency depth                         |
| P14: Don't split one thing      | Do these files only make sense together?             | Check if paired files exist that cannot function independently          |
| P16: Simplicity is structural   | Can this be simpler?                                 | Compare approach to the simplest known pattern for this task            |

**Gather evidence (prefer codegraph, fall back to grep):**

For each changed file, use `codegraph_search` to find its symbols, then:

- `codegraph_callers` on exported symbols → reverse dependency count (P12)
- `codegraph_callees` on the file's main function → dependency depth (P13)
- `codegraph_impact` on changed symbols → blast radius of the change

```bash
# File lengths (flag > 200 lines)
for file in <changed-source-files>; do
  wc -l "$file"
done

# Fallback: Import count per file (flag > 8 imports)
for file in <changed-source-files>; do
  echo "$(grep -c '^import ' "$file") imports — $file"
done

# Fallback: Reverse dependency count (how many files import this one?)
for file in <changed-source-files>; do
  BASENAME=$(basename "$file" .ts)
  grep -rl "from '.*/$BASENAME'" --include="*.ts" --include="*.tsx" | wc -l
done
```

### Phase 2 — Separation of Concerns (Group B)

**Skip if Group B is not active.**

For each changed service, route, or dbhandler file, evaluate:

| Principle                         | Diagnostic Question                                           | What to Check                                        |
| --------------------------------- | ------------------------------------------------------------- | ---------------------------------------------------- |
| P2: Separate computation from I/O | Does this function do logic AND side effects?                 | Functions should be pure OR perform I/O — not both   |
| P3: Small API, hidden complexity  | Can consumers ignore the implementation?                      | Exported surface should be minimal; internals hidden |
| P21: Each layer has one job       | Is this code in the right layer? What must this layer NOT do? | See layer table below                                |

**Layer responsibility reference (from P21):**

| Layer             | Does                          | Must NOT                                            |
| ----------------- | ----------------------------- | --------------------------------------------------- |
| contracts/schemas | Define Zod schemas            | Contain logic, import from services                 |
| contracts/routes  | Define typed route contracts  | Contain implementation                              |
| services          | Business logic, orchestration | Access DB directly, define response shapes          |
| data access layer | Build and execute queries against external systems (DB, API) | Transform to contract types, contain business logic |
| routes            | Wire HTTP to service calls    | Contain business logic, access DB                   |
| ui-modules        | Compose UI from components    | Contain business logic, call DB                     |

**Gather evidence:**

```bash
# Check for DB/external client imports outside data access layer
grep -rEn "from ['\"]( oracledb|pg|mysql2|mssql|mongodb|mongoose|@aws-sdk/client-dynamodb|dynamoose|redis|ioredis|cassandra-driver|@elastic/elasticsearch|prisma|typeorm|sequelize|knex|drizzle)['\"]" <changed-files> \
  | grep -vE "(repositories|data-access|dbhandlers)/"

# Check for business logic in route handlers (flag functions > 10 lines in routes)
grep -c "function\|=>" <changed-route-files>
```

### Phase 3 — Schema & Type Integrity (Group C)

**Skip if Group C is not active.**

For each changed contract, schema, or type file, evaluate:

| Principle                          | Diagnostic Question                                                | What to Check                                                                   |
| ---------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------- |
| P15: One schema, many shapes       | Is the same field defined in two places?                           | Schemas use `.pick()`, `.omit()`, `.partial()` — no duplicate field definitions |
| P25: Pipeline stages narrow types  | Does this stage receive a broader type and produce a narrower one? | Type inputs should be wider than type outputs                                   |
| P26: Types are the design artifact | Were types defined before implementation, or added after?          | Types derived via `z.infer<>`, not hand-written interfaces                      |

**Gather evidence:**

```bash
# Find hand-written interfaces that duplicate schema fields
grep -rn "^export interface\|^export type" <changed-files>

# Find z.infer usage (good — types derived from schemas)
grep -rn "z\.infer" <changed-files>

# Find duplicate field names across schema files
grep -rn "z\.string()\|z\.number()\|z\.boolean()" --include="*.ts" \
  $(find . -type d \( -name schemas -o -name contracts \) -not -path '*/node_modules/*') \
  2>/dev/null | sed 's/.*: //' | sort | uniq -d
```

### Phase 4 — Agent Reliability (Group D)

**Skip if Group D is not active.**

For new files and config changes, evaluate:

| Principle                                 | Diagnostic Question                                            | What to Check                                                       |
| ----------------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------- |
| P4: Wrong abstraction > duplication       | Is this shared because it IS the same, or just LOOKS the same? | New shared utils must have 2+ call sites                            |
| P5: Constraints are infrastructure        | Would removing this rule make agents more or less reliable?    | No lint rules removed, no constraints bypassed                      |
| P8: Anchor to concrete examples           | Is the agent generating from a reference or from theory?       | New code follows the golden example declared by the project (see CLAUDE.md, README, or `examples/` dir) |
| P9: Define terms concretely               | Could this rule be interpreted two different ways?             | Config values, constants, enums are explicit — no ambiguous strings |
| P17: Golden examples guide transformation | Is there a reference file to follow?                           | New files mirror structure of existing reference implementations    |

**Gather evidence:**

```bash
# Check for removed eslint-disable or lint rule changes
git diff $BASE...HEAD -- '*.ts' '*.tsx' | grep -i "eslint-disable"
git diff $BASE...HEAD -- '*eslint*' '*config*'

# Check new shared utils have multiple callers
for file in <new-files-in-utils-or-helpers>; do
  BASENAME=$(basename "$file" .ts)
  echo "--- $BASENAME ---"
  grep -rl "$BASENAME" --include="*.ts" --include="*.tsx" | grep -v "$file"
done

# Compare new file structure against project's declared golden example
# (path declared in CLAUDE.md / README / examples/; substitute below)
GOLDEN_EXAMPLE_PATH="<path declared by project>"
ls -la "$GOLDEN_EXAMPLE_PATH"
```

### Phase 5 — Safety & Verification (Group E)

**Skip if Group E is not active.**

For error handling, test, and pipeline files, evaluate:

| Principle                       | Diagnostic Question                                     | What to Check                                                     |
| ------------------------------- | ------------------------------------------------------- | ----------------------------------------------------------------- |
| P7: Fail loudly                 | If this fails silently, who notices?                    | No empty catch blocks, no swallowed errors, no silent fallbacks   |
| P10: Evidence first             | Can every claim trace back to a source?                 | Agent outputs include `sources[]`, assertions have messages       |
| P20: Tests are safety net       | Can the output be verified without reading it?          | Test directory mirrors source 1:1                                 |
| P23: Map errors to status codes | Which exact HTTP status code does this error produce?   | Custom error classes use explicit status codes (never default 500/INTERNAL_SERVER_ERROR) |
| P24: Verify before you start    | Has every assumption been grounded before writing code? | Pre-conditions checked, dependencies verified                     |

**Gather evidence:**

```bash
# Find empty catch blocks
grep -rn "catch" <changed-files> -A2 | grep -B1 "}"

# Find silent error swallowing
grep -rn "catch.*{" <changed-files> -A3 | grep "console\.\|// \|/\*"

# Check test mirror structure — try common conventions
for file in <changed-source-files>; do
  BASE_NO_EXT="${file%.ts}"
  CANDIDATES=(
    "$(echo "$file" | sed 's|/src/|/tests/unit/|; s|\.ts$|.test.ts|')"
    "$(echo "$file" | sed 's|/src/|/tests/|; s|\.ts$|.test.ts|')"
    "$(echo "$file" | sed 's|/src/|/__tests__/|; s|\.ts$|.test.ts|')"
    "${BASE_NO_EXT}.test.ts"
    "${BASE_NO_EXT}.spec.ts"
  )
  FOUND=""
  for c in "${CANDIDATES[@]}"; do
    [ -f "$c" ] && FOUND="$c" && break
  done
  [ -n "$FOUND" ] && echo "test exists: $FOUND" || echo "MISSING test for: $file"
done

# Check for explicit AppError status codes
grep -rEn "new [A-Z][A-Za-z]*Error\(" <changed-files> | grep -v "StatusCodes\."
```

### Phase 6 — Conditional Principles

**P22: State belongs where its lifecycle lives** — only if frontend `.tsx` changed.

For each changed frontend component:

- Is server state in a server-state lib (TanStack Query / SWR / RTK Query / Apollo) — not `useState`?
- Is form state in a form lib (react-hook-form / Formik / React Final Form) — not manual `onChange`?
- Is UI-only state in `useState` — not Context?
- Is cross-component state in Context or a global store (Zustand / Redux / Jotai / Recoil) — not prop drilling?

```bash
# Find useState usage that might be server state
grep -rn "useState.*data\|useState.*loading\|useState.*error" <changed-tsx-files>

# Find manual form state management
grep -rn "useState.*value\|onChange.*setState" <changed-tsx-files>
```

**P18 + P19: MCP principles** — only if MCP server code changed.

- P18: Does the tool validate at both protocol (JSON Schema) and runtime (Zod) level?
- P19: Are auth, errors, and versioning built-in or delegated to third parties?

```bash
# Auto-discover MCP server dirs, then check for dual validation
MCP_DIRS=$(find . -type d -name 'mcp-*' 2>/dev/null)
[ -z "$MCP_DIRS" ] && MCP_DIRS=$(grep -rl "@modelcontextprotocol/" --include="*.ts" --include="*.js" . 2>/dev/null | xargs -I{} dirname {} | sort -u)
[ -n "$MCP_DIRS" ] && grep -rn "zodSchema\|jsonSchema\|inputSchema" $MCP_DIRS
```

### Phase 7 — Design Principles Scorecard

**Principle Evaluation Table** — one row per checked principle:

| #    | Principle | Status             | Evidence                        |
| ---- | --------- | ------------------ | ------------------------------- |
| P*n* | _name_    | PASS / WARN / FAIL | _specific file:line or finding_ |

Only include principles from active groups. Skip principles from inactive groups.

**Group Summary Table:**

| Group                      | Checked | Pass | Warn | Fail |
| -------------------------- | ------- | ---- | ---- | ---- |
| A: File & Module Design    | _n_     | _n_  | _n_  | _n_  |
| B: Separation of Concerns  | _n_     | _n_  | _n_  | _n_  |
| C: Schema & Type Integrity | _n_     | _n_  | _n_  | _n_  |
| D: Agent Reliability       | _n_     | _n_  | _n_  | _n_  |
| E: Safety & Verification   | _n_     | _n_  | _n_  | _n_  |
| Conditional (P22/P18/P19)  | _n_     | _n_  | _n_  | _n_  |

**Design Health Score:** `(total pass / total checked) * 10`

Scoring guide:

- **8-10** — Strong design alignment. No action needed.
- **5-7** — Acceptable with warnings. Review flagged principles.
- **1-4** — Design drift detected. Address FAIL items before merge.

This score measures design principle adherence — it is distinct from the AI Patch Safety
Score used by `/review-ai-compat` (which measures agent modifiability dimensions).

### Phase 8 — Improvements

If any principles scored WARN or FAIL, provide:

**Quick Fixes** (per-principle, low disruption):

- The specific principle violated
- The exact file and line
- What to change and why

**Structural Improvements** (if 3+ FAILs in one group):

- Pattern-level fix that addresses the root cause
- Reference to the golden example that demonstrates the correct pattern

Prioritize by: **Principle severity x Number of violations x Fix effort**

## Contract

Append this JSON block to every audit output — it is the verifiable contract:

```json
{
  "agent": "review-design",
  "branch": "<branch>",
  "date": "<today>",
  "verdict": "PASS|FLAG|DRIFT",
  "groups": {
    "fileModuleDesign": { "checked": 0, "pass": 0, "warn": 0, "fail": 0 },
    "separationOfConcerns": { "checked": 0, "pass": 0, "warn": 0, "fail": 0 },
    "schemaTypeIntegrity": { "checked": 0, "pass": 0, "warn": 0, "fail": 0 },
    "agentReliability": { "checked": 0, "pass": 0, "warn": 0, "fail": 0 },
    "safetyVerification": { "checked": 0, "pass": 0, "warn": 0, "fail": 0 },
    "conditional": { "checked": 0, "pass": 0, "warn": 0, "fail": 0 }
  },
  "designHealthScore": 0,
  "findings": ["specific principle violations"],
  "improvements": ["specific recommendations"]
}
```

**Verdict rules:**

- **PASS** — Design Health Score ≥ 8
- **FLAG** — Design Health Score 5–7
- **DRIFT** — Design Health Score < 5

## Output Constraints

- No vague "follow the principles" advice.
- Every finding must reference a specific file, function, line, or pattern.
- Every WARN or FAIL must cite the diagnostic question that triggered it.
- Separate confirmed violations from assumptions.
- If insufficient information to conclude, state: "Insufficient information to conclude".
- This audit measures design principle adherence — not general code quality or agent readability.

## Optional: Self-Correction (Manual)

After reviewing the output, you may paste the findings into a new prompt:

> "Here are the findings from my design principles audit. Which of these might be incorrect
> due to missing context? What additional data would increase confidence?"

IMPORTANT: This step must be human-initiated — never auto-dismiss findings.
The human decides what to act on.
