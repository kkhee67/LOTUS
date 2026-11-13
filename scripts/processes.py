"""Lifecycle for subprocess trees owned by local test runners only."""
from contextlib import contextmanager
import os
import signal
import subprocess
import sys

WINDOWS = sys.platform == 'win32'


def stop_process(process):
    if WINDOWS:
        if process.poll() is None:
            # Kill descendants while their parent PID still identifies our tree.
            result = subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    timeout=10, check=False)
            if result.returncode and process.poll() is None:
                raise RuntimeError('Could not stop the owned test process tree')
        process.wait(timeout=5)
        return
    # Each process was started in its own session. Never signal the user's group.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    finally:
        # A descendant can ignore TERM or outlive an already-exited parent.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)


@contextmanager
def managed_process(args, **kwargs):
    process = subprocess.Popen(args, start_new_session=not WINDOWS, **kwargs)
    try:
        yield process
    finally:
        stop_process(process)
