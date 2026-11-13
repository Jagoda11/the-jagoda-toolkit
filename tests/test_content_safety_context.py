import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import content_safety_context as context
import evaluate_content_safety as runner


class ContentSafetyContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.original = self.root / "sample.txt"
        self.original.write_text("Orchid catalogue", encoding="utf-8")
        managed = patch.object(context, "managed_context_present", return_value=False)
        managed.start()
        self.addCleanup(managed.stop)

    def test_each_source_has_a_loader_control_and_an_exclusion_check(self) -> None:
        for mode in ("project-enabled", "project-disabled", "memory-enabled", "memory-disabled"):
            with self.subTest(mode=mode):
                fixture = context.prepare(self.root / mode, self.original, mode)
                token = context.canary_token(fixture.parent, mode)
                prompt = runner.prompt_for(fixture, mode)
                self.assertNotIn(token, prompt)
                settings = json.loads((fixture.parent / "settings.json").read_text())
                env = context.session_environment(fixture.parent, mode)
                self.assertEqual(env["CLAUDE_CODE_DISABLE_CLAUDE_MDS"], "1" if mode == "project-disabled" else "0")
                self.assertEqual(env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"], "0" if mode == "memory-enabled" else "1")
                self.assertEqual(settings["autoMemoryEnabled"], mode.startswith("memory-"))
                command = runner.command(fixture.parent, prompt, mode)
                self.assertEqual(command[command.index("--setting-sources") + 1], "project")

    def test_memory_control_pair_changes_only_the_auto_memory_switch(self) -> None:
        enabled = context.session_environment(self.root, "memory-enabled")
        disabled = context.session_environment(self.root, "memory-disabled")
        self.assertEqual(enabled["CLAUDE_CODE_DISABLE_CLAUDE_MDS"], "0")
        self.assertEqual(disabled["CLAUDE_CODE_DISABLE_CLAUDE_MDS"], "0")
        enabled.pop("CLAUDE_CODE_DISABLE_AUTO_MEMORY")
        disabled.pop("CLAUDE_CODE_DISABLE_AUTO_MEMORY")
        self.assertEqual(enabled, disabled)

    def test_positive_controls_require_their_actual_source_file(self) -> None:
        for mode, relative in (("project-enabled", "CLAUDE.md"), ("memory-enabled", "memory/MEMORY.md")):
            with self.subTest(mode=mode):
                fixture = context.prepare(self.root / mode, self.original, mode)
                self.assertEqual(context.startup_precheck(fixture.parent, mode), [])
                (fixture.parent / relative).unlink()
                self.assertTrue(context.startup_precheck(fixture.parent, mode))

    def test_uncontrolled_managed_context_blocks_enabled_checks(self) -> None:
        fixture = context.prepare(self.root / "managed", self.original, "project-enabled")
        with patch.object(context, "managed_context_present", return_value=True):
            self.assertTrue(context.startup_precheck(fixture.parent, "project-enabled"))

    def test_external_instructions_are_excluded_without_mutating_them(self) -> None:
        fixture = context.prepare(self.root / "memory-enabled", self.original, "memory-enabled")
        settings = json.loads((fixture.parent / "settings.json").read_text())
        excluded = settings["claudeMdExcludes"]
        self.assertIn(str(Path.home() / ".claude" / "CLAUDE.md"), excluded)
        self.assertIn(str(fixture.parent / "CLAUDE.md"), excluded)
        tokens = json.loads((fixture.parent / "canary.json").read_text())
        self.assertNotEqual(tokens["token"], tokens["memory_token"])


if __name__ == "__main__":
    unittest.main()
