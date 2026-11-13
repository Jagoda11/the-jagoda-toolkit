# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.3] - 2026-11-13

### Added (0.2.3)

- Optional content-safety behavior checks with isolated HTML/CSS/SVG text fixtures, local mock tools and regression tests.

## [0.2.2] - 2026-11-12

### Added (0.2.2)

- Approval checkpoint for file-tool changes to Codex configuration.

## [0.2.1] - 2026-11-12

### Added (0.2.1)

- `escape-unicode-tags.py` PostToolUse hook on `Read`: replaces hidden Unicode Tag characters (U+E0000–U+E007F) in the text Claude receives with visible escapes via `updatedToolOutput`, and notes them as untrusted. Recognized emoji tag sequences (England, Scotland, Wales flags) are kept; source files are not modified.
- `tests/test_unicode_tag_guard.py` (7 tests), including recognized flags and a fake flag wrapping hidden instructions.

## [0.2.0] - 2026-11-11

### Added (0.2.0)

- `content-safety-context.py` hook: injects `rules/untrusted-content.md` (prompt-injection and untrusted-content rules) at `SessionStart` and on every `UserPromptSubmit`. Guidance only — it does not block actions.
- `tests/test_content_safety.py`: rule is injected, hostile prompts cannot replace it, missing or empty rule fails cleanly without echoing the prompt, hook is registered with a plugin-relative path. Run with `python3 -m unittest discover -s tests`.

## [0.1.16] - 2026-11-11

### Fixed (0.1.16)

- `block-git-commit-protected` hook never ran: its PreToolUse `matcher` used permission-rule syntax (`Bash(git commit*)`), which hooks treat as a tool-name regex that never matches. Now `matcher: "Bash"` with `if: "Bash(git commit*)"`.
- `block-git-commit-protected` now also blocks commits on `develop`, as its header comment already stated.

## [0.1.15] - 2026-07-03

### Added (0.1.15)

- Recommend `typescript-lsp@claude-plugins-official` under Companion Tools in README.
- `## Optional statusline` section in README documenting how users can wire a statusline in their own `~/.claude/settings.json`.

### Changed (0.1.15)

- `start` and `verify` skill descriptions extended with "Use when…" trigger clauses so Claude can auto-invoke alongside user invocation.
- Replace angle brackets with square brackets in `protocol` skill and `test-writer` / `ui-verifier` agent descriptions to avoid a known validator silent-reject bug (anthropics/claude-code#63081).
- Update keywords in `marketplace.json` and `plugin.json` (#11).
- Pre submission fixes across `marketplace.json`, `plugin.json`, `README.md`, and hook scripts (#10).

### Fixed (0.1.15)

- Description double space in `plugin.json` (#11).

### Removed (0.1.15)

- `SessionStart` sync-skills hook and `hooks/sync-skills.sh` script — plugin no longer symlinks skills into `~/.claude/skills/` (#12).
- `statusline-command.sh` — plugins can't ship a main-thread statusline; users add one in their own settings (see README).

## [0.1.14] - 2026-05-25

### Added (0.1.14)

- `PRIVACY.md` at repo root.
- README introductory note for new users.

### Changed (0.1.14)

- `jq` and CodeGraph documented as mandatory prerequisites.
- README clarifies companion tools and their requirements (#9).
- Skill and command syntax normalized in README for consistency.

### Fixed (0.1.14)

- Capitalization in Privacy Policy header.

## [0.1.13] - 2026-05-25

### Changed (0.1.13)

- Documentation and metadata updates only.

## [Pre-tagged]

### Added (Pre-tagged)

- Initial `the-jagoda-toolkit` plugin scaffolding.
- `start` and `start-ui` skills.
- `prompt` skill for structured task handoff.
- `review-design` skill (#2).
- `review-cicd` skill (#3).
- `review-auth` skill (#4).
- `test-writer` and `ui-verifier` agents (#5).
- `review` skill for detecting branch changes and recommending audits (bumped version to 0.1.7).
- `review-ai-compat` skill for AI-agent compatibility auditing (introduced alongside `Task(Explore)` permission).
- `rtk-rewrite` hook script.
- Additional hooks and scripts for workflow management and security.
- `no-overwrite` hook to prevent overwriting existing files.
- `SessionStart` sync-skills hook (later removed in Unreleased).
- Credential-scanning script.

### Changed (Pre-tagged)

- Statusline command path in `settings.json`.
- Permissions in `settings.json` extended with additional read, glob, and grep rules for sensitive files.
- Version bumps to 0.1.1, 0.1.7, 0.1.13.
- `plugin.json`.

### Removed (Pre-tagged)

- Deprecated hooks.

### Security (Pre-tagged)

- Deny permissions tightened in `settings.json`.
