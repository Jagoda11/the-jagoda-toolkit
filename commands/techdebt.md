---
description: Review changed files for tech debt lint can't catch
---

Review files changed in this session for technical debt that lint cannot catch.

```bash
git diff --name-only
```

For each changed file, check:

1. **Duplicated logic** — same pattern repeated in 2+ places that should be a shared helper
2. **Dead code** — exported functions or constants with zero callers (use codegraph_callers to verify)
3. **Naming drift** — same concept called different names across files (e.g., `blockName` vs `targetBlock` for the same thing)
4. **Stale references** — comments, docs, or error messages that reference moved or renamed things

Do NOT report:

- Anything lint or typecheck would catch (file length, complexity, unused vars)
- Style preferences
- Speculative improvements

Report only confirmed findings. For dead code, show the proof (no callers). For duplication, show both locations. Keep it short — one line per finding.

If nothing found: "No techdebt found in changed files."
