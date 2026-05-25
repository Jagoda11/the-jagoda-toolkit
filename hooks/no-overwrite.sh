#!/bin/bash
# PreToolUse hook for Write — blocks overwriting existing files
# Write creates new files. If the file exists, Claude should use Edit instead.

if ! command -v jq >/dev/null 2>&1; then
  echo "jc plugin: jq required for no-overwrite, install via brew/apt/dnf — see README" >&2
  exit 1
fi

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty')

# Only check Write, not Edit or MultiEdit
if [ "$TOOL" != "Write" ]; then
  exit 0
fi

FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

if [ -f "$FILE_PATH" ]; then
  echo "⚠️ File already exists: $FILE_PATH" >&2
  echo "Use Edit to modify existing files, not Write." >&2
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: "File already exists. Use Edit to modify existing files instead of Write which overwrites the entire file."
    }
  }'
  exit 0
fi

exit 0
