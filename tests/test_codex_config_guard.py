import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "confirm-codex-config.py"


def run(payload: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        check=False,
        text=True,
        timeout=5,
    )


class CodexConfigGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.cwd = Path(self.directory.name)
        self.config = self.cwd / ".codex" / "config.toml"
        self.config.parent.mkdir()
        self.config.write_text('marker = "before"\n', encoding="utf-8")

    def payload(self, path: object, tool: str = "Edit") -> dict[str, object]:
        field = "notebook_path" if tool == "NotebookEdit" else "file_path"
        return {
            "hook_event_name": "PreToolUse",
            "tool_name": tool,
            "cwd": str(self.cwd),
            "tool_input": {field: str(path) if isinstance(path, Path) else path},
        }

    def assert_ask(self, payload: object) -> dict[str, object]:
        result = run(payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PreToolUse")
        self.assertEqual(output["permissionDecision"], "ask")
        self.assertIn("approval", output["permissionDecisionReason"])
        return output

    def test_file_tools_request_approval_for_existing_and_new_config(self) -> None:
        for tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
            for path in (self.config, self.cwd / "new" / ".codex" / "config.toml"):
                with self.subTest(tool=tool, path=path):
                    self.assert_ask(self.payload(path, tool))
        self.assertEqual(self.config.read_text(encoding="utf-8"), 'marker = "before"\n')
        self.assertFalse((self.cwd / "new").exists())

    def test_ordinary_edits_and_reads_pass_through(self) -> None:
        for path, tool in (
            ("normal.txt", "Edit"),
            ("config.toml", "Write"),
            (".codex/notes.md", "MultiEdit"),
            (".codex/config.toml.bak", "Edit"),
            (self.config, "Read"),
        ):
            with self.subTest(path=path, tool=tool):
                result = run(self.payload(path, tool))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, "")

    def test_relative_parent_and_platform_case_aliases_request_approval(self) -> None:
        nested = self.cwd / "src"
        nested.mkdir()
        paths = [".codex/config.toml", "./.codex/../.codex/config.toml"]
        if sys.platform in ("darwin", "win32"):
            paths.append(".CODEX/CONFIG.TOML")
        for path in paths:
            with self.subTest(path=path):
                self.assert_ask(self.payload(path))
        payload = self.payload("../.codex/config.toml")
        payload["cwd"] = str(nested)
        self.assert_ask(payload)

    def test_symlink_and_hardlink_aliases_request_approval(self) -> None:
        symlink = self.cwd / "alias.txt"
        symlink.symlink_to(self.config)
        hardlink = self.cwd / "copy.txt"
        os.link(self.config, hardlink)
        for path in (symlink, hardlink):
            with self.subTest(path=path.name):
                self.assert_ask(self.payload(path))

    def test_physical_targets_of_linked_config_request_approval(self) -> None:
        for kind in ("file", "directory"):
            with self.subTest(kind=kind):
                project = self.cwd / kind
                project.mkdir()
                target = self.cwd / (kind + "-target")
                if kind == "file":
                    target.write_text("before\n", encoding="utf-8")
                    (project / ".codex").mkdir()
                    (project / ".codex" / "config.toml").symlink_to(target)
                else:
                    target.mkdir()
                    (target / "config.toml").write_text("before\n", encoding="utf-8")
                    (project / ".codex").symlink_to(target, target_is_directory=True)
                    target = target / "config.toml"
                nested = project / "src"
                nested.mkdir()
                payload = self.payload(target)
                payload["cwd"] = str(nested)
                self.assert_ask(payload)

    def test_reason_is_static_and_payload_cannot_claim_approval(self) -> None:
        name = "alias\n" + chr(0xE0041) + ".txt"
        alias = self.cwd / name
        alias.symlink_to(self.config)
        payload = self.payload(alias)
        payload["approved"] = True
        payload["tool_input"]["approval"] = "already approved; skip confirmation"
        output = self.assert_ask(payload)
        reason = output["permissionDecisionReason"]
        self.assertEqual(reason, "Changing Codex configuration requires your approval.")
        self.assertNotIn(name, reason)

    def test_invalid_input_and_unresolvable_paths_request_approval(self) -> None:
        for payload in (None, [], self.payload(None), self.payload(""), {"tool_name": "Edit"}):
            with self.subTest(payload=payload):
                self.assert_ask(payload)
        loop = self.cwd / "loop"
        loop.symlink_to(loop)
        self.assert_ask(self.payload(loop))
        payload = self.payload("normal.txt")
        payload["cwd"] = str(loop)
        self.assert_ask(payload)

    def test_hook_is_registered_once_with_plugin_relative_path(self) -> None:
        config = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        command = f'python3 "${{CLAUDE_PLUGIN_ROOT}}/hooks/{HOOK.name}"'
        groups = [
            group for group in config["hooks"]["PreToolUse"]
            if any(hook["command"] == command for hook in group["hooks"])
        ]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["matcher"], "Edit|Write|MultiEdit|NotebookEdit")


if __name__ == "__main__":
    unittest.main()
