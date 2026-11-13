"""Run an evaluation with owned process lifetime and captured diagnostics."""

import errno
import os
import signal
import subprocess
from pathlib import Path

TERMINATE_GRACE_SECONDS = 1
DRAIN_GRACE_SECONDS = 1


def ignorable_signal_error(process: subprocess.Popen, error: OSError) -> bool:
    return error.errno == errno.ESRCH or (os.name == "posix"
                                        and error.errno == errno.EPERM and process.poll() is not None)


def signal_process(process: subprocess.Popen, force: bool) -> None:
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL if force else signal.SIGTERM)
        elif force:
            process.kill()
        else:
            process.terminate()
    except OSError as error:
        if not ignorable_signal_error(process, error):
            raise


def wait_direct(process: subprocess.Popen) -> None:
    try:
        process.wait(timeout=TERMINATE_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        pass


def drain_output(process: subprocess.Popen) -> tuple[bytes, bytes]:
    try:
        return process.communicate(timeout=DRAIN_GRACE_SECONDS)
    except subprocess.TimeoutExpired as error:
        for pipe in (process.stdout, process.stderr):
            if pipe is not None:
                pipe.close()
        wait_direct(process)
        return error.stdout or b"", error.stderr or b""


def run_owned(args: list[str], cwd: Path, env: dict[str, str], timeout: float = 120) -> subprocess.CompletedProcess:
    with subprocess.Popen(args, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          start_new_session=os.name == "posix") as process:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except BaseException as error:
            try:
                signal_process(process, False)
                wait_direct(process)
            finally:
                signal_process(process, True)
            stdout, stderr = drain_output(process)
            if isinstance(error, subprocess.TimeoutExpired):
                error.output, error.stderr = stdout, stderr
            raise
        return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
