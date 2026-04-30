#!/bin/bash
# Warn when a file write contains secrets, passwords, tokens, or hardcoded credentials.
# Runs as PostToolUse hook on Edit|Write — scans the written file immediately.

if ! command -v jq >/dev/null 2>&1; then
  exit 0
fi

INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
  exit 0
fi

CONTENT=$(cat "$FILE")
VIOLATIONS=""

# Passwords and secrets (skip env refs, schemas, types, interfaces)
if echo "$CONTENT" | grep -inE '(password|passwd|pwd)\s*[:=]\s*["\x27]' | grep -v 'process\.env\|example\|mock\|fake\|schema\|interface\|type \|z\.\|zod' | head -1 | grep -q .; then
  VIOLATIONS="${VIOLATIONS}\n- Hardcoded password"
fi

# API keys and tokens
if echo "$CONTENT" | grep -inE '(api[_-]?key|api[_-]?secret|auth[_-]?token|access[_-]?token|bearer)\s*[:=]\s*["\x27]' | grep -v 'process\.env\|example\|mock\|fake\|schema\|interface\|type ' | head -1 | grep -q .; then
  VIOLATIONS="${VIOLATIONS}\n- API key or token"
fi

# Private keys
if echo "$CONTENT" | grep -qE 'BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY'; then
  VIOLATIONS="${VIOLATIONS}\n- Private key"
fi

# AWS credentials (IAM, STS temp, groups, IAM-alt)
if echo "$CONTENT" | grep -qE '(AKIA|ASIA|AGPA|AIDA)[0-9A-Z]{16}'; then
  VIOLATIONS="${VIOLATIONS}\n- AWS access key"
fi

# Connection strings with embedded credentials
if echo "$CONTENT" | grep -inE '(connect|connection)[_-]?string.*[:=].*[:@]' | grep -v 'process\.env\|example\|mock\|\.env' | head -1 | grep -q .; then
  VIOLATIONS="${VIOLATIONS}\n- Connection string with credentials"
fi

# Oracle TNS connection strings (real DB hosts leaking into code)
if echo "$CONTENT" | grep -inE '\(DESCRIPTION\s*=\s*\(ADDRESS' | grep -v 'process\.env\|example\|mock\|\.env' | head -1 | grep -q .; then
  VIOLATIONS="${VIOLATIONS}\n- Oracle TNS connection string"
fi

# OIDC / OAuth secrets
if echo "$CONTENT" | grep -inE '(client[_-]?secret|oidc[_-]?secret|session[_-]?secret)\s*[:=]\s*["\x27]' | grep -v 'process\.env\|example\|mock\|fake\|schema\|interface\|type ' | head -1 | grep -q .; then
  VIOLATIONS="${VIOLATIONS}\n- OIDC/session secret"
fi

# Anthropic / OpenAI keys
if echo "$CONTENT" | grep -qE 'sk-(ant|proj)-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{32,}'; then
  VIOLATIONS="${VIOLATIONS}\n- Anthropic/OpenAI API key"
fi

# JWT in source
if echo "$CONTENT" | grep -qE 'eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.'; then
  VIOLATIONS="${VIOLATIONS}\n- JWT token"
fi

if [ -n "$VIOLATIONS" ]; then
  echo -e "⚠️ Possible secrets in $FILE:${VIOLATIONS}" >&2
  echo "Use environment variables instead of hardcoded values." >&2
fi

exit 0
