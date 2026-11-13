import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.importer import import_directory


def test_unexpected_response_error_is_contained_and_has_cors(monkeypatch):
    monkeypatch.setattr(main, 'options', {'secret': 'private-response-sentinel'})
    with TestClient(main.app) as client:
        response = client.get('/api/v1/options', headers={'Origin': 'http://localhost:5173'})
        assert response.status_code == 500
        assert response.json()['error']['code'] == 'INTERNAL_ERROR'
        assert 'private-response-sentinel' not in response.text
        assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'
        assert client.get('/api/v1/health').status_code == 200


@pytest.mark.parametrize('origin,allowed', [
    ('http://localhost:5173', True), ('https://untrusted.example', False),
])
def test_response_validation_error_does_not_expand_cors(monkeypatch, origin, allowed):
    monkeypatch.setattr(main, 'options', {'secret': 'private-response-sentinel'})
    response = TestClient(main.app).get('/api/v1/options', headers={'Origin': origin})
    assert response.status_code == 500
    assert response.headers.get('access-control-allow-origin') == (origin if allowed else None)


@pytest.mark.parametrize('body', [
    '{"profile":{"goal":"private-input-sentinel"}',
    '{"profile":{"goal":"private-input-sentinel","unknown_key":true}}',
    '{"profile":{"age":"private-input-sentinel"}}',
])
def test_invalid_request_is_safe(body):
    response = TestClient(main.app).post('/api/v1/recommendations', content=body,
                                         headers={'Content-Type': 'application/json'})
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'VALIDATION_ERROR'
    assert 'private-input-sentinel' not in response.text


def test_failed_recommendation_hides_input_and_keeps_catalog_available(tmp_path, monkeypatch, caplog):
    db = tmp_path / 'real.db'
    import_directory('data/normalized', db, mode='real')
    before = db.read_bytes()
    monkeypatch.setattr(main.settings, 'database_url', 'sqlite:///' + str(db))
    monkeypatch.setattr(main.settings, 'data_mode', 'real')
    def broken_engine(*args, **kwargs):
        raise RuntimeError('private-engine-sentinel private-profile-sentinel')
    monkeypatch.setattr('backend.service_adapters.opportunity_engine.recommend', broken_engine)
    client = TestClient(main.app)
    response = client.post('/api/v1/recommendations', json={'profile': {'goal': 'private-profile-sentinel'}})
    assert response.status_code == 500 and response.json()['error']['code'] == 'INTERNAL_ERROR'
    assert 'private-' not in response.text and 'private-' not in caplog.text
    assert client.get('/api/v1/opportunities').json()['total'] == 3
    assert client.get('/api/v1/health').status_code == 200
    assert db.read_bytes() == before


def test_actual_server_logs_do_not_receive_invalid_response_payload():
    root = Path(__file__).resolve().parents[2]
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    # A public test sentinel, never a real secret. No production route is added.
    code = ("from backend import main; import uvicorn; "
            "main.options={'secret':'private-log-sentinel'}; "
            f"uvicorn.run(main.app,host='127.0.0.1',port={port},access_log=False)")
    process = subprocess.Popen([sys.executable, '-c', code], cwd=root,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    try:
        with httpx.Client(timeout=1) as client:
            deadline = time.monotonic() + 15
            while True:
                if process.poll() is not None:
                    pytest.fail('Test server exited before startup')
                try:
                    response = client.get(f'http://127.0.0.1:{port}/api/v1/options',
                                          headers={'Origin': 'http://localhost:5173'})
                    break
                except httpx.TransportError:
                    if time.monotonic() > deadline:
                        pytest.fail('Test server startup timed out')
                    time.sleep(0.1)
            assert response.status_code == 500
            assert 'private-log-sentinel' not in response.text
            assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'
            assert client.get(f'http://127.0.0.1:{port}/api/v1/health').status_code == 200
    finally:
        process.terminate()
        try:
            output, _ = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate(timeout=5)
    assert b'private-log-sentinel' not in output
    assert b'Traceback' not in output
