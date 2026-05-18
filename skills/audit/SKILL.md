---
name: audit
description: Deep architecture audit for any feature or change. Runs failure mode analysis, boundary audit, test gap mapping, contract compliance, data flow tracing, and risk prioritization. Use for major features, critical refactors, or when things feel architecturally wrong.
allowed-tools: Bash(*), Read, Glob, Grep, Task(Explore), mcp__codegraph__codegraph_search, mcp__codegraph__codegraph_callers, mcp__codegraph__codegraph_callees, mcp__codegraph__codegraph_context, mcp__codegraph__codegraph_node, mcp__codegraph__codegraph_impact
---

# Audit — Deep Architecture Audit

## Purpose

Comprehensive architecture audit for major features, critical refactors, or suspicious changes.
This is the deep-dive skill — slower and more thorough than `/review-pr`.

Use when:

- A new feature spans backend + contracts + frontend
- A refactor changes multiple service boundaries
- Something feels architecturally wrong but you can't pinpoint it
- A periodic health check is needed on a specific area
- Changes touch the data flow (DB → service → contract → frontend)

This audit covers governance phases 1, 2, 3, and 5 from `docs/AI_GOVERNANCE.md`,
plus codebase-specific phases. Phase 4 (AI-Agent Readability Audit) is covered by
`/review-ai-compat`, not this skill.

1. Failure Mode Analysis ← governance phase 1
2. Boundary Audit ← governance phase 2
3. Test Gap Mapping ← governance phase 3
4. Contract Compliance & Data Flow ← codebase-specific
5. Adversarial Review ← governance phase 5
6. AI Patch Safety Score ← codebase-specific
7. Consolidated Audit Report
8. Prioritized Action Plan

## Expert Panel

You are a review board composed of:

- **Failure Mode Analyst** — What can go wrong? What are the blast radii?
- **Boundary Architect** — Domain ownership, dependency direction, contract chain
- **Test Strategy Auditor** — Coverage gaps, missing edge cases, test isolation
- **Data Flow Analyst** — Request → route → service → dbhandler → DB → mapper → response
- **Contract Compliance Specialist** — schema validators (Zod, Pydantic, JSON Schema, etc.), typed route/API contracts, type chain integrity
- **Adversarial Reviewer** — Assumes the optimistic analysis is wrong. Challenges every "it's fine"

Each expert must speak separately. No repetition between experts.

## Instructions

### Step 0 — Scope Detection

Detect the base branch (auto: `main`/`master` for trunk-based, `develop` for GitFlow, `release` if used as integration branch):

```bash
BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$BASE" ] && for b in main master develop release; do
  git show-ref --verify --quiet "refs/heads/$b" && BASE="$b" && break
done
[ -z "$BASE" ] && BASE=$(git rev-parse --abbrev-ref HEAD)
echo "base=$BASE"
```

All subsequent steps reference `$BASE`.

Use `git` commands only — do NOT use `gh` CLI or GitHub API.

**Step 0a — Map the change surface:**

```bash
# All changed files
git diff $BASE...HEAD --name-only

# Change magnitude
git diff $BASE...HEAD --stat | tail -1
git log $BASE..HEAD --oneline
```

**Step 0b — Identify affected domains:**

```bash
# Top-level workspace/dir affected (generic monorepo detection)
git diff $BASE...HEAD --name-only | awk -F/ '{print $1"/"$2}' | sort -u

# Files per common monorepo root
for root in services packages apps libs crates modules cmd pkg internal; do
  count=$(git diff $BASE...HEAD --name-only | grep -c "^$root/" 2>/dev/null)
  [ "$count" -gt 0 ] && echo "$root: $count files changed"
done

# Frontend-ish dirs touched
git diff $BASE...HEAD --name-only | grep -E '^(apps/|web/|frontend/|client/|ui/)' | head -10

# Backend-ish dirs touched
git diff $BASE...HEAD --name-only | grep -E '^(services/|api/|backend/|server/)' | head -10

# Domain markers — non-trivial all-caps IDs in paths (project-specific, may be empty)
git diff $BASE...HEAD --name-only | tr '/._-' '\n' | grep -xE '[A-Z]{2,8}[0-9]{2,5}' | sort -u
```

**Step 0c — Read all changed files in full:**

```bash
git diff $BASE...HEAD
```

Read every changed file completely. Also read the surrounding context — the files they
import from and export to. Shallow reading produces shallow audits.

### Phase 1 — Failure Mode Analysis

For each changed component (service, package, route, handler), identify failure modes.

**Step 1a — Gather error handling evidence:**

```bash
# Error handling patterns across changed files (multi-language)
for file in $(git diff $BASE...HEAD --name-only | grep -E '\.(ts|tsx|js|jsx|py|go|rs|rb|java|cs|kt)$'); do
  [ -f "$file" ] && echo "=== $file ===" && grep -nE "throw|catch|raise|except|panic|recover|Result<|Error\(" "$file"
done

# HTTP status / response codes in changed files
for file in $(git diff $BASE...HEAD --name-only | grep -E '\.(ts|tsx|js|jsx|py|go|rs|rb|java|cs|kt)$'); do
  [ -f "$file" ] && grep -nE "StatusCodes\.|status\(|HTTP_|StatusBadRequest|StatusOK" "$file"
done

# Async/concurrency patterns
for file in $(git diff $BASE...HEAD --name-only | grep -E '\.(ts|tsx|js|jsx|py|go|rs|rb|java|cs|kt)$'); do
  [ -f "$file" ] && grep -nE "async |await |\.then|\.catch|Promise|go func|spawn|tokio::|asyncio" "$file"
done
```

**Step 1b — For each component, produce a failure mode table:**

| Component | Failure Mode | Trigger          | Impact        | Current Handling   | Adequate? |
| --------- | ------------ | ---------------- | ------------- | ------------------ | --------- |
| _name_    | _what fails_ | _how it happens_ | _what breaks_ | _how it's handled_ | Yes/No    |

Categories to check:

- **Input validation failures** — malformed requests, missing fields, type mismatches
- **DB failures** — connection loss, query timeout, constraint violation, deadlock
- **Auth failures** — expired token, missing session, insufficient permissions
- **Contract violations** — response doesn't match schema, missing fields
- **Concurrency issues** — race conditions, stale reads, double writes
- **Resource exhaustion** — memory, connection pool, file handles
- **External service failures** — downstream timeouts, network issues

### Phase 2 — Boundary Audit

**Step 2a — Verify the dependency chain for affected code:**

```bash
# Map imports/uses for each changed file (multi-language)
for file in $(git diff $BASE...HEAD --name-only | grep -E '\.(ts|tsx|js|jsx|py|go|rs|rb|java|cs|kt)$'); do
  [ -f "$file" ] && echo "=== $file ===" && grep -nE "^import |^from |^use |require\(" "$file"
done

# Cross-package imports (any npm scope, workspace path, or absolute module path)
for file in $(git diff $BASE...HEAD --name-only | grep -E '\.(ts|tsx|js|jsx|py|go|rs|rb)$'); do
  [ -f "$file" ] && grep -nE "from '@[^/]+/|from '(services|packages|apps|libs)/|from \"github\.com/" "$file" | sed "s|^|$file:|"
done

# Cross-workspace imports (file importing from a different top-level workspace)
for file in $(git diff $BASE...HEAD --name-only | grep -E '^[^/]+/[^/]+/.*\.(ts|tsx|js|jsx|py|go|rs)$'); do
  workspace=$(echo "$file" | cut -d/ -f1-2)
  [ -f "$file" ] && grep -nE "^import |^from |^use |require\(" "$file" | grep -v "$workspace"
done
```

**Step 2b — Verify the allowed dependency flow:**

Identify the project's intended dependency direction. Look for:

- `package.json` workspaces (npm/yarn/pnpm) or root `pnpm-workspace.yaml`
- `nx.json` / `project.json` (Nx workspace boundaries)
- `Cargo.toml` `[workspace]` (Rust)
- `go.work` (Go workspaces)
- Architecture docs (`docs/ARCHITECTURE.md`, `README.md`, ADRs)

Common pattern:

```
shared utilities    ← consumed by everyone
shared contracts    ← consumed by everyone
domain libs         ← consumed by services + apps
DB / data access    ← consumed by services only
    ↓
services/api        (consume libs, never each other)
    ↓
apps/* (web, cli)   (consume libs + contracts, never services directly)
```

For every import found in Step 2a, verify it follows the project's intended flow. Flag every violation with file, line, and the illegal import. If the flow isn't documented anywhere, flag that — "no documented dependency direction" is itself a finding.

**Step 2c — Domain ownership check:**

If the project mirrors a single domain entity across multiple layers (e.g., schema, route contract, service handler, UI module), verify every affected domain marker has a directory/file in each expected layer.

```bash
# Generic domain mirror discovery — adapt to project's layer roots
markers=$(git diff $BASE...HEAD --name-only | tr '/._-' '\n' | grep -xE '[A-Z]{2,8}[0-9]{2,5}' | sort -u)
for marker in $markers; do
  echo "=== $marker ==="
  find . -type d -iname "$marker" -not -path '*/node_modules/*' -not -path '*/.git/*' 2>/dev/null
done
```

If the project doesn't use this pattern, skip 2c.

### Phase 3 — Test Gap Mapping

**Step 3a — Inventory tests for affected code:**

```bash
# Test files per affected workspace (workspace = top-2 path segments)
for ws in $(git diff $BASE...HEAD --name-only | grep -E '^[^/]+/[^/]+/' | awk -F/ '{print $1"/"$2}' | sort -u); do
  echo "=== $ws ==="
  find "$ws" -type f \( \
      -name "*.test.*" -o -name "*.spec.*" \
      -o -name "*_test.go" -o -name "*_test.py" -o -name "test_*.py" \
      -o -name "*Test.kt" -o -name "*Test.java" -o -name "*Tests.cs" -o -name "*_spec.rb" \
    \) -not -path '*/node_modules/*' 2>/dev/null | sort
done
```

**Step 3b — Map source files to test files:**

```bash
# For every changed source file, find its test (multi-language)
for file in $(git diff $BASE...HEAD --name-only | grep -E '\.(ts|tsx|js|jsx|py|go|rs|rb|java|kt|cs)$' | grep -vE '\.(test|spec)\.|_test\.|/test_|\.tests?\.'); do
  [ -f "$file" ] || continue
  base=$(basename "$file" | sed -E 's/\.(ts|tsx|js|jsx|py|go|rs|rb|java|kt|cs)$//')
  workspace=$(echo "$file" | cut -d/ -f1-2)
  testfile=$(find "$workspace" -type f \( \
      -name "${base}.test.*" -o -name "${base}.spec.*" \
      -o -name "${base}_test.go" -o -name "${base}_test.py" -o -name "test_${base}.py" \
      -o -name "${base}Test.kt" -o -name "${base}Test.java" -o -name "${base}Tests.cs" -o -name "${base}_spec.rb" \
    \) -not -path '*/node_modules/*' 2>/dev/null | head -1)
  [ -n "$testfile" ] && echo "✅ $file → $testfile" || echo "❌ $file → NO TEST"
done
```

**Step 3c — Classify untested code by risk:**

For every untested file found in Step 3b, classify:

| File   | Type                                         | Risk Level | Why                            |
| ------ | -------------------------------------------- | ---------- | ------------------------------ |
| _path_ | route/handler/service/data-access/util/model | 🚨/⚠️/✅   | _what could go wrong untested_ |

Risk classification:

- 🚨 HIGH — data access (SQL/query correctness), auth/authz logic, payment or money-handling paths, security-critical code
- ⚠️ MEDIUM — service/business logic, route handlers (input validation), data mappers/transformers, integration glue
- ✅ LOW — utilities, constants, types, pure functions with trivial logic

**Step 3d — Check test quality indicators:**

```bash
# Mock density (over-mocking = false confidence)
for ws in $(git diff $BASE...HEAD --name-only | grep -E '^[^/]+/[^/]+/' | awk -F/ '{print $1"/"$2}' | sort -u); do
  echo "=== $ws ==="
  count=$(grep -rnE "vi\.(mock|fn|spyOn)|jest\.(mock|fn|spyOn)|sinon\.|mock\.patch|MagicMock|@patch|gomock|mock\.New|@Mock|mockito|allow\(|instance_double" "$ws" \
    --include="*.test.*" --include="*.spec.*" --include="*_test.go" --include="*_test.py" --include="test_*.py" --include="*Test.kt" --include="*Test.java" --include="*Tests.cs" --include="*_spec.rb" \
    --exclude-dir=node_modules 2>/dev/null | wc -l)
  echo "Mock count: $count"
done

# Assertion density (low assertions = weak tests)
for ws in $(git diff $BASE...HEAD --name-only | grep -E '^[^/]+/[^/]+/' | awk -F/ '{print $1"/"$2}' | sort -u); do
  echo "=== $ws ==="
  asserts=$(grep -rnE "expect\(|assert |assertEquals|assertThat|assert_equal|require\." "$ws" \
    --include="*.test.*" --include="*.spec.*" --include="*_test.go" --include="*_test.py" --include="test_*.py" --include="*Test.kt" --include="*Test.java" --include="*Tests.cs" --include="*_spec.rb" \
    --exclude-dir=node_modules 2>/dev/null | wc -l)
  echo "Assertions: $asserts"
done

# Shared state across tests (flakiness risk)
for ws in $(git diff $BASE...HEAD --name-only | grep -E '^[^/]+/[^/]+/' | awk -F/ '{print $1"/"$2}' | sort -u); do
  grep -rnE "beforeAll|afterAll|globalSetup|@BeforeAll|@AfterAll|setUp|tearDown|setup_module|TestMain" "$ws" \
    --include="*.test.*" --include="*.spec.*" --include="*_test.go" --include="*_test.py" --include="test_*.py" --include="*Test.kt" --include="*Test.java" --include="*Tests.cs" --include="*_spec.rb" \
    --exclude-dir=node_modules 2>/dev/null
done
```

### Phase 4 — Contract Compliance & Data Flow

Phase 4 enforces that data contracts hold across every layer they cross —
from the source-of-truth schema all the way to the UI that renders the data.

**Configure once per project.** Edit the path variables at the top of Step 4a
to match your repo layout. `*` wildcards are honored.

**Step 4a — Trace the full contract chain for affected markers:**

```bash
# === EDIT FOR YOUR PROJECT =========================================
SCHEMA_DIR="packages/contracts/src/schemas"
ROUTE_CONTRACT_DIR="packages/contracts/src/routes"
SERVICE_DIR="services/*/src"
DB_HANDLER_SUBPATH="dbhandlers"
APP_DIR="apps/*/src"
API_CLIENT_SUBPATH="api"
UI_COMPONENT_SUBPATH="components"
MARKER_REGEX='[A-Z]{2,8}[0-9]{2,5}'
# ===================================================================

markers=$(git diff $BASE...HEAD --name-only \
  | tr '/._-' '\n' | grep -xiE "$MARKER_REGEX" | sort -u)

for marker in $markers; do
  upper=$(echo "$marker" | tr '[:lower:]' '[:upper:]')
  lower=$(echo "$marker" | tr '[:upper:]' '[:lower:]')

  echo "=== Marker: $upper ==="

  echo "-- 1. Schema (source of truth) --"
  find . -path "*$SCHEMA_DIR/*$lower*" -name "*.ts" \
    -not -path '*/node_modules/*' 2>/dev/null

  echo "-- 2. Route contract --"
  find . -path "*$ROUTE_CONTRACT_DIR/*$lower*" -name "*.ts" \
    -not -path '*/node_modules/*' 2>/dev/null

  echo "-- 3. Service route handler --"
  find . -path "*$SERVICE_DIR/$upper/*" \( -name "*.route.ts" -o -name "*.routes.ts" \) \
    -not -path '*/node_modules/*' 2>/dev/null

  echo "-- 4. DB handler --"
  find . -path "*$SERVICE_DIR/$upper/$DB_HANDLER_SUBPATH/*" -name "*.ts" \
    -not -path '*/node_modules/*' 2>/dev/null

  echo "-- 5. API client (consumer side) --"
  find . -path "*$APP_DIR/$API_CLIENT_SUBPATH/*" \( -name "*.ts" -o -name "*.tsx" \) \
    -not -path '*/node_modules/*' 2>/dev/null \
    | xargs grep -l -iE "$marker" 2>/dev/null

  echo "-- 6. UI component (consumer side) --"
  find . -path "*$APP_DIR/$UI_COMPONENT_SUBPATH/*" -iname "*$marker*" \
    -not -path '*/node_modules/*' 2>/dev/null
done
```

Read every file found. Verify the chain holds end to end:

Schema type → route contract request/response → service handler input/output
→ DB query → row mapper → HTTP response → API client return type → UI prop type.

**Step 4b — Check for contract breaks at each layer root:**

```bash
for root in "$SCHEMA_DIR" "$ROUTE_CONTRACT_DIR" "$SERVICE_DIR" "$APP_DIR"; do
  echo "=== Diff in $root ==="
  git diff $BASE...HEAD -- "$root"
done

# Removed / changed schema fields
git diff $BASE...HEAD -- "$SCHEMA_DIR" | grep -E "^[-+].*z\." | head -30

# Service response shape changes
for file in $(git diff $BASE...HEAD --name-only | grep -E "${SERVICE_DIR//\*/.*}.*\.route\.ts$"); do
  [ -f "$file" ] && echo "=== $file ===" && grep -n "return\|body:" "$file"
done

# Consumer-side: API client return-type changes
for file in $(git diff $BASE...HEAD --name-only | grep -E "${APP_DIR//\*/.*}/$API_CLIENT_SUBPATH/.*\.tsx?$"); do
  [ -f "$file" ] && echo "=== $file ===" && grep -n "type \|interface \|return " "$file"
done
```

Flag any removed/changed field that downstream layers still reference —
backend **and** frontend.

**Step 4c — Data flow verification:**

For each new or changed route, trace the full chain end to end:

1. **Request** → which validator/schema runs?
2. **Route handler** → calls correct service function?
3. **Service** → orchestrates correctly? Pure logic vs side effects?
4. **DB handler** → query correctness? Parameters bound safely?
5. **Mapper** → DB row → contract type transform correct?
6. **HTTP response** → matches the declared schema?
7. **API client** → response type matches contract? Error handling?
8. **UI component** → prop types match API client return? Loading/error states?

Flag any break in the chain — backend **and** consumer side.

### Phase 5 — Adversarial Review

This phase assumes the optimistic analysis from Phases 1-4 is wrong.

**Step 5a — Challenge every "it's fine":**

For each finding rated as "Adequate" or "No issues" in Phases 1-4, ask:

- What assumption am I making?
- What input would violate that assumption?
- What edge case did I not consider?
- What happens under load?
- What happens during partial deployment (old + new versions coexisting)?

**Step 5b — Look for hidden assumptions:**

```bash
EXTS='\.(ts|tsx|js|jsx|py|go|rs|rb|java|cs|kt|swift)$'

# Hardcoded values that look like they should be configurable
for file in $(git diff $BASE...HEAD --name-only | grep -E "$EXTS"); do
  [ -f "$file" ] && grep -nE "= [0-9]+|= '[^']{10,}'|= \"[^\"]{10,}\"" "$file" | head -5 && echo "--- $file ---"
done

# Type assertions / unsafe casts (multi-language)
for file in $(git diff $BASE...HEAD --name-only | grep -E "$EXTS"); do
  [ -f "$file" ] && grep -nE "as [A-Z]|!|!!|\.\([A-Z][a-zA-Z]+\)|unwrap\(\)|expect\(" "$file" | grep -v "!==\|!=" | head -5 && echo "--- $file ---"
done

# Null/undefined silencers (optional chaining, default coalescing)
for file in $(git diff $BASE...HEAD --name-only | grep -E "$EXTS"); do
  [ -f "$file" ] && grep -nE "\?\.|\?\?|\.unwrap_or|\.getOrElse|\?:" "$file" | head -5 && echo "--- $file ---"
done
```

**Step 5c — Worst-case scenario analysis:**

For the most critical changed component, answer:

- What is the worst thing that can happen if this code has a bug?
- What data could be corrupted?
- What user-facing impact would occur?
- How would we detect it?
- How would we recover?

### Phase 6 — AI Patch Safety Score

Score the overall change 1-10 for AI-modifiability. Do not skip any dimension:

| Dimension                   | Score (1-10) | Justification                                                 |
| --------------------------- | ------------ | ------------------------------------------------------------- |
| Local understandability     |              | Can an agent reason about each file without reading 5 others? |
| State explicitness          |              | Is all state visible and traceable?                           |
| Control flow simplicity     |              | Can the execution path be followed linearly?                  |
| Refactor safety             |              | What would break during automated refactor?                   |
| Tribal knowledge dependency |              | Does understanding require unwritten context?                 |

**Scoring guide:**

- **7-10** — Safe for agents. No action needed.
- **4-6** — Flag for review. Improvements recommended.
- **1-3** — Redesign required. Not safe for agent modification.

Calculate an overall average score.

### Phase 7 — Consolidated Audit Report

**Violation Summary:**

| #   | Violation | Severity                               | Phase   | File   | Details        |
| --- | --------- | -------------------------------------- | ------- | ------ | -------------- |
| V1  | _type_    | 🔴 HIGH / 🟡 MEDIUM / 🔵 LOW / ℹ️ INFO | _phase_ | _path_ | _what and why_ |

**Architecture Health Assessment:**

| Dimension              | Status   | Notes |
| ---------------------- | -------- | ----- |
| Failure mode coverage  | ✅/⚠️/❌ |       |
| Boundary integrity     | ✅/⚠️/❌ |       |
| Test coverage          | ✅/⚠️/❌ |       |
| Contract compliance    | ✅/⚠️/❌ |       |
| Data flow integrity    | ✅/⚠️/❌ |       |
| Adversarial resilience | ✅/⚠️/❌ |       |
| AI Patch Safety Score  | _X/10_   |       |

### Phase 8 — Prioritized Action Plan

If any violations are found, provide two strategies:

**Minimal Safe Fix** (short term, low disruption):

- Specific changes ordered by risk reduction
- Each fix must reference the exact violation it addresses
- No architectural changes required

**Structural Redesign** (if architecture is systemically weak):

- Architectural changes to address root causes
- Contract chain repairs
- Test strategy additions
- Data flow corrections

Prioritize by: **Blast radius × Likelihood of failure × Recovery time**

Provide a concrete ordered list:

1. Fix X because Y (addresses V1, V3)
2. Add test for Z because W (addresses V5)
3. etc.

## Output Constraints

- No vague "improve the architecture" advice.
- Every finding must reference a specific file, function, line, or data flow step.
- Separate confirmed violations from assumptions from unknowns.
- If insufficient information to conclude, state: "Insufficient information to conclude".
- This audit measures architectural soundness — not style or formatting.
- The Adversarial Review (Phase 5) must explicitly challenge the findings from Phases 1-4.
- Never recommend disabling or bypassing constraints.

## Optional: Self-Correction (Manual)

After reviewing the output, you may paste the findings into a new prompt:

> "Here are the findings from my architecture audit. Which of these might be incorrect
> due to missing context? What additional data would increase confidence?"

IMPORTANT: This step must be human-initiated — never auto-dismiss findings.
The human decides what to act on.
