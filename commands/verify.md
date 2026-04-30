---
description: Run lint, typecheck, test on affected workspaces only. Auto-detects package manager.
---

Run lint, typecheck, and test on affected workspaces. Detect what changed, verify only those.

Detect package manager:

```bash
if [ -f bun.lockb ]; then PM=bun
elif [ -f pnpm-lock.yaml ]; then PM=pnpm
elif [ -f yarn.lock ]; then PM=yarn
elif [ -f package-lock.json ]; then PM=npm
else PM=npm
fi
```

Detect changed files:

```bash
git diff --name-only HEAD~1 2>/dev/null || git diff --name-only
```

From the changed files, determine which workspaces are affected. Then run in order using `$PM`:

1. If `package.json` has a `format` script: `$PM format` — auto-fix formatting. Otherwise skip.
2. `$PM lint` — must pass with zero errors
3. `$PM typecheck` — must pass with zero errors
4. `$PM test` — all tests must pass

If any step fails, stop and report:

- Which step failed
- The relevant error output (not the full log)
- A suggested fix

If all pass, report: "All clear — format, lint, typecheck, test passed."

Keep output short. No explanations unless something fails.
