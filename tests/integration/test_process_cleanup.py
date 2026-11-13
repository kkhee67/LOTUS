"""Own-process cleanup on success, failure, timeout, and Windows command dispatch."""
import json
import socket
import subprocess
import sys
import time

import pytest
from scripts import processes


@pytest.mark.parametrize('failure', [False, True])
def test_runner_stops_descendant_and_releases_inherited_log(tmp_path, failure):
    ready = tmp_path / 'ready.json'
    log = tmp_path / 'servers.log'
    child = (
        "import socket,time,json; from pathlib import Path; "
        "s=socket.socket(); s.bind(('127.0.0.1',0)); s.listen(); "
        f"Path({str(ready)!r}).write_text(json.dumps(s.getsockname()[1])); time.sleep(60)"
    )
    parent = (
        f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child!r}]); time.sleep(60)"
    )
    try:
        with log.open('w') as output:
            with processes.managed_process([sys.executable, '-c', parent], stdout=output, stderr=output) as process:
                deadline = time.monotonic() + 10
                while not ready.exists():
                    if process.poll() is not None or time.monotonic() > deadline:
                        pytest.fail('Descendant did not start')
                    time.sleep(0.05)
                port = json.loads(ready.read_text())
                if failure:
                    raise RuntimeError('expected test failure')
    except RuntimeError as error:
        assert failure and str(error) == 'expected test failure'
    assert process.poll() is not None
    # Kernel handle release can briefly lag forced process-tree termination.
    deadline = time.monotonic() + 5
    while True:
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', port)) != 0:
                break
        assert time.monotonic() < deadline, 'Descendant still listening'
        time.sleep(0.05)
    log.unlink()  # On Windows this fails if a descendant retains the file handle.
    assert not log.exists()


def test_timeout_still_stops_owned_process():
    with pytest.raises(subprocess.TimeoutExpired):
        with processes.managed_process([sys.executable, '-c', 'import time; time.sleep(60)']) as process:
            process.wait(timeout=0.05)
    assert process.poll() is not None


def test_windows_uses_only_owned_pid_and_entire_tree(monkeypatch):
    monkeypatch.setattr(processes, 'WINDOWS', True)
    class Owned:
        pid = 12345
        def poll(self): return None
        def wait(self, timeout): assert timeout == 5
    calls = []
    def taskkill(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0)
    monkeypatch.setattr(processes.subprocess, 'run', taskkill)
    processes.stop_process(Owned())
    assert calls[0][0] == ['taskkill', '/PID', '12345', '/T', '/F']
    assert calls[0][1]['timeout'] == 10


def test_windows_cleanup_failure_is_not_reported_as_success(monkeypatch):
    monkeypatch.setattr(processes, 'WINDOWS', True)
    class Owned:
        pid = 12345
        def poll(self): return None
    monkeypatch.setattr(processes.subprocess, 'run', lambda *args, **kwargs: subprocess.CompletedProcess(args, 1))
    with pytest.raises(RuntimeError, match='Could not stop'):
        processes.stop_process(Owned())
