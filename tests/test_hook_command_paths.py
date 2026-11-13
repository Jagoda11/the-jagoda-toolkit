import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHELL_HOOKS = ('rtk-rewrite.sh', 'block-git-commit-protected.sh', 'no-overwrite.sh',
               'scan-credentials.sh', 'verify-on-write.sh')


def registered_commands() -> list[str]:
    config = json.loads((ROOT / 'hooks/hooks.json').read_text())
    return [hook['command'] for groups in config['hooks'].values()
            for group in groups for hook in group['hooks']]


class HookCommandPathTests(unittest.TestCase):
    def test_shell_hook_paths_with_spaces_remain_one_argument(self) -> None:
        commands = registered_commands()
        plugin_root = ROOT.parent / 'plugin folder with spaces'
        env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(plugin_root))
        for name in SHELL_HOOKS:
            command, = [value for value in commands if value.endswith(name) or value.endswith(name + '"')]
            with self.subTest(name=name):
                self.assertEqual(command, f'"${{CLAUDE_PLUGIN_ROOT}}/hooks/{name}"')
                probe = 'set -- ' + command + '; printf "%s\\n" "$#" "$1"'
                result = subprocess.run(['/bin/sh', '-c', probe], env=env, capture_output=True, text=True, check=True)
                self.assertEqual(result.stdout.splitlines(), ['1', str(plugin_root / 'hooks' / name)])


if __name__ == '__main__':
    unittest.main()
