#!/bin/bash
# Block Claude from committing on master or develop.
# Triggered via PreToolUse with `if: "Bash(git commit*)"` filter,
# so this script only runs when a git commit is about to happen.

set -euo pipefail

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

if [[ "$BRANCH" == "master" || "$BRANCH" == "main" ]]; then
  jq -n --arg branch "$BRANCH" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: ("Direct commits to " + $branch + " forbidden. Switch to a feature branch.")
    }
  }'
fi

exit 0
