#!/bin/bash
# PostToolUse hook on Edit|Write|MultiEdit
# Runs full verify (format → lint → typecheck → test) after every code-file edit.
# Blocks via JSON if any step fails so Claude must fix before continuing.

if ! command -v jq >/dev/null 2>&1; then
  echo "jc plugin: jq required for verify-on-write, install via brew/apt/dnf — see README" >&2
  exit 1
fi

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only run on source code files
case "$FILE_PATH" in
  *.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs|*.vue|*.svelte) ;;
  *) exit 0 ;;
esac

# Skip if no package.json at repo root
[ -f package.json ] || exit 0

# Detect package manager
if [ -f bun.lockb ]; then PM=bun
elif [ -f pnpm-lock.yaml ]; then PM=pnpm
elif [ -f yarn.lock ]; then PM=yarn
elif [ -f package-lock.json ]; then PM=npm
else PM=npm
fi

FAILED=""
OUTPUT=""

run_step() {
  local script="$1"
  if ! grep -q "\"$script\"" package.json; then
    return 0
  fi
  local out
  if ! out=$("$PM" run "$script" 2>&1); then
    FAILED="$script"
    OUTPUT="$out"
    return 1
  fi
  return 0
}

run_step format && \
run_step lint && \
run_step typecheck && \
run_step test

if [ -n "$FAILED" ]; then
  jq -n --arg step "$FAILED" --arg out "$OUTPUT" '{
    decision: "block",
    reason: ("verify failed at step: " + $step + "\n\n" + $out + "\n\nFix and re-run.")
  }'
fi

exit 0
