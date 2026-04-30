#!/bin/bash
# SessionStart hook: sync plugin skills to ~/.claude/skills/ as symlinks
# so they appear in the / autocomplete menu (workaround for Claude Code bug)

PLUGIN_SKILLS="${CLAUDE_PLUGIN_ROOT}/skills"

if [ ! -d "$PLUGIN_SKILLS" ]; then
  exit 0
fi

mkdir -p "$HOME/.claude/skills"

for skill in "$PLUGIN_SKILLS"/*/; do
  name=$(basename "$skill")
  target="$HOME/.claude/skills/$name"

  # Skip if a real directory (not symlink) already exists — don't overwrite user's own skills
  if [ -d "$target" ] && [ ! -L "$target" ]; then
    continue
  fi

  # Create or update symlink
  ln -sfn "$skill" "$target"
done

exit 0
