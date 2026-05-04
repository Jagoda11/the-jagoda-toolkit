#!/bin/bash
# Build internal dependency graph from monorepo workspaces.
# Output: <package> → <internal-deps>
# Used by skills/review-monorepo/SKILL.md via !`<cmd>` injection.

if ! command -v jq >/dev/null 2>&1; then
  echo "(jq not installed — cannot build dependency graph)"
  exit 0
fi

SCOPE=$(grep -h '"name":' packages/*/package.json apps/*/package.json services/*/package.json 2>/dev/null \
  | head -1 | sed -n 's/.*"\(@[^/]*\)\/.*/\1/p')

if [ -z "$SCOPE" ]; then
  echo "(no scoped packages found — not a monorepo or unrecognized layout)"
  exit 0
fi

for pkg in apps/*/package.json services/*/package.json packages/*/package.json; do
  [ -f "$pkg" ] || continue
  name=$(jq -r '.name' "$pkg")
  deps=$(jq -r --arg scope "$SCOPE" \
    '(.dependencies // {}) + (.devDependencies // {}) | to_entries[] | select(.key | startswith($scope)) | .key' \
    "$pkg" 2>/dev/null | tr '\n' ',' | sed 's/,$//')
  echo "$name → ${deps:-(no internal deps)}"
done | sort
