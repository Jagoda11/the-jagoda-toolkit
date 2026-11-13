import errno
import json
import os
import signal
import subprocess
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch
import content_safety_process as owned


TREE = """import json, os, pathlib, signal, subprocess, sys, time
level = int(sys.argv[1])
root = pathlib.Path(sys.argv[2])
child = subprocess.Popen([sys.executable, '-B', __file__, str(level - 1), str(root), sys.argv[3]]) if level else None
def stop(_signal, _frame):
    if child:
        child.wait()
    sys.exit(0)
signal.signal(signal.SIGTERM, signal.SIG_IGN if not level and sys.argv[3] == 'ignore' else stop)
(root / (str(level) + '.json')).write_text(json.dumps({'pid': os.getpid(), 'pgid': os.getpgrp()}))
print(json.dumps({'level': level}), flush=True)
print('diagnostic-' + str(level), file=sys.stderr, flush=True)
while True:
    if not level:
        with (root / 'heartbeat.txt').open('a') as output:
            output.write('tick\\n')
    time.sleep(.03)
"""


CLOSED_TREE = """import json, os, pathlib, signal, subprocess, sys, time
root = pathlib.Path(sys.argv[1])
if len(sys.argv) == 2:
    subprocess.Popen([sys.executable, '-B', __file__, str(root), 'child'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    (root / '2.json').write_text(json.dumps({'pid': os.getpid(), 'pgid': os.getpgrp()}))
    print('parent ready', flush=True)
else:
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    (root / '0.json').write_text(json.dumps({'pid': os.getpid(), 'pgid': os.getpgrp()}))
while True:
    if len(sys.argv) > 2:
        with (root / 'heartbeat.txt').open('a') as output:
            output.write('tick')
    time.sleep(.03)
"""


class OwnedProcessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def test_normal_exit_captures_both_streams_and_closes_stdin(self) -> None:
        source = "import sys; print(len(sys.stdin.read())); print('diagnostic', file=sys.stderr); sys.exit(7)"
        result = owned.run_owned([sys.executable, '-B', '-c', source], self.root, os.environ.copy())
        self.assertEqual(result.returncode, 7)
        self.assertEqual(result.stdout, b'0\n')
        self.assertEqual(result.stderr, b'diagnostic\n')

    @unittest.skipUnless(os.name == 'posix', 'POSIX process groups')
    def test_timeout_stops_child_and_grandchild(self) -> None:
        self.check_tree('normal')

    @unittest.skipUnless(os.name == 'posix', 'POSIX process groups')
    def test_timeout_escalates_for_a_descendant_ignoring_term(self) -> None:
        self.check_tree('ignore')

    def check_tree(self, mode: str) -> None:
        script = self.root / 'tree.py'
        script.write_text(TREE)
        self.addCleanup(self.cleanup_tree)
        with self.assertRaises(subprocess.TimeoutExpired) as caught:
            owned.run_owned([sys.executable, '-B', str(script), '2', str(self.root), mode],
                            self.root, os.environ.copy(), timeout=2)
        self.assertIn(b'diagnostic-0', caught.exception.stderr)
        self.assertIn(b'"level": 0', caught.exception.stdout)
        identities = [json.loads((self.root / (str(level) + '.json')).read_text()) for level in range(3)]
        pgids = {item['pgid'] for item in identities}
        self.assertEqual(len(pgids), 1)
        self.assertNotIn(os.getpgrp(), pgids)
        before = (self.root / 'heartbeat.txt').read_bytes()
        time.sleep(.12)
        self.assertEqual((self.root / 'heartbeat.txt').read_bytes(), before)
        states = [subprocess.run(['ps', '-o', 'stat=', '-p', str(identity['pid'])],
                                 capture_output=True, text=True).stdout.strip() for identity in identities]
        self.assertFalse(states[2], 'The direct child must be reaped')
        self.assertTrue(all(not state or state.startswith('Z') for state in states), states)

    @unittest.skipUnless(os.name == 'posix', 'POSIX process groups')
    def test_survivor_with_closed_output_pipes_is_still_killed(self) -> None:
        script = self.root / 'closed.py'
        script.write_text(CLOSED_TREE)
        self.addCleanup(self.cleanup_tree)
        with self.assertRaises(subprocess.TimeoutExpired) as caught:
            owned.run_owned([sys.executable, '-B', str(script), str(self.root)],
                            self.root, os.environ.copy(), timeout=2)
        self.assertIn(b'parent ready', caught.exception.stdout)
        child = json.loads((self.root / '0.json').read_text())
        before = (self.root / 'heartbeat.txt').read_bytes()
        time.sleep(.12)
        self.assertEqual((self.root / 'heartbeat.txt').read_bytes(), before)
        result = subprocess.run(['ps', '-o', 'stat=', '-p', str(child['pid'])], capture_output=True, text=True)
        self.assertTrue(not result.stdout.strip() or result.stdout.strip().startswith('Z'), result.stdout)

    def cleanup_tree(self) -> None:
        identity = self.root / '2.json'
        if identity.exists():
            pgid = json.loads(identity.read_text())['pgid']
            self.assertNotEqual(pgid, os.getpgrp())
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    @unittest.skipUnless(os.name == 'posix', 'POSIX process groups')
    def test_permission_handling_is_limited_to_exited_owned_groups(self) -> None:
        for force in (False, True):
            reaped = SimpleNamespace(pid=123456, returncode=None, poll=Mock(return_value=0))
            with patch.object(owned.os, 'killpg', side_effect=PermissionError(errno.EPERM, 'denied')):
                self.assertIsNone(owned.signal_process(reaped, force))
                reaped.poll.assert_called_once_with()
        for code, returncode, force in ((errno.EPERM, None, True), (errno.EPERM, None, False),
                                        (errno.EACCES, 0, True), (errno.EACCES, 0, False)):
            with self.subTest(code=code, returncode=returncode, force=force):
                process = SimpleNamespace(pid=123456, returncode=returncode, poll=Mock(return_value=returncode))
                with patch.object(owned.os, 'killpg', side_effect=PermissionError(code, 'denied')):
                    with self.assertRaises(PermissionError):
                        owned.signal_process(process, force)

    def test_final_drain_keeps_partial_streams_if_wait_hits_its_deadline(self) -> None:
        process = Mock()
        process.communicate.side_effect = subprocess.TimeoutExpired(['probe'], 1, output=b'partial', stderr=b'diagnostic')
        process.wait.side_effect = subprocess.TimeoutExpired(['probe'], 1)
        self.assertEqual(owned.drain_output(process), (b'partial', b'diagnostic'))
        process.stdout.close.assert_called_once()
        process.stderr.close.assert_called_once()

    def test_interrupt_also_stops_and_waits_for_owned_process(self) -> None:
        with patch.object(owned.subprocess, 'Popen') as invoke, patch.object(owned, 'signal_process') as stop:
            process = invoke.return_value.__enter__.return_value
            process.communicate.side_effect = [KeyboardInterrupt(), (b'partial', b'diagnostic')]
            with self.assertRaises(KeyboardInterrupt):
                owned.run_owned(['fixture-command'], self.root, {})
        self.assertEqual(stop.call_args_list[0].args, (process, False))
        self.assertEqual(stop.call_args_list[1].args, (process, True))
        self.assertEqual(process.communicate.call_count, 2)
        process.wait.assert_called_once_with(timeout=owned.TERMINATE_GRACE_SECONDS)
        invoke.return_value.__exit__.assert_called_once()


if __name__ == '__main__':
    unittest.main()
