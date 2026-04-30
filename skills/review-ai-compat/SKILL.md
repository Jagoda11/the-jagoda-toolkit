---
name: review-ai-compat
description: "AI-agent compatibility audit. Use when evaluating whether code changes are safely readable, analyzable, and modifiable by AI agents. Checks determinism, explicitness, complexity, and boundary clarity."
---

# Review AI-Compat — AI-Agent Compatibility Audit

## Purpose

Evaluate whether code changes are safely readable, analyzable, and modifiable by AI agents.
This codebase treats AI as an architectural participant — not just a code generator.

All changes must optimize for:

- Deterministic behavior
- Explicit contracts
- Shallow reasoning depth
- Minimal hidden state
- Clear module boundaries
- Structural testability
- Predictable file organization
- Minimal cognitive complexity

## Instructions

### Step 0 — Scope Detection

Detect the repo's default branch:

```bash
BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$BASE" ] && BASE=$(git rev-parse --abbrev-ref HEAD)
```

Run: `git diff $BASE...HEAD --name-only`

Read the changed files. For each file, run the audit phases below.

Use `git` commands only — do NOT use `gh` CLI or GitHub API.

### Phase 1 — AI-Agent Compatibility Check

For each changed file, answer these questions:

| #   | Question                                                 | Answer |
| --- | -------------------------------------------------------- | ------ |
| 1   | Does this change introduce hidden state?                 | Yes/No |
| 2   | Does this increase function complexity or nesting depth? | Yes/No |
| 3   | Does this introduce implicit cross-layer dependencies?   | Yes/No |
| 4   | Would an AI agent understand this file in isolation?     | Yes/No |
| 5   | Are contracts explicit and typed?                        | Yes/No |
| 6   | Is side-effect behavior clearly separated?               | Yes/No |
| 7   | Are error paths explicit?                                | Yes/No |

If any answer is concerning, explain why and what to fix.

### Phase 2 — Structural Coding Rules Assessment

**Before assessing, gather evidence.** Run these checks on the changed files (or all `src/` files in baseline mode):

```bash
# Find `any` usage (should be zero)
grep -rn ": any\|as any\|<any>" <workspace>/src/ --include="*.ts" --include="*.tsx"

# Find swallowed errors (empty catch blocks)
grep -rn "catch.*{" <workspace>/src/ --include="*.ts" -A2 | grep -B1 "}"

# Find implicit return types on exported functions
grep -rn "^export.*function\|^export const.*=.*=>" <workspace>/src/ --include="*.ts" | grep -v ":"

# Find global mutable state (let/var at module level)
grep -rn "^let \|^var " <workspace>/src/ --include="*.ts" --include="*.tsx"

# Measure file lengths (flag files over 200 lines)
wc -l <workspace>/src/**/*.ts 2>/dev/null | sort -rn | head -20
```

Verify these rules are respected:

| Rule                    | Check                                                          |
| ----------------------- | -------------------------------------------------------------- |
| Pure-First Policy       | Are functions pure where possible? Side effects at edges only? |
| Shallow Modules         | No deep inheritance or decorator chains?                       |
| No Implicit Singletons  | All dependencies injected?                                     |
| Typed Boundaries        | No `any`? No implicit return types?                            |
| Explicit Error Surfaces | No swallowed errors? No silent fallback?                       |
| File Cohesion           | One responsibility per file?                                   |
| Predictable Layout      | Standard directory structure? No magic dynamic resolution?     |

Every rule violation must cite the exact grep output or file/line that triggered it.

### Phase 2a — Named Anti-Pattern Detection

Detect these labeled failure modes in the diff. Flag with the name, cite the line.

| Label                  | Detection                                                                                    |
| ---------------------- | -------------------------------------------------------------------------------------------- |
| `drive_by_refactoring` | Diff contains edits outside the scope of the reported fix/feature                            |
| `style_drift`          | Quote style, type annotations, or whitespace changed in the same diff as a functional change |
| `speculative_features` | New options, configs, abstractions not in the user ask                                       |
| `hidden_assumptions`   | Code commits to a scope/format/fields without asking (missing clarification turn)            |

Format each finding as: `[label] <file>:<line> — <specific issue>`

### Phase 3 — AI-Agent Readability Audit

Assess each changed file across these dimensions:

| Dimension             | What to evaluate                                                    |
| --------------------- | ------------------------------------------------------------------- |
| Determinism           | Given the same input, does the code always produce the same output? |
| Contract explicitness | Are all inputs, outputs, and side effects typed and documented?     |
| Hidden state          | Is there global, mutable, or closure-captured state?                |
| Call graph depth      | How many files must an agent read to understand this one?           |
| Mutation boundaries   | Is it clear where state changes happen?                             |
| Dependency injection  | Are external dependencies visible and injectable?                   |
| Error explicitness    | Are all error paths handled and surfaced?                           |
| Test determinism      | Can tests run in any order without shared state?                    |

**Measure call graph depth and import density for changed files:**

```bash
# Count imports per file (high count = high coupling)
for file in <changed-files>; do
  echo "$(grep -c "^import " "$file") imports — $file"
done | sort -rn

# Find files that import from 5+ different modules
grep -c "^import " <workspace>/src/**/*.ts 2>/dev/null | awk -F: '$2 >= 5 {print}'
```

Then identify:

- **Parts likely to cause incorrect automated refactors** — Why?
- **Parts likely to cause patch conflicts** — Why?
- **Parts that rely on implicit architectural knowledge** — What knowledge?

### Phase 4 — Structural Integrity Checks

These checks are MANDATORY. Do not skip any. Run each one and report the result.

**Detect dual-tooling layout first:**

```bash
DUAL_TOOLING=0
[ -d .agents/skills ] || [ -f AGENTS.md ] && DUAL_TOOLING=1
```

Phases 4a, 4b, 4c only run when `DUAL_TOOLING=1`. Otherwise skip them and note "single-tooling repo — dual-tooling checks skipped".

**4a — Duplicate detection (dual-tooling only):**
Search for files with similar names or identical content in different locations.
Run: `find .claude/skills .agents/skills -name "SKILL.md" -type f` and compare.
Are there orphaned, renamed, or duplicate files? List them.

**4b — Cross-reference validation (dual-tooling only):**
For every skill name referenced in any file (router tables, AGENTS.md, CLAUDE.md):

- Does the actual skill file exist in `.claude/skills/` AND `.agents/skills/`?
- List any referenced skills that do not exist.

**4c — Symmetry check (dual-tooling only):**
For each skill, compare `.claude/skills/<name>/SKILL.md` with `.agents/skills/<name>/SKILL.md`.

- Content must be identical except for `allowed-tools` (Claude Code only).
- Report any content differences beyond `allowed-tools`.

**4d — Naming consistency:**

- Does the directory name match the `name:` field in YAML front matter?
- If `AGENTS.md` exists, does it match the name in the `AGENTS.md` skills table?
- Are there any stale references to old names?

**4e — Implicit knowledge audit:**
List every piece of information an agent would need to work with these files
that is NOT written in the files themselves. Examples:

- Which branch is the base branch?
- Which directory is for which tool?
- Which names are canonical vs deprecated?

### Phase 5 — AI Patch Safety Score (MANDATORY)

The patch safety score is MANDATORY — without a numeric score, findings stay vague and there's no way to track whether changes are making the codebase more or less agent-friendly over time. Report all scores. Every dimension gets a number, even if it's a 10.

Score the change 1-10 for AI-modifiability. Do not skip any dimension:

| Dimension                   | Score (1-10) | Justification                                                 |
| --------------------------- | ------------ | ------------------------------------------------------------- |
| Local understandability     |              | Can an agent reason about this file without reading 5 others? |
| State explicitness          |              | Is all state visible and traceable?                           |
| Control flow simplicity     |              | Can the execution path be followed linearly?                  |
| Refactor safety             |              | What would break during automated refactor?                   |
| Tribal knowledge dependency |              | Does understanding require unwritten context?                 |

**Scoring action table:**

| Score | Action                                                      |
| ----- | ----------------------------------------------------------- |
| 9-10  | Report — safe for agents, no action needed                  |
| 7-8   | Report — acceptable, minor improvements optional            |
| 4-6   | Report — flag for review, improvements recommended          |
| 1-3   | Report — redesign required, not safe for agent modification |

Calculate an overall average score.

**Verdict rules:**

- **PASS** — average ≥ 7
- **FLAG** — average 4–6
- **REDESIGN** — average < 4

### Phase 6 — Improvements

If overall score is below 7, provide:

**Minimal Improvements** (low disruption):

- Specific changes to improve agent readability
- No architectural changes required

**Structural Improvements** (if score below 4):

- Architectural changes to restore agent compatibility
- File splits, dependency extraction, state isolation

## Anti-Entropy Rules

Flag violations of:

- No global mutable state
- No business logic in UI rendering
- No DB access outside the dedicated data-access layer
- No undocumented shared abstractions
- No dynamic runtime patching
- No circular dependencies

## Contract

Append this JSON block to every audit output — it is the verifiable contract:

```json
{
  "agent": "review-ai-compat",
  "branch": "<branch>",
  "date": "<today>",
  "verdict": "PASS|FLAG|REDESIGN",
  "dimensions": {
    "localUnderstandability": 0,
    "stateExplicitness": 0,
    "controlFlowSimplicity": 0,
    "refactorSafety": 0,
    "tribalKnowledgeDependency": 0
  },
  "averageScore": 0,
  "findings": ["specific issues"],
  "improvements": ["specific recommendations"]
}
```

## Output Constraints

- No vague "simplify the code" advice.
- Every finding must reference a specific file, function, or pattern.
- Separate facts from assumptions.
- If insufficient information to conclude, state: "Insufficient information to conclude".
- This audit measures AI compatibility — not general code quality.

## Optional: Self-Correction (Manual)

After reviewing the output, you may paste the findings into a new prompt:

> "Here are the findings from my AI-compat audit. Which of these might be incorrect
> due to missing context? What additional data would increase confidence?"

IMPORTANT: This step must be human-initiated — never auto-dismiss findings.
The human decides what to act on.
