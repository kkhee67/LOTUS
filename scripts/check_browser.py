"""Start isolated real-data servers and run the deterministic browser regression."""
from contextlib import ExitStack
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

from backend.importer import import_directory
from scripts.processes import managed_process
from tests.support import REAL_BATCH, RECOMMENDATION_TIME

ROOT = Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def wait_ready(url, process):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError('Test server exited during startup')
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError('Test server startup timed out')


def main():
    with tempfile.TemporaryDirectory(prefix='lotus-browser-') as directory:
        db = Path(directory) / 'real.db'
        import_directory(REAL_BATCH, db, mode='real')
        api_port, ui_port = free_port(), free_port()
        while ui_port == api_port:
            ui_port = free_port()
        api = f'http://127.0.0.1:{api_port}'
        ui = f'http://127.0.0.1:{ui_port}'
        env = {**os.environ, 'DATABASE_URL': 'sqlite:///' + str(db), 'DATA_MODE': 'real',
               'CORS_ORIGINS': ui, 'VITE_API_BASE_URL': api, 'LOTUS_TEST_URL': ui,
               'LOTUS_TEST_TIME': RECOMMENDATION_TIME.isoformat(), 'LOTUS_TEST_DB': str(db)}
        # Do not pass temporary file handles to servers or their descendants.
        # Vite/esbuild can retain inherited handles after the parent exits on Windows.
        # ExitStack stops every owned tree before TemporaryDirectory removes the DB.
        with ExitStack() as stack:
            server = stack.enter_context(managed_process(
                [sys.executable, '-m', 'uvicorn', 'tests.browser_server:app',
                 '--host', '127.0.0.1', '--port', str(api_port), '--no-access-log'],
                cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
            ui_server = stack.enter_context(managed_process(
                ['node', str(ROOT / 'frontend/node_modules/vite/bin/vite.js'),
                 '--host', '127.0.0.1', '--port', str(ui_port), '--strictPort'],
                cwd=ROOT / 'frontend', env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
            wait_ready(api + '/api/v1/health', server)
            wait_ready(ui, ui_server)
            for script in ('recommendation_browser.mjs', 'service_feedback_browser.mjs'):
                args = ['node', 'tests/integration/' + script]
                with managed_process(args, cwd=ROOT, env=env) as browser:
                    code = browser.wait(timeout=120)
                    if code:
                        raise subprocess.CalledProcessError(code, args)


if __name__ == '__main__':
    main()
