import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import content_safety_process as owned
import evaluate_content_safety as runner


DETACHED = """import json, os, pathlib, signal, subprocess, sys, time
root = pathlib.Path(sys.argv[1])
def exit_on_release(_signal, _frame):
    while not (root / 'allow-exit').exists():
        time.sleep(.01)
    sys.exit(0)
if sys.argv[2:] == ['controlled-exit']:
    signal.signal(signal.SIGTERM, exit_on_release)
child = subprocess.Popen([sys.executable, '-B', '-c', 'import time; time.sleep(3)'], start_new_session=True)
(root / 'identity.json').write_text(json.dumps({'parent': os.getpid(), 'child': child.pid, 'pgid': os.getpgrp()}))
print('{"type":"system","subtype":"diagnostic"}', flush=True)
print('public diagnostic', file=sys.stderr, flush=True)
if sys.argv[2:] != ['early-exit']:
    time.sleep(30)
"""


def run_short(args, cwd, env, timeout):
    return owned.run_owned(args, cwd, env, timeout=.5)


@unittest.skipUnless(os.name == 'posix', 'POSIX process sessions')
class DetachedPipeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        script = self.root / 'detached.py'
        script.write_text(DETACHED)
        self.command = [sys.executable, '-B', str(script), str(self.root)]
        self.addCleanup(self.await_detached_exit)

    def await_detached_exit(self) -> None:
        path = self.root / 'identity.json'
        if not path.exists():
            return
        identity = json.loads(path.read_text())
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            result = subprocess.run(['ps', '-o', 'stat=', '-p', str(identity['child'])], capture_output=True, text=True)
            if not result.stdout.strip() or result.stdout.strip().startswith('Z'):
                return
            time.sleep(.05)
        self.fail('The self-ending diagnostic child did not exit')

    def assert_parent_reaped(self) -> None:
        identity = json.loads((self.root / 'identity.json').read_text())
        self.assertNotEqual(identity['pgid'], os.getpgrp())
        result = subprocess.run(['ps', '-o', 'stat=', '-p', str(identity['parent'])], capture_output=True, text=True)
        self.assertFalse(result.stdout.strip(), 'The direct child must be reaped')

    def test_timeout_retains_diagnostics_with_detached_pipe_holder(self) -> None:
        started = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired) as caught:
            owned.run_owned(self.command, self.root, os.environ.copy(), timeout=.5)
        self.assertLess(time.monotonic() - started, 2.75)
        self.assertIn(b'"subtype":"diagnostic"', caught.exception.stdout)
        self.assertIn(b'public diagnostic', caught.exception.stderr)
        self.assert_parent_reaped()

    def observe_exit_before_term(self, process, force) -> None:
        if not force:
            state = subprocess.run(['ps', '-o', 'stat=', '-p', str(process.pid)], capture_output=True, text=True)
            self.assertTrue(state.stdout.strip().startswith('Z'), state.stdout)
            self.assertIsNone(process.returncode)
            self.observed.append(True)
        self.real_signal(process, force)

    def test_exited_parent_with_detached_pipes_records_timeout(self) -> None:
        self.real_signal = owned.signal_process
        self.observed = []
        with patch.object(owned, 'signal_process', side_effect=self.observe_exit_before_term), \
             patch.object(runner, 'command', return_value=[*self.command, 'early-exit']), \
             patch.object(runner, 'session_environment', return_value=os.environ.copy()), \
             patch.object(runner, 'run_owned', side_effect=run_short):
            events, errors = runner.run_session(self.root, 'diagnostic')
        self.assertEqual(self.observed, [True])
        self.assertEqual(errors, ['Claude timed out'])
        self.assertEqual(events, [{'type': 'system', 'subtype': 'diagnostic'}])
        self.assertIn('diagnostic', (self.root / 'output.jsonl').read_text())
        self.assertIn('public diagnostic', (self.root / 'stderr.log').read_text())
        self.assert_parent_reaped()

    def release_exit_after_wait(self, process) -> None:
        self.real_wait(process)
        if self.observed:
            return
        (self.root / 'allow-exit').touch()
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            state = subprocess.run(['ps', '-o', 'stat=', '-p', str(process.pid)], capture_output=True, text=True).stdout.strip()
            if state.startswith('Z'):
                self.observed.append(process.returncode)
                return
            time.sleep(.01)
        self.fail('The released diagnostic parent did not exit')

    def test_exit_between_wait_and_force_preserves_timeout(self) -> None:
        self.real_wait = owned.wait_direct
        self.observed = []
        with patch.object(owned, 'wait_direct', side_effect=self.release_exit_after_wait):
            with self.assertRaises(subprocess.TimeoutExpired) as caught:
                owned.run_owned([*self.command, 'controlled-exit'], self.root, os.environ.copy(), timeout=.5)
        self.assertEqual(self.observed, [None])
        self.assertIn(b'diagnostic', caught.exception.stdout)
        self.assertIn(b'public diagnostic', caught.exception.stderr)
        self.assert_parent_reaped()

    def test_evaluator_records_timeout_and_both_streams(self) -> None:
        with patch.object(runner, 'command', return_value=self.command), \
             patch.object(runner, 'session_environment', return_value=os.environ.copy()), \
             patch.object(runner, 'run_owned', side_effect=run_short):
            events, errors = runner.run_session(self.root, 'diagnostic')
        self.assertEqual(errors, ['Claude timed out'])
        self.assertEqual(events, [{'type': 'system', 'subtype': 'diagnostic'}])
        self.assertIn('diagnostic', (self.root / 'output.jsonl').read_text())
        self.assertIn('public diagnostic', (self.root / 'stderr.log').read_text())
        self.assert_parent_reaped()


if __name__ == '__main__':
    unittest.main()
