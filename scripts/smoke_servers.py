"""Start isolated local servers, check real HTTP, and always stop our processes."""
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def wait_for(url, process):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError('Server exited before readiness')
        try:
            with urlopen(url, timeout=1) as response:
                return response.read()
        except (URLError, TimeoutError):
            time.sleep(0.2)
    raise TimeoutError('Server did not become ready')


def main():
    backend_port, frontend_port = free_port(), free_port()
    processes = []
    try:
        backend = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.main:app', '--host',
                                    '127.0.0.1', '--port', str(backend_port), '--no-access-log'],
                                   cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(backend)
        base = f'http://127.0.0.1:{backend_port}/api/v1'
        assert json.loads(wait_for(base+'/health', backend))['status'] == 'ok'
        assert json.loads(wait_for(base+'/options', backend))['opportunity_types']
        caps = json.loads(wait_for(base+'/capabilities', backend))
        assert caps['opportunities']['implemented'] and caps['opportunities']['enabled']
        assert all(flag['enabled'] == (name == 'recommendations') and flag['implemented'] == (name in {'recommendations', 'resource-links'})
                   for name, flag in caps.items() if name != 'opportunities')
        frontend = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1',
                                     '--port', str(frontend_port), '--strictPort'],
                                    cwd=ROOT/'frontend', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(frontend)
        assert b'id="root"' in wait_for(f'http://127.0.0.1:{frontend_port}', frontend)
        print('PASS: actual backend health/options/capabilities and Vite HTTP. Browser rendering not tested.')
    finally:
        for process in reversed(processes):
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == '__main__':
    main()
