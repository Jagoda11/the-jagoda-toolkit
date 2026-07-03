# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Recommend `typescript-lsp@claude-plugins-official` under Companion Tools in README.

### Changed

- `start` and `verify` skill descriptions extended with "Use when…" trigger clauses so Claude can auto-invoke alongside user invocation.
- Update keywords in `marketplace.json` and `plugin.json` (#11).
- Pre submission fixes across `marketplace.json`, `plugin.json`, `README.md`, and hook scripts (#10).

### Fixed

- Description double space in `plugin.json` (#11).

### Removed

- `SessionStart` sync-skills hook and `hooks/sync-skills.sh` script — plugin no longer symlinks skills into `~/.claude/skills/` (#12).

## [0.1.14] - 2026-05-25

### Added

- `PRIVACY.md` at repo root.
- README introductory note for new users.

### Changed

- `jq` and CodeGraph documented as mandatory prerequisites.
- README clarifies companion tools and their requirements (#9).
- Skill and command syntax normalized in README for consistency.

### Fixed

- Capitalization in Privacy Policy header.

## [0.1.13] - 2026-05-25

### Changed

- Documentation and metadata updates only.

## [Pre-tagged]

### Added

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

### Changed

- Statusline command path in `settings.json`.
- Permissions in `settings.json` extended with additional read, glob, and grep rules for sensitive files.
- Version bumps to 0.1.1, 0.1.7, 0.1.13.
- `plugin.json`.

### Removed

- Deprecated hooks.

### Security

- Deny permissions tightened in `settings.json`.
