import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from data_pipeline.normalize import MODELS, main, normalize, read_dataset
from shared.rules import application_state


@pytest.fixture
def capture():
    return {
        "post_id": "999999",
        "title": "테스트용 공고",
        "summary": "테스트 전용 수동 입력 예시",
        "region": "테스트 지역",
        "activities": ["테스트 업무"],
        "requirements": ["테스트용 학위 조건 또는 예외"],
        "experience_note": "테스트 경력 우대",
        "application": {"status": "unknown", "closes_on": "2026-11-30"},
        "application_note": "테스트에서 마감 날짜만 제공한다.",
        "published_on": "2026-11-05",
        "checked_at": "2026-11-11T12:00:00+09:00",
    }


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def snapshot_outputs(directory):
    if not directory.exists():
        return {}
    return {
        path.name: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in directory.iterdir()
    }


def test_newer_capture_updates_one_stable_id_and_preserves_other_arrays(tmp_path, capture):
    input_file = tmp_path / "capture.json"
    output = tmp_path / "output"
    write_json(input_file, [capture])
    normalize(input_file, output)

    role = {
        "id": "test-role",
        "name": "테스트 직무",
        "tasks": [],
        "fields": [],
        "preparation_skills": [],
        "source_ids": ["dankook-recruitment"],
        "source_url": "https://example.org/role",
        "source_kind": "real",
        "checked_at": capture["checked_at"],
    }
    write_json(output / "roles.json", [role])
    new_capture = {
        **capture,
        "title": "테스트용 수정 공고",
        "checked_at": "2026-11-12T12:00:00+09:00",
    }
    write_json(input_file, [new_capture])
    normalize(input_file, output)

    write_json(input_file, [capture])
    normalize(input_file, output)
    dataset = read_dataset(output)
    item, = dataset["opportunities"]
    assert item.id == "dankook-recruitment-999999"
    assert item.title == new_capture["title"]
    assert item.experience_required is None
    assert item.unresolved_conditions == capture["requirements"]
    assert item.application.closes_at is None
    assert item.application.closes_on.isoformat() == capture["application"]["closes_on"]
    assert dataset["roles"][0].id == role["id"]
    assert dataset["sources"][0].checked_at == item.checked_at


@pytest.mark.parametrize("failure", ["missing", "duplicate", "invalid_date", "timestamp_date", "missing_title"])
def test_invalid_capture_leaves_all_outputs_untouched(tmp_path, capture, failure):
    input_file = tmp_path / "capture.json"
    output = tmp_path / "output"
    write_json(input_file, [capture])
    normalize(input_file, output)
    before = {name: (output / f"{name}.json").read_bytes() for name in MODELS}

    if failure == "missing":
        input_file = tmp_path / "missing.json"
    elif failure == "duplicate":
        write_json(input_file, [capture, capture])
    elif failure == "invalid_date":
        write_json(input_file, [{**capture, "published_on": "2026-11-31"}])
    elif failure == "timestamp_date":
        write_json(input_file, [{**capture, "published_on": "2026-11-11T00:00:00+09:00"}])
    else:
        del capture["title"]
        write_json(input_file, [capture])

    with pytest.raises((FileNotFoundError, ValueError)):
        normalize(input_file, output)
    assert {name: (output / f"{name}.json").read_bytes() for name in MODELS} == before


@pytest.mark.parametrize("existing_batch", [False, True])
def test_duplicate_nested_capture_key_leaves_output_untouched(tmp_path, capture, existing_batch):
    input_file = tmp_path / "capture.json"
    output = tmp_path / "output"
    if existing_batch:
        write_json(input_file, [capture])
        normalize(input_file, output)
    before = snapshot_outputs(output)

    updated = {**capture, "checked_at": "2026-11-12T12:00:00+09:00"}
    text = json.dumps([updated], ensure_ascii=False)
    input_file.write_text(
        text.replace('"status": "unknown"', '"status": "closed", "status": "open"', 1),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"capture\.json: duplicate JSON key 'status'"):
        normalize(input_file, output)

    assert snapshot_outputs(output) == before
    assert output.exists() == existing_batch


@pytest.mark.parametrize("name", MODELS)
def test_duplicate_normalized_key_is_rejected_without_writing(tmp_path, capture, name):
    input_file = tmp_path / "capture.json"
    output = tmp_path / "output"
    write_json(input_file, [capture])
    normalize(input_file, output)
    path = output / f"{name}.json"
    if name in ("roles", "resource_links"):
        record = {
            "id": "test-entry",
            "name": "테스트용 항목",
            "source_ids": ["dankook-recruitment"],
            "source_kind": "real",
            "checked_at": capture["checked_at"],
        }
        if name == "roles":
            record.update(tasks=[], fields=[], preparation_skills=[], source_url="https://example.org/role")
        else:
            record.update(kind="official_site", description="테스트 설명", url="https://example.org/link")
        write_json(path, [record])
    read_dataset(output)

    text = path.read_text(encoding="utf-8")
    if name == "opportunities":
        key = "status"
        text = text.replace('"status": "unknown"', '"status": "closed", "status": "open"', 1)
    else:
        key = "name"
        text = text.replace('"name":', '"name": "이전 이름", "name":', 1)
    path.write_text(text, encoding="utf-8")
    message = rf"{name}\.json: duplicate JSON key '{key}'"
    before = snapshot_outputs(output)
    with pytest.raises(ValueError, match=message):
        read_dataset(output)
    assert snapshot_outputs(output) == before

    missing = output / ("resource_links.json" if name == "roles" else "roles.json")
    missing.unlink()
    before = snapshot_outputs(output)
    with pytest.raises(ValueError, match=message):
        normalize(input_file, output)
    assert snapshot_outputs(output) == before
    assert not missing.exists()


def test_exact_deadline_survives_normalization(tmp_path, capture):
    input_file = tmp_path / "capture.json"
    output = tmp_path / "output"
    deadline = "2026-11-18T23:59:00+09:00"
    write_json(input_file, [{**capture, "application": {"status": "open", "closes_at": deadline}}])

    normalize(input_file, output)

    item, = read_dataset(output)["opportunities"]
    assert item.application.closes_on is None
    assert item.application.closes_at.isoformat() == deadline
    cutoff = datetime.fromisoformat(deadline)
    assert application_state(item.application, now=cutoff - timedelta(seconds=1)).status == "open"
    assert application_state(item.application, now=cutoff).status == "closed"


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"application": {"opens_on": "2026-11-18T00:00:00+09:00"}}, "opens_on requires YYYY-MM-DD"),
        ({"application": {"closes_on": "2026-11-18T00:00:00+09:00"}}, "closes_on requires YYYY-MM-DD"),
        ({"application": {"closes_at": 1795000000}}, "closes_at: use a timestamp"),
        ({"application": {"opens_at": "2026-11-18T09:00:00"}}, "opens_at: use a timestamp"),
        ({"checked_at": "1795000000"}, "use a timestamp with an explicit UTC offset"),
    ],
)
def test_capture_rejects_dates_with_wrong_precision(tmp_path, capture, changes, message):
    input_file = tmp_path / "capture.json"
    output = tmp_path / "output"
    write_json(input_file, [{**capture, **changes}])

    with pytest.raises(ValueError, match=message):
        normalize(input_file, output)

    assert not output.exists()


def test_as_of_reports_calculated_status_without_writing(tmp_path, capture, monkeypatch, capsys):
    input_file = tmp_path / "capture.json"
    output = tmp_path / "output"
    deadline = "2026-11-18T23:59:00+09:00"
    write_json(input_file, [{**capture, "application": {"status": "open", "closes_at": deadline}}])
    normalize(input_file, output)
    files = list(output.glob("*.json"))
    before = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in files}

    monkeypatch.setattr(sys, "argv", [
        "data_pipeline.normalize", "--output", str(output), "--as-of", deadline,
    ])
    main()

    report = capsys.readouterr().out
    assert "dankook-recruitment-999999: closed" in report
    assert f"deadline={deadline}" in report
    assert "checked=2026-11-11T12:00:00+09:00" in report
    assert {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in files} == before


@pytest.mark.parametrize("existing_batch", [False, True])
def test_failed_replacement_restores_previous_batch(tmp_path, capture, monkeypatch, existing_batch):
    input_file = tmp_path / "capture.json"
    output = tmp_path / "output"
    if existing_batch:
        write_json(input_file, [capture])
        normalize(input_file, output)
    before = {path.name: path.read_bytes() for path in output.glob("*.json")}

    updated_capture = {**capture, "checked_at": "2026-11-12T12:00:00+09:00"}
    write_json(input_file, [updated_capture])
    replace = Path.replace

    def fail_opportunities(source, target):
        if Path(target) == output / "opportunities.json":
            assert (output / "sources.json").read_bytes() != before.get("sources.json")
            raise PermissionError("output file is locked")
        return replace(source, target)

    monkeypatch.setattr(Path, "replace", fail_opportunities)
    with pytest.raises(PermissionError, match="output file is locked"):
        normalize(input_file, output)

    assert {path.name: path.read_bytes() for path in output.iterdir()} == before


def test_failed_restore_keeps_backup_path(tmp_path, capture, monkeypatch):
    input_file = tmp_path / "capture.json"
    output = tmp_path / "output"
    write_json(input_file, [capture])
    normalize(input_file, output)
    previous_sources = (output / "sources.json").read_bytes()
    write_json(input_file, [{**capture, "checked_at": "2026-11-12T12:00:00+09:00"}])
    replace = Path.replace

    def fail_write_and_restore(source, target):
        if source.name in {"opportunities.json", "sources.json.previous"}:
            raise PermissionError("output file is locked")
        return replace(source, target)

    monkeypatch.setattr(Path, "replace", fail_write_and_restore)
    with pytest.raises(OSError, match="Could not restore sources.json") as failure:
        normalize(input_file, output)

    backup, = output.glob("*/sources.json.previous")
    assert backup.read_bytes() == previous_sources
    assert str(backup.parent) in str(failure.value)


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"source_ids": ["unknown-source"]}, "unknown source reference"),
        ({"fields": ["unknown-field"]}, "unknown catalog field code"),
        ({"source_kind": "synthetic"}, "real and synthetic"),
    ],
)
def test_checker_rejects_invalid_cross_file_data(tmp_path, capture, changes, error):
    input_file = tmp_path / "capture.json"
    output = tmp_path / "output"
    write_json(input_file, [capture])
    normalize(input_file, output)
    path = output / "opportunities.json"
    item, = json.loads(path.read_text(encoding="utf-8"))
    write_json(path, [{**item, **changes}])

    with pytest.raises(ValueError, match=error):
        read_dataset(output)
