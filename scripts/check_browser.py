"""Start isolated real-data servers and run the deterministic browser regression."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

from backend.importer import import_directory
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
    processes = []
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
        # Logs stay in the temporary directory; no user profiles are printed.
        with (Path(directory) / 'servers.log').open('w') as log:
            try:
                server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'tests.browser_server:app',
                    '--host', '127.0.0.1', '--port', str(api_port), '--no-access-log'],
                    cwd=ROOT, env=env, stdout=log, stderr=log)
                processes.append(server)
                ui_server = subprocess.Popen(['node', str(ROOT / 'frontend/node_modules/vite/bin/vite.js'),
                    '--host', '127.0.0.1', '--port', str(ui_port), '--strictPort'],
                    cwd=ROOT / 'frontend', env=env, stdout=log, stderr=log)
                processes.append(ui_server)
                wait_ready(api + '/api/v1/health', server)
                wait_ready(ui, ui_server)
                for script in ('recommendation_browser.mjs', 'service_feedback_browser.mjs'):
                    subprocess.run(['node', 'tests/integration/' + script],
                                   cwd=ROOT, env=env, check=True, timeout=120)
            finally:
                for process in reversed(processes):
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()


if __name__ == '__main__':
    main()
