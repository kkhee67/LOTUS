import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from backend.main import app, FEATURES
from shared.models import RecommendationRequest

client = TestClient(app)

def test_health_and_capabilities():
    assert client.get("/api/v1/health").json()["status"] == "ok"
    caps = client.get("/api/v1/capabilities").json()
    assert caps['opportunities']['enabled'] and caps['opportunities']['implemented']
    assert all(not x['enabled'] and not x['implemented'] for name, x in caps.items() if name != 'opportunities')

@pytest.mark.parametrize("feature", FEATURES)
def test_unimplemented(feature):
    r = client.post(f"/api/v1/{feature}", json={"profile":{"major":"소프트웨어"}})
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "FEATURE_UNAVAILABLE"

def test_example_and_privacy_defaults():
    example = json.loads(Path("contracts/examples/recommendation_request.json").read_text(encoding="utf-8"))
    req = RecommendationRequest.model_validate(example["request"])
    assert example["source_kind"] == "synthetic"
    assert req.allow_external_ai is False
    assert req.profile.age is None

@pytest.mark.parametrize("profile", [{}, {"major":"개발", "secret":"private"}, {"major":"개발", "experience_status":"provided"}])
def test_invalid_profiles(profile):
    with pytest.raises(ValidationError):
        RecommendationRequest(profile=profile)

def test_not_found():
    assert client.get("/api/v1/missing").status_code == 404


def test_validation_error_hides_input():
    r = client.post("/api/v1/recommendations", json={"profile":{"secret":"private-value"}})
    assert r.status_code == 422
    assert "private-value" not in r.text
