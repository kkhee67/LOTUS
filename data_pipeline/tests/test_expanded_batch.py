from collections import Counter
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from data_pipeline.normalize import MODELS, export_current, normalize, read_dataset
from data_pipeline.public_opportunities import CapturedApplication
from shared.rules import application_state


ROOT = Path(__file__).resolve().parents[2]


def test_expanded_batch_can_be_rebuilt_with_verified_links(tmp_path):
    raw = ROOT / "data/raw"
    submitted = ROOT / "data/normalized/expanded"

    result = normalize(
        raw / "dankook_recruitment.json",
        tmp_path,
        public_batch=(raw / "job_alio.json", raw / "organizer_notices.json"),
    )

    opportunities = result["opportunities"]
    assert len({item.source_url for item in opportunities}) == len(opportunities)
    assert {"job", "contest", "competition", "training", "event", "project", "certification", "notice"} == {
        item.type for item in opportunities
    }
    by_id = {item.id: item for item in opportunities}
    fair = by_id["seoul-global-job-fair-2026"]
    assert fair.event_schedule.starts_on.isoformat() == "2026-11-18"
    assert fair.application.closes_on is None
    certification = by_id["kcci-business-intelligence"]
    assert certification.application.status == "unknown"
    assert certification.certification.status == "active"
    assert certification.certification.exam_sessions[0].application.status == "closed"
    hospital = by_id["job-alio-306755"]
    assert hospital.type == "job"
    assert hospital.application.closes_at.isoformat() == "2026-11-20T17:00:00+09:00"
    assert any("토익" in requirement for requirement in hospital.requirements)
    volunteer = by_id["chungcheong2027-lumi-volunteers"]
    assert "체육학" in volunteer.related_majors
    assert any(evidence.field == "related_majors" for evidence in volunteer.evidence)
    for name in MODELS:
        filename = f"{name}.json"
        assert (tmp_path / filename).read_bytes() == (submitted / filename).read_bytes()


def test_current_export_rebuilds_without_expired_opportunities(tmp_path):
    normalized = ROOT / "data/normalized"
    now = datetime.fromisoformat("2026-11-14T12:00:00+09:00")
    expanded = read_dataset(normalized / "expanded")
    result = export_current(expanded, tmp_path, now=now)
    ids = {item.id for item in result["opportunities"]}
    counts = Counter(item.type for item in result["opportunities"])
    assert all(counts[kind] >= 30 for kind in (
        "contest", "competition", "training", "event", "project", "certification", "notice"
    ))
    assert "sff-character-2026" in ids
    assert "dankook-recruitment-186322" not in ids
    assert "blaybus-manufacturing-ax-1148" in ids
    assert all(
        item.certification.status == "active" if item.certification
        else (application_state(item.application, now=now).status in {"open", "upcoming"}
              or (item.application.status == "unknown" and
                  (item.subtype == "policy_guide" or
                   (item.type == "event" and item.event_schedule.ends_on >= now.date()))))
        for item in result["opportunities"]
    )
    assert {source.id for source in result["sources"]} == {
        source_id for item in result["opportunities"] for source_id in item.source_ids
    }
    for name in MODELS:
        filename = f"{name}.json"
        assert (tmp_path / filename).read_bytes() == (normalized / "current" / filename).read_bytes()


@pytest.mark.parametrize("deadline", [1795705200, "2026-11-27T18:00:00"])
def test_captured_deadline_requires_an_explicit_offset(deadline):
    with pytest.raises(ValidationError, match="explicit UTC offset"):
        CapturedApplication.model_validate({"closes_at": deadline})
