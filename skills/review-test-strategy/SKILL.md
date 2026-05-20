---
name: review-test-strategy
description: Systemic review of test strategy and coverage. Use when tests feel weak, flaky, slow, or unclear — or when test-related code has changed. Triggers on "test strategy", "test coverage", "are the tests good enough", "flaky tests", or "review the tests".
---

# Review Test Strategy — Test Architecture & Strategy Review

## Purpose

Evaluate the current test strategy for structural soundness and production readiness.
Use when tests feel weak, flaky, slow, or when test-related code has changed.
Produces a scored JSON contract with per-dimension verdicts.

## Scoring Model

Five dimensions, each scored 0–100. Each dimension gets its own verdict — no overall average.

| Dimension | Key | What it measures |
| --- | --- | --- |
| Coverage Breadth | `coverageBreadth` | Are all workspaces with test scripts actually tested? |
| Pyramid Shape | `pyramidShape` | Unit > Integration > E2E ratio |
| Isolation Quality | `isolationQuality` | No shared state, no env coupling, no test-to-test imports |
| CI Gating | `ciGating` | Tests enforced in CI, coverage thresholds configured |
| Flakiness Risk | `flakinessRisk` | Timer usage, async patterns, mock density |

### Deduction Guide

**coverageBreadth** (start at 100):
- Each workspace with test script but zero test files: −20
- Each test layer (unit/integration/e2e) with zero files: −10

**pyramidShape** (start at 100):
- Inverted pyramid (more integration than unit): −30
- No unit tests at all: −40
- No integration tests at all: −20
- Diamond shape (fat middle, thin top and bottom): −15

**isolationQuality** (start at 100):
- Each test file importing from another test file: −10
- Each `beforeAll`/`afterAll` with shared mutable state: −5
- Over-mocking (mock count > 3× test file count): −15
- Environment-dependent tests (hardcoded paths, ports): −10

**ciGating** (start at 100):
- Tests not gated in CI workflow: −40
- No coverage threshold configured: −20
- No coverage provider configured: −10
- Tests run but failures don't block merge: −30

**flakinessRisk** (start at 100):
- Each test file with `setTimeout`/`setInterval`/`sleep`: −10
- Each uncontrolled `waitFor` without timeout: −5
- Tests depending on execution order: −15
- Shared global state across test suites: −10

Floor at 0 — no negative scores.

### Per-Dimension Verdicts
- ✅ score > 80
- ⚠️ score 60–80
- ❌ score < 60

## Expert Panel

You are a cross-functional architecture board composed of:

- **Node.js Backend Architect** — Service testability, middleware testing, async patterns
- **React Frontend Architect** — Component testing, hook testing, integration boundaries
- **TypeScript Type-Safety Expert** — Type-level tests, contract validation, schema testing
- **Database Architect** — DB test isolation, transaction safety, test data lifecycle
- **Testing Strategy Expert** — Pyramid shape, coverage gaps, test design patterns
- **CI/CD Pipeline Engineer** — Test gating, parallelism, flakiness detection
- **Monorepo Architecture Specialist** — Cross-package test isolation, shared fixtures

Each expert must speak separately. No repetition between experts.

## Instructions

### Step 0 — Scope Detection

Detect the base branch (auto: `develop` for GitFlow, `main`/`master` for trunk-based, `release` if used as integration branch):

```bash
BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$BASE" ] && for b in develop main master release; do
  git show-ref --verify --quiet "refs/heads/$b" && BASE="$b" && break
done
[ -z "$BASE" ] && BASE=$(git rev-parse --abbrev-ref HEAD)
git diff "$BASE"...HEAD --name-only
```

Focus on changes in:
- `tests/` directories across all workspaces
- `vitest.config.ts` files
- Test utilities and fixtures
- Coverage configuration
- CI test gating (`.github/workflows/`)

If no test-related files changed, run a baseline audit of the current test landscape
(inventory test files, configs, and CI).

Also read testing rules from `AGENTS.md` and `CLAUDE.md` for context, if present.

Do NOT use `gh` CLI or GitHub API — use `git`, `find`, and standard shell commands only.

### Phase 1 — Coverage Mapping

**Step 1a — Inventory all test files by workspace:**

```bash
for dir in apps/*/ services/*/ packages/*/ libs/*/; do
  [ -d "$dir" ] || continue
  count=$(find "$dir" \( -name "*.test.ts" -o -name "*.test.tsx" -o -name "*.spec.ts" -o -name "*.spec.tsx" \) -not -path "*/node_modules/*" 2>/dev/null | wc -l)
  echo "$count tests — $dir"
done | sort -rn
```

**Step 1b — Inventory test files by type (unit vs integration):**

```bash
echo "Unit:           $(find . \( -path '*/tests/unit/*' -o -path '*/test/unit/*' -o -path '*/__tests__/unit/*' \) \( -name '*.test.ts' -o -name '*.test.tsx' -o -name '*.spec.ts' -o -name '*.spec.tsx' \) -not -path '*/node_modules/*' 2>/dev/null | wc -l)"
echo "Integration:    $(find . \( -path '*/tests/integration/*' -o -path '*/test/integration/*' -o -path '*/__tests__/integration/*' \) \( -name '*.test.ts' -o -name '*.test.tsx' -o -name '*.spec.ts' -o -name '*.spec.tsx' \) -not -path '*/node_modules/*' 2>/dev/null | wc -l)"
echo "Co-located/Other: $(find . \( -name '*.test.ts' -o -name '*.test.tsx' -o -name '*.spec.ts' -o -name '*.spec.tsx' \) -not -path '*/tests/unit/*' -not -path '*/tests/integration/*' -not -path '*/tests/e2e/*' -not -path '*/__tests__/*' -not -path '*/node_modules/*' 2>/dev/null | wc -l)"
```

**Step 1c — Find all vitest configs and check coverage settings:**

```bash
find . \( -name "vitest.config.*" -o -name "vitest.workspace.*" -o -name "playwright.config.*" \) -not -path "*/node_modules/*"
```

Read each config. Check for `coverage` settings, `globals: true`, and test file patterns.

**Step 1d — Check CI test gating:**

```bash
for f in .github/workflows/*.yml .github/workflows/*.yaml .gitlab-ci.yml .circleci/config.yml .azure-pipelines.yml cloudbuild.yaml buildspec.yml; do
  [ -f "$f" ] || continue
  echo "=== $f ==="
  grep -nA20 -iE "test|coverage" "$f" 2>/dev/null
done
```

Analyze each test layer using the inventory above:

| Layer | What to check |
| --- | --- |
| Unit tests | Business logic, mappers, utilities, schema validation |
| Integration tests | API routes, middleware chains, service interactions |
| DB tests | Query builders, data access layer, transaction behavior |
| E2E tests | Full request/response flows |
| Type-level tests | Contract compliance, Zod schema inference, typed route contract types |

For each layer:
- What is covered?
- What is implicitly trusted but not tested?
- What is untested but critical?

Mark assumptions explicitly.

### Phase 2 — Risk Identification

**Before identifying risks, gather evidence.** Run these checks:

```bash
# Count mock usage across all workspaces (high mock count may signal over-mocking)
find . \( -name "*.test.ts" -o -name "*.test.tsx" -o -name "*.spec.ts" -o -name "*.spec.tsx" \) -not -path "*/node_modules/*" -exec grep -l "vi\.mock\|vi\.fn\|vi\.spyOn" {} \; 2>/dev/null | wc -l

# Count total test files for ratio comparison
find . \( -name "*.test.ts" -o -name "*.test.tsx" -o -name "*.spec.ts" -o -name "*.spec.tsx" \) -not -path "*/node_modules/*" 2>/dev/null | wc -l

# Find shared state across test files (beforeAll, global setup)
find . \( -name "*.test.ts" -o -name "*.test.tsx" -o -name "*.spec.ts" -o -name "*.spec.tsx" \) -not -path "*/node_modules/*" -exec grep -ln "beforeAll\|afterAll\|globalSetup\|globalTeardown" {} \; 2>/dev/null

# Find tests with timers or delays (flakiness risk)
find . \( -name "*.test.ts" -o -name "*.test.tsx" -o -name "*.spec.ts" -o -name "*.spec.tsx" \) -not -path "*/node_modules/*" -exec grep -ln "setTimeout\|setInterval\|waitFor\|sleep\|vi\.advanceTimersByTime" {} \; 2>/dev/null

# Find test files that import from other test files (coupling)
find . \( -name "*.test.ts" -o -name "*.test.tsx" -o -name "*.spec.ts" -o -name "*.spec.tsx" \) -not -path "*/node_modules/*" -exec grep -ln "from '.*test\|from '.*spec\|from '.*fixture" {} \; 2>/dev/null

# Find workspaces with test script but no test files
for dir in apps/*/ services/*/ packages/*/ libs/*/; do
  [ -d "$dir" ] || continue
  if [ -f "$dir/package.json" ] && grep -q '"test"' "$dir/package.json" 2>/dev/null; then
    count=$(find "$dir" \( -name "*.test.ts" -o -name "*.test.tsx" -o -name "*.spec.ts" -o -name "*.spec.tsx" \) -not -path "*/node_modules/*" 2>/dev/null | wc -l)
    [ "$count" -eq 0 ] && echo "⚠️ $dir has test script but 0 test files"
  fi
done
```

Each expert must detect (in separate sections):

- **Over-mocking** — Are mocks hiding real integration failures?
- **Brittle tests** — Tests that break on refactor but not on bugs
- **Race conditions** — Async timing issues, uncontrolled promises
- **Transaction isolation** — DB tests leaking state between runs
- **Flaky async behavior** — Tests that pass/fail intermittently
- **Shared test state** — Global state pollution across test files
- **Environmental coupling** — Tests that depend on specific environment

Rules:
- No generic advice — reference specific test files or patterns.
- If an expert has no findings, state: "No issues detected in my domain."
- Mark assumptions as **"Assumption"**.
- Every finding must cite output from the commands above or from reading specific files.

### Phase 3 — Pyramid Evaluation

**Build the pyramid from data, not intuition:**

```bash
# Count by test type across the whole repo
echo "Unit:        $(find . -path '*/tests/unit/*.test.ts' -not -path '*/node_modules/*' 2>/dev/null | wc -l)"
echo "Integration: $(find . -path '*/tests/integration/*.test.ts' -not -path '*/node_modules/*' 2>/dev/null | wc -l)"
echo "E2E:         $(find . -path '*/tests/e2e/*.test.ts' -not -path '*/node_modules/*' -o -path '*/tests/e2e/*.spec.ts' -not -path '*/node_modules/*' 2>/dev/null | wc -l)"
echo "Other:       $(find . -path '*/tests/*.test.ts' -not -path '*/unit/*' -not -path '*/integration/*' -not -path '*/e2e/*' -not -path '*/node_modules/*' 2>/dev/null | wc -l)"
```

Using those counts, assess:

- Is it actually a pyramid? Or inverted?
- Where is redundancy wasteful?
- Where is risk under-tested?
- What is the unit-to-integration-to-E2E ratio?

Produce a visual assessment:

```
Ideal:          Actual:
  /\              ??
 /  \            ????
/____\          ??????
Unit base      [ assess using counts above ]
```

### Phase 4 — Proposed Strategy

Provide:

**Test Structure Improvements:**
- Ideal pyramid distribution for this project
- Test isolation strategy per workspace
- DB test data lifecycle strategy
- Deterministic test design improvements

**CI Improvements:**
- Test gating recommendations
- Parallelism opportunities
- Anti-flakiness strategy

**Migration Plan:**
- Incremental steps — not a rewrite
- Priority order based on risk reduction
- Performance test insertion points

### Phase 5 — Score Calculation and Contract Output

After completing all phases, calculate scores using the deduction guide from the Scoring Model.

**Step 5a — Tally deductions per dimension:**

| Dimension | Starting | Deductions | Final Score | Verdict |
| --- | --- | --- | --- | --- |
| coverageBreadth | 100 | _list each_ | _score_ | ✅/⚠️/❌ |
| pyramidShape | 100 | _list each_ | _score_ | ✅/⚠️/❌ |
| isolationQuality | 100 | _list each_ | _score_ | ✅/⚠️/❌ |
| ciGating | 100 | _list each_ | _score_ | ✅/⚠️/❌ |
| flakinessRisk | 100 | _list each_ | _score_ | ✅/⚠️/❌ |

**Step 5b — For any dimension scoring below 80, provide:**

**Minimal Safe Fix** (short term, low disruption):
- Specific test files to add or fix
- Coverage thresholds to configure
- CI gating adjustments

**Structural Redesign** (if 2+ dimensions scored ❌):
- Test directory restructuring
- Shared fixture extraction
- DB test isolation strategy

Prioritize by: **Score impact × Blast radius × Fix effort**

## Contract

Append this JSON block to every audit output — it is the verifiable contract:

```json
{
  "agent": "review-test-strategy",
  "branch": "<branch>",
  "date": "<today>",
  "verdictThresholds": { "✅": ">80", "⚠️": "60–80", "❌": "<60" },
  "scores": {
    "coverageBreadth": { "score": 0, "verdict": "✅|⚠️|❌" },
    "pyramidShape": { "score": 0, "verdict": "✅|⚠️|❌" },
    "isolationQuality": { "score": 0, "verdict": "✅|⚠️|❌" },
    "ciGating": { "score": 0, "verdict": "✅|⚠️|❌" },
    "flakinessRisk": { "score": 0, "verdict": "✅|⚠️|❌" }
  },
  "deductions": [
    { "dimension": "<key>", "points": 0, "reason": "specific finding" }
  ],
  "violations": { "high": 0, "medium": 0, "low": 0 },
  "findings": ["specific test strategy issues"],
  "improvements": ["specific recommendations"]
}
```

The JSON contract block is mandatory — never omit it.

## Output Constraints

- No generic "add more tests" advice.
- Every recommendation must reference specific code, files, or patterns.
- Separate confirmed weaknesses from assumptions from unknowns.
- If insufficient information to conclude something, state: "Insufficient information to conclude".
- Prioritize by: **Risk reduction x Effort**

## Optional: Self-Correction (Manual)

After reviewing the output, you may paste the findings into a new prompt:

> "Here are the findings from my test strategy audit. Which of these might be incorrect
> due to missing context? What additional data would increase confidence?"

IMPORTANT: This step must be human-initiated — never auto-dismiss findings.
The human decides what to act on.
