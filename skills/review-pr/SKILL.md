---
name: review-pr
description: Full PR review as a merge gate. Use before merging any non-trivial PR. Checks automated validation, governance principles, anti-entropy rules, harmonic constraints, code conventions, and production readiness.
---

# Review PR — AI Governance Merge Gate

## Purpose

Full pre-merge review as an automated checklist. This skill is the final gate before merge — it combines automated
validation, governance principle verification, and an AI Patch Safety Score into a single
pass/fail decision.

This is NOT a code review for logic correctness — it is a structural and governance review.
For domain-specific depth, this skill recommends targeted audit skills.

## Expert Panel

You are a review board composed of:

- **AI Governance Auditor** — Enforces the 7 core governance principles (defined in Phase 2 below)
- **TypeScript Strictness Validator** — No `any`, explicit types, safe patterns
- **Structural Integrity Engineer** — Harmonic constraints, file/function size, complexity
- **Convention Compliance Checker** — Code style, imports, naming, formatting
- **Security & Secret Hygiene Reviewer** — No leaked secrets, safe env handling
- **Production Readiness Assessor** — Rollback safety, migration safety, observability

Each expert must speak separately. No repetition between experts.

## Instructions

### Step 0 — Scope Detection & Change Classification

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

**Step 0a — Classify every changed file:**

```bash
# Get all changed files
git diff $BASE...HEAD --name-only

# Count changes by area (common monorepo / repo conventions)
CHANGED=$(git diff $BASE...HEAD --name-only)
echo "--- Change Summary ---"
echo "Backend:   $(echo "$CHANGED" | grep -E '^(services|server|backend|apps/api)/|/(server|backend)/' | wc -l)"
echo "Frontend:  $(echo "$CHANGED" | grep -E '^(apps/web|apps/frontend|web|client|frontend)/|/(frontend|client)/' | wc -l)"
echo "Packages:  $(echo "$CHANGED" | grep -E '^(packages|libs|modules)/' | wc -l)"
echo "CI/CD:     $(echo "$CHANGED" | grep -E '^\.(github|gitlab|circleci|azure-pipelines|deploy)/|^(skaffold|Dockerfile|docker-compose|Jenkinsfile)' | wc -l)"
echo "Tests:     $(echo "$CHANGED" | grep -E 'test|spec' | wc -l)"
echo "Config:    $(echo "$CHANGED" | grep -E 'package\.json|tsconfig|(turbo|nx|lerna)\.json|pnpm-workspace|\.eslint|\.prettier' | wc -l)"
echo "Docs:      $(echo "$CHANGED" | grep -E '\.md$' | wc -l)"
```

**Step 0b — Measure change magnitude:**

```bash
# Lines added/removed
git diff $BASE...HEAD --stat | tail -1

# Number of commits
git log $BASE..HEAD --oneline | wc -l

# Files changed
git diff $BASE...HEAD --name-only | wc -l
```

**Step 0c — Read the full diff for code review:**

```bash
git diff $BASE...HEAD
```

Read every changed file in full. Do not skip any file — governance violations hide in files
that "look fine."

### Phase 1 — Automated Validation Status

These checks MUST pass before any manual review proceeds.

**Step 1a — Check if CI has already validated:**

```bash
# Check recent commit messages for CI status hints
git log $BASE..HEAD --oneline

# Verify key config files haven't been tampered with
git diff $BASE...HEAD --name-only | grep -E 'eslint|prettier|vitest|tsconfig'
```

**Step 1b — Run local validation (if not already run by CI):**

The CI pipeline runs these gates in order:

Detect the package manager from the lockfile, then run gates with the appropriate command:

```bash
if [ -f yarn.lock ]; then
  PM=yarn; INSTALL="yarn install --immutable"; AUDIT="yarn npm audit --recursive --severity=moderate"; RUN="yarn"
elif [ -f pnpm-lock.yaml ]; then
  PM=pnpm; INSTALL="pnpm install --frozen-lockfile"; AUDIT="pnpm audit --audit-level=moderate"; RUN="pnpm"
elif [ -f bun.lockb ]; then
  PM=bun; INSTALL="bun install --frozen-lockfile"; AUDIT="bun audit"; RUN="bun run"
else
  PM=npm; INSTALL="npm ci"; AUDIT="npm audit --audit-level=moderate"; RUN="npm run"
fi
echo "package manager=$PM"
```

Then run gates in order:

1. `$INSTALL`
2. `$AUDIT`
3. `$RUN format:check`
4. `$RUN lint`
5. `$RUN build`
6. `$RUN test`

For the PR review, verify each gate:

```bash
# Check if lint rules have been disabled or removed in this PR
git diff $BASE...HEAD -- '*.ts' '*.tsx' | grep -n "eslint-disable\|@ts-ignore\|@ts-expect-error\|@ts-nocheck"

# Check if any eslint config was modified
git diff $BASE...HEAD -- '**/.eslintrc*' '**/eslint.config*'

# Check if vitest config was modified
git diff $BASE...HEAD -- '**/vitest.config.ts'

# Check if tsconfig was modified
git diff $BASE...HEAD -- '**/tsconfig.json' '**/tsconfig.*.json'
```

Flag every `eslint-disable`, `@ts-ignore`, `@ts-expect-error`, or `@ts-nocheck` added in this PR.
These are governance bypasses — each one needs justification.

**Step 1c — Check for test coverage on changed code:**

```bash
# Find test files added/changed in this PR
git diff $BASE...HEAD --name-only | grep -E '\.test\.ts$|\.spec\.ts$'

# Find source files changed without corresponding test changes
git diff $BASE...HEAD --name-only | grep -E '\.ts$' | grep -v '\.test\.' | grep -v '\.spec\.' | grep '/src/'
```

For each source file changed, check if a corresponding test file exists.
Untested changes in critical paths (data-access layer, services, routes/controllers) are a merge risk.

### Phase 2 — AI Governance Principles Check

For every changed file, evaluate against these 7 governance principles:

**Principle 1 — Determinism Over Cleverness:**

```bash
# Hidden state: global mutable variables
git diff $BASE...HEAD -- '*.ts' '*.tsx' | grep -n "^+.*\(^let \|^var \)" | grep -v "^+.*const "

# Runtime magic: dynamic imports, eval, Function constructor
git diff $BASE...HEAD -- '*.ts' '*.tsx' | grep -n "^+.*\(dynamic import\|eval(\|new Function\|Reflect\.\|Proxy\)"
```

**Principle 2 — Explicit Contracts:**

```bash
# any usage in new code
git diff $BASE...HEAD -- '*.ts' '*.tsx' | grep -n "^+.*\(: any\|as any\|<any>\)"

# Implicit return types on exported functions
git diff $BASE...HEAD -- '*.ts' '*.tsx' | grep -n "^+export.*function\|^+export const.*=>" | grep -v ":"
```

**Principle 3 — Shallow Cognitive Complexity:**

```bash
# Check file lengths of changed files (flag >200 lines)
for file in $(git diff $BASE...HEAD --name-only | grep -E '\.ts$|\.tsx$'); do
  [ -f "$file" ] && lines=$(wc -l < "$file") && [ "$lines" -gt 200 ] && echo "⚠️ $file: $lines lines (limit: 200)"
done

# Check for deep nesting (4+ levels of indentation)
for file in $(git diff $BASE...HEAD --name-only | grep -E '\.ts$|\.tsx$'); do
  [ -f "$file" ] && grep -n "^                " "$file" | head -5 && echo "--- $file ---"
done
```

**Principle 4 — Boundary Integrity:**

```bash
# Cross-service imports (services importing from each other)
# Adjust SERVICE_ROOT regex if your project uses a different layout
SERVICE_ROOT='^(services|apps/api|server|backend)/'
for file in $(git diff $BASE...HEAD --name-only | grep -E "${SERVICE_ROOT}.*\.ts$"); do
  service=$(echo "$file" | sed -E "s|${SERVICE_ROOT}([^/]+)/.*|\1|")
  [ -f "$file" ] && grep -E "from ['\"].*/(services|apps/api|server|backend)/" "$file" | grep -v "/$service/" && echo "⚠️ Cross-service import in $file"
done

# DB / external client access outside data-access layer
DB_DRIVERS='oracledb|pg|mysql2|mssql|mongodb|mongoose|@aws-sdk/client-dynamodb|dynamoose|redis|ioredis|cassandra-driver|@elastic/elasticsearch|prisma|typeorm|sequelize|knex|drizzle'
for file in $(git diff $BASE...HEAD --name-only | grep -E '\.ts$' | grep -vE '(repositories|data-access|dbhandlers)/'); do
  [ -f "$file" ] && grep -lE "from ['\"]($DB_DRIVERS)['\"]" "$file" 2>/dev/null && echo "⚠️ DB access outside data-access layer: $file"
done
```

**Principle 5 — Explicit Error Surfaces:**

```bash
# Swallowed errors (empty catch blocks)
git diff $BASE...HEAD -- '*.ts' '*.tsx' | grep -A2 "^+.*catch" | grep -B1 "^+.*}"

# Silent fallback (catch blocks that return default values without logging)
for file in $(git diff $BASE...HEAD --name-only | grep -E '\.ts$'); do
  [ -f "$file" ] && grep -n "catch" "$file" | head -5
done
```

**Principle 6 — Structural Testability:**

Already covered in Phase 1c. Additionally check:

```bash
# Critical-path files without tests (services / routes / data-access)
for file in $(git diff $BASE...HEAD --name-only | grep -E '(services|routes|repositories|data-access|dbhandlers)/.*\.ts$' | grep -v '\.test\.' | grep -v '\.spec\.'); do
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
  [ -z "$FOUND" ] && echo "⚠️ No test for: $file"
done
```

**Principle 7 — AI-Modifiability Constraint:**

For each changed file, answer:

- Would an AI agent understand this file in isolation?
- Is control flow explicit?
- Are dependencies visible?
- Is state mutation obvious?
- Are error paths clear?

If any answer is "no", flag the file with explanation.

### Phase 3 — Anti-Entropy Rules

These are HARD FAILURES. Any violation blocks the merge.

```bash
# Rule 1: No global mutable state
for file in $(git diff $BASE...HEAD --name-only | grep -E '\.ts$|\.tsx$'); do
  [ -f "$file" ] && grep -n "^let \|^var " "$file" && echo "^^^ $file"
done

# Rule 2: No business logic in UI rendering (DB / external client imports in .tsx files)
DB_DRIVERS='oracledb|pg|mysql2|mssql|mongodb|mongoose|@aws-sdk/client-dynamodb|dynamoose|redis|ioredis|cassandra-driver|@elastic/elasticsearch|prisma|typeorm|sequelize|knex|drizzle'
for file in $(git diff $BASE...HEAD --name-only | grep -E '\.tsx$'); do
  [ -f "$file" ] && grep -nE "from ['\"]($DB_DRIVERS)['\"]|\.query\(" "$file" && echo "^^^ DB in UI: $file"
done

# Rule 3: No DB access outside data-access layer
DB_DRIVERS='oracledb|pg|mysql2|mssql|mongodb|mongoose|@aws-sdk/client-dynamodb|dynamoose|redis|ioredis|cassandra-driver|@elastic/elasticsearch|prisma|typeorm|sequelize|knex|drizzle'
for file in $(git diff $BASE...HEAD --name-only | grep -E '\.ts$' | grep -vE '(repositories|data-access|dbhandlers)/'); do
  [ -f "$file" ] && grep -nE "from ['\"]($DB_DRIVERS)['\"]" "$file" && echo "^^^ $file"
done

# Rule 4: No undocumented shared abstractions (shared/common packages)
for file in $(git diff $BASE...HEAD --name-only | grep -E '(packages|libs|modules)/(common|shared|utils)/.*\.ts$'); do
  [ -f "$file" ] && echo "Check: $file — is this types/constants/utilities only?"
done

# Rule 5: No dynamic runtime patching
git diff $BASE...HEAD -- '*.ts' '*.tsx' | grep -n "^+.*\(Object\.defineProperty\|prototype\.\|__proto__\)"

# Rule 6: No circular dependencies — list cross-package imports from project's own scope
# Auto-detect npm scope from root package.json (e.g., @myorg from "@myorg/pkg")
SCOPE=$(grep -m1 '"name"' package.json 2>/dev/null | sed -nE 's/.*"name": *"(@[^/"]+)\/.*/\1/p')
if [ -n "$SCOPE" ]; then
  for file in $(git diff $BASE...HEAD --name-only | grep -E '\.ts$'); do
    [ -f "$file" ] && grep "from '$SCOPE/" "$file" 2>/dev/null
  done | sort | uniq -c | sort -rn | head -20
else
  echo "No npm scope in root package.json — skipping cross-package import audit"
fi
```

### Phase 4 — Harmonic Constraints Verification

The constraints exist because agent reliability degrades beyond these limits.

```bash
# Check all changed .ts/.tsx files against constraints
for file in $(git diff $BASE...HEAD --name-only | grep -E '\.ts$|\.tsx$'); do
  if [ -f "$file" ]; then
    lines=$(wc -l < "$file")
    echo "$lines lines — $file"
  fi
done | sort -rn | head -20
```

For each changed file, verify:

| Constraint            | Limit                            | How to check                       |
| --------------------- | -------------------------------- | ---------------------------------- |
| File length           | 200 lines (skip blanks/comments) | `wc -l` on each file               |
| Function length       | 30 lines (skip blanks/comments)  | Read each function                 |
| Cyclomatic complexity | 6                                | Count decision points per function |
| Cognitive complexity  | 8                                | Count nested decisions             |
| Nesting depth         | 4                                | Check indentation levels           |
| Nested callbacks      | 3                                | Count callback nesting             |
| Parameters            | 4                                | Count function parameters          |

Flag every violation with file path and the specific function/line.

### Phase 5 — Code Convention Audit

Check the PR diff against codebase conventions:

```bash
# Array.reduce (FORBIDDEN)
git diff $BASE...HEAD -- '*.ts' '*.tsx' | grep -n "^+.*\.reduce("

# Barrel imports from major UI libs (FORBIDDEN — defeats tree-shaking)
git diff $BASE...HEAD -- '*.tsx' | grep -nE "^\+.*from ['\"]@(mui/material|chakra-ui/react|mantine/core|ant-design/icons)['\"]"

# Implicit boolean coercion (must be explicit)
git diff $BASE...HEAD -- '*.ts' '*.tsx' | grep -n "^+.*if (" | grep -v "!=\|===\|!==\|>\|<\|typeof\|instanceof"

# Missing trailing commas (check object/array endings)
git diff $BASE...HEAD -- '*.ts' '*.tsx' | grep -n "^+.*[^,]$" | grep -E "\}$|\]$" | head -20

# Short identifiers (min 2 chars, exceptions: _, i, j, id, ok, db, fn, cb, eq, gt, ne, lt, in, no, or, en)
git diff $BASE...HEAD -- '*.ts' '*.tsx' | grep -n "^+.* [a-z] [=:,)]" | grep -v "_ \|i \|j \|id\|ok\|db\|fn\|cb\|eq\|gt\|ne\|lt\|in\|no\|or\|en"

# Custom error with default INTERNAL_SERVER_ERROR status (redundant — it's the default)
git diff $BASE...HEAD -- '*.ts' | grep -nE "^\+.*new [A-Z][A-Za-z]*Error\(.*INTERNAL_SERVER_ERROR"

# Negated conditions
git diff $BASE...HEAD -- '*.ts' '*.tsx' | grep -n "^+.*if (!.*)" | head -10

# Floating promises (missing await)
git diff $BASE...HEAD -- '*.ts' | grep -n "^+.*[^await ].*Promise\|^+.*\.\(then\|catch\)(" | head -10
```

### Phase 6 — Secret & Security Hygiene

```bash
# Hardcoded secrets in new code
git diff $BASE...HEAD -- '*.ts' '*.tsx' '*.json' '*.yaml' '*.yml' | grep -in "^+.*\(password\|secret\|token\|api.key\|private.key\)" | grep -v "secretKeyRef\|SecretStore\|\.env\.\|process\.env\|secrets\.\|example\|mock\|test\|fake"

# .env files committed (should never be committed)
git diff $BASE...HEAD --name-only | grep "^\.env$\|/\.env$" | grep -v "\.example"

# New environment variables without .env.example update
git diff $BASE...HEAD -- '*.ts' | grep -n "^+.*process\.env\." | sed 's/.*process\.env\.\([A-Z_]*\).*/\1/' | sort -u
```

For each `process.env.X` reference added, verify it exists in the corresponding `.env.example`.

### Phase 7 — Constraint Preservation Check

This is a CRITICAL check. Constraints must never be silently removed.

```bash
# Lint rules removed
git diff $BASE...HEAD -- '*eslint*' | grep "^-" | grep -v "^---"

# Validation removed
git diff $BASE...HEAD -- '*.ts' | grep -E "^-.*(throw|new [A-Z][A-Za-z]*Error\(|assert|validate|\.parse\()" | head -20

# Type safety weakened
git diff $BASE...HEAD -- '*.ts' | grep "^-.*: " | grep -v "^-.*: any" | head -10
git diff $BASE...HEAD -- '*.ts' | grep "^+.*: any\|^+.*as any\|^+.*@ts-ignore\|^+.*@ts-expect-error"

# Config references removed
git diff $BASE...HEAD -- '*.json' '*.yaml' '*.yml' | grep "^-" | grep -v "^---" | head -20
```

For every removed constraint, ask: "Is this fixing a reference or removing a constraint?"
Removing a constraint without explicit permission is a merge blocker.

### Phase 8 — Production Readiness Gate

Production Readiness Gate:

| Dimension              | How to check                                                                      |
| ---------------------- | --------------------------------------------------------------------------------- |
| Determinism            | Phase 2 Principle 1 results                                                       |
| Rollback safety        | Can the change be reverted without data loss? Are DB changes backward-compatible? |
| Migration safety       | Are there schema changes? Are they additive-only?                                 |
| Observability          | Do new services/routes have health endpoints?                                     |
| Backward compatibility | Can old and new versions coexist during rolling update?                           |
| No hidden coupling     | Phase 2 Principle 4 results                                                       |

```bash
# Check for DB migration files
git diff $BASE...HEAD --name-only | grep -i "migrat\|ddl\|alter\|schema"

# Check for new routes without health endpoints
# Detect service dirs from changed files (services/, apps/api/, server/, backend/)
SERVICE_DIRS=$(git diff $BASE...HEAD --name-only | grep -E '^(services|apps/api|server|backend)/[^/]+' | sed -E 's|^(services|apps/api|server|backend)/([^/]+)/.*|\1/\2|' | sort -u)
for dir in $SERVICE_DIRS; do
  grep -rn "/health" "$dir" --include="*.ts" 2>/dev/null | head -3
  echo "--- $dir ---"
done

# Check for breaking contract changes (auto-discover contracts/schemas/types dirs)
CONTRACT_DIRS=$(find . -type d \( -name contracts -o -name schemas -o -name types -o -name interfaces \) -not -path '*/node_modules/*' 2>/dev/null)
[ -n "$CONTRACT_DIRS" ] && git diff $BASE...HEAD -- $CONTRACT_DIRS | grep "^-" | grep -v "^---" | head -20
```

### Phase 9 — AI Patch Safety Score

Score the overall PR 1-10 for AI-modifiability. Do not skip any dimension:

| Dimension                   | Score (1-10) | Justification                                                 |
| --------------------------- | ------------ | ------------------------------------------------------------- |
| Local understandability     |              | Can an agent reason about each file without reading 5 others? |
| State explicitness          |              | Is all state visible and traceable?                           |
| Control flow simplicity     |              | Can the execution path be followed linearly?                  |
| Refactor safety             |              | What would break during automated refactor?                   |
| Tribal knowledge dependency |              | Does understanding require unwritten context?                 |

**Scoring guide:**

- **7-10** — Safe for agents. No action needed.
- **4-6** — Flag for review. Improvements recommended before merge.
- **1-3** — Redesign required. Do NOT merge.

Calculate an overall average score.

### Phase 10 — Consolidated Review & Merge Decision

**Violation Summary:**

| #   | Violation | Severity                               | File   | Phase   | Details        |
| --- | --------- | -------------------------------------- | ------ | ------- | -------------- |
| V1  | _type_    | 🔴 HIGH / 🟡 MEDIUM / 🔵 LOW / ℹ️ INFO | _path_ | _phase_ | _what and why_ |

**Recommended Follow-up Audits:**

Based on the change classification from Step 0, recommend targeted audits:

| Trigger                              | Run                  |
| ------------------------------------ | -------------------- |
| Design principle concerns            | `/review-design`     |
| Monorepo / package boundary changes  | `/review-monorepo`   |
| AI-compat concerns (score <7)        | `/review-ai-compat`  |

### Merge Decision

Based on all phases, issue ONE of these decisions:

**✅ APPROVED** — All checks pass. AI Patch Safety Score >= 7. No HIGH violations.

**⚠️ CONDITIONAL** — Minor issues found. Can merge after addressing:

- List specific items that must be fixed
- State which items are blocking vs advisory

**❌ BLOCKED** — Merge blocked. Reasons:

- Any 🔴 HIGH violation
- Anti-entropy rule violation
- AI Patch Safety Score < 4
- Constraint removed without permission
- Leaked secret detected

## Contract

Append this JSON block to every audit output — it is the verifiable contract:

```json
{
  "agent": "review-pr",
  "branch": "<branch>",
  "date": "<today>",
  "mergeDecision": "APPROVED|CONDITIONAL|BLOCKED",
  "governance": {
    "automatedValidation": "pass|warn|fail",
    "governancePrinciples": "pass|warn|fail",
    "antiEntropyRules": "pass|warn|fail",
    "harmonicConstraints": "pass|warn|fail",
    "codeConventions": "pass|warn|fail",
    "secretHygiene": "pass|warn|fail",
    "constraintPreservation": "pass|warn|fail",
    "productionReadiness": "pass|warn|fail"
  },
  "aiPatchSafetyScore": {
    "localUnderstandability": 0,
    "stateExplicitness": 0,
    "controlFlowSimplicity": 0,
    "refactorSafety": 0,
    "tribalKnowledgeDependency": 0,
    "average": 0
  },
  "violations": { "high": 0, "medium": 0, "low": 0, "info": 0 },
  "recommendedAudits": ["skill names"],
  "findings": ["specific issues"],
  "blockers": ["merge-blocking items"]
}
```

**Merge decision rules:**

- **APPROVED** — all governance checks pass, AI Patch Safety Score ≥ 7, no HIGH violations
- **CONDITIONAL** — minor issues, can merge after addressing listed items
- **BLOCKED** — any HIGH violation, anti-entropy rule violation, score < 4, constraint removed, or leaked secret

## Output Constraints

- No vague "improve the code" advice.
- Every finding must reference a specific file, line, or configuration.
- Separate confirmed violations from assumptions from unknowns.
- If insufficient information to conclude, state: "Insufficient information to conclude".
- This is a governance review, not a logic review. Focus on structure, not behavior.
- Never recommend disabling or bypassing any lint rule or constraint.
- The human makes the final merge decision — this skill provides the evidence.

## Optional: Self-Correction (Manual)

After reviewing the output, you may paste the findings into a new prompt:

> "Here are the findings from my PR review. Which of these might be incorrect
> due to missing context? What additional data would increase confidence?"

IMPORTANT: This step must be human-initiated — never auto-dismiss findings.
The human decides what to act on.
