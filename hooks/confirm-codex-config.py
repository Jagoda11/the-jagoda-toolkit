#!/usr/bin/env python3
"""Request approval before file tools change Codex configuration."""

import json
import sys
from pathlib import Path

FILE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def is_config_name(path: Path) -> bool:
    parts = path.parts[-2:]
    if sys.platform in ("darwin", "win32"):
        parts = tuple(part.casefold() for part in parts)
    return parts == (".codex", "config.toml")


def resolve_path(path: Path) -> Path:
    try:
        return path.resolve(strict=True)
    except FileNotFoundError:
        return path.resolve()


def parse_paths(payload: dict) -> tuple[Path, Path]:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        raise ValueError("Missing tool input")
    field = "notebook_path" if payload["tool_name"] == "NotebookEdit" else "file_path"
    raw_path = tool_input.get(field)
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError("Missing file path")
    cwd = resolve_path(Path(payload.get("cwd") or Path.cwd()).expanduser())
    return Path(raw_path).expanduser(), cwd


def same_target(target: Path, config: Path) -> bool:
    if target == resolve_path(config):
        return True
    return target.exists() and config.exists() and target.samefile(config)


def matches_config(path: Path, cwd: Path) -> bool:
    target = resolve_path(path)
    if is_config_name(path) or is_config_name(target):
        return True
    # Also recognize physical targets when a project config is itself linked.
    return any(
        same_target(target, directory / ".codex" / "config.toml")
        for directory in (cwd, *cwd.parents)
    )


def needs_approval(payload: object) -> bool:
    if not isinstance(payload, dict):
        return True
    if payload.get("tool_name") not in FILE_TOOLS:
        return False
    path, cwd = parse_paths(payload)
    if not path.is_absolute():
        path = cwd / path
    return matches_config(path, cwd)


def main() -> None:
    try:
        ask = needs_approval(json.load(sys.stdin))
    except (ValueError, TypeError, OSError, RuntimeError):
        # Invalid input or an unresolvable path must not silently skip approval.
        ask = True
    if ask:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": "Changing Codex configuration requires your approval.",
        }}))


if __name__ == "__main__":
    main()
