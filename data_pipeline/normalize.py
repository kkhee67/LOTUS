"""Validate or update the four real-data JSON arrays from a local capture."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import TypeAdapter

from data_pipeline.dankook import load_dankook_batch
from data_pipeline.json_input import read_unique_json
from data_pipeline.public_opportunities import load_public_batch
from shared.models import Opportunity, ResourceLink, RoleProfile, Source
from shared.rules import SEOUL, application_state
from shared.validation import validate_dataset


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data/normalized"
EXPANDED_OUTPUT = DEFAULT_OUTPUT / "expanded"
CURRENT_OUTPUT = DEFAULT_OUTPUT / "current"
MODELS = {
    "sources": Source,
    "opportunities": Opportunity,
    "roles": RoleProfile,
    "resource_links": ResourceLink,
}


def validate_real_dataset(dataset):
    validate_dataset(**dataset)
    if any(item.source_kind != "real" for group in dataset.values() for item in group):
        raise ValueError("normalized data must have source_kind=real")


def read_dataset(directory: Path, *, allow_missing: bool = False):
    dataset = {}
    for name, model in MODELS.items():
        path = directory / f"{name}.json"
        try:
            dataset[name] = TypeAdapter(list[model]).validate_python(read_unique_json(path))
        except FileNotFoundError:
            if not allow_missing:
                raise
            dataset[name] = []
    validate_real_dataset(dataset)
    return dataset


def write_dataset(dataset, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    temporary = TemporaryDirectory(dir=output, delete=False, ignore_cleanup_errors=True)
    staging = Path(temporary.name)
    keep_backups = False
    try:
        replacements = []
        for name, records in dataset.items():
            target = output / f"{name}.json"
            rows = [record.model_dump(mode="json", exclude_unset=True) for record in records]
            content = (json.dumps(rows, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            try:
                previous = target.read_bytes()
            except FileNotFoundError:
                previous = None
            if previous == content:
                continue

            staged = staging / target.name
            staged.write_bytes(content)
            backup = None
            if previous is not None:
                backup = staging / f"{target.name}.previous"
                backup.write_bytes(previous)
            replacements.append((staged, target, backup))

        applied = []
        try:
            for staged, target, backup in replacements:
                staged.replace(target)
                applied.append((target, backup))
        except OSError as write_error:
            restore_failures = []
            for target, backup in reversed(applied):
                try:
                    if backup is None:
                        target.unlink()
                    else:
                        backup.replace(target)
                except OSError as restore_error:
                    restore_failures.append(f"{target.name}: {restore_error}")
            if restore_failures:
                keep_backups = True
                errors = ", ".join(restore_failures)
                raise OSError(
                    f"{write_error}. Could not restore {errors}. Recovery files are in {staging}"
                ) from write_error
            raise
    finally:
        if not keep_backups:
            temporary.cleanup()


def normalize(capture: Path, output: Path, *, public_batch: tuple[Path, Path] | None = None):
    source, opportunities = load_dankook_batch(capture)
    incoming = {"sources": [source], "opportunities": opportunities, "roles": [], "resource_links": []}
    if public_batch is not None:
        public_sources, public_opportunities = load_public_batch(*public_batch)
        incoming["sources"].extend(public_sources)
        incoming["opportunities"].extend(public_opportunities)
        supplement = public_batch[1].with_name("nonjob_snapshot.json")
        if supplement.is_file():
            rows = read_unique_json(supplement)
            for table in ("opportunities", "sources"):
                incoming[table].extend(TypeAdapter(list[MODELS[table]]).validate_python(rows[table]))
    validate_real_dataset(incoming)
    dataset = read_dataset(output, allow_missing=True)

    for name, records in incoming.items():
        by_id = {record.id: record for record in dataset[name]}
        for record in records:
            previous = by_id.get(record.id)
            if previous is None or record.checked_at >= previous.checked_at:
                by_id[record.id] = record
        dataset[name] = list(by_id.values())

    validate_real_dataset(dataset)
    write_dataset(dataset, output)
    return dataset


def parse_as_of(value: str) -> datetime:
    try:
        now = datetime.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("use an ISO 8601 date and time with a UTC offset") from error
    if now.utcoffset() is None:
        raise argparse.ArgumentTypeError("use an explicit UTC offset, for example +09:00")
    return now


def export_current(dataset, output: Path, *, now: datetime):
    today = now.astimezone(SEOUL).date()

    def is_current(item):
        if item.certification:
            return item.certification.status == "active"
        status = application_state(item.application, now=now).status
        if status != "unknown":
            return status in {"open", "upcoming"}
        if item.type == "notice" and item.subtype == "policy_guide":
            return True
        schedule = item.event_schedule
        return item.type == "event" and schedule and schedule.ends_on and schedule.ends_on >= today

    opportunities = [item for item in dataset["opportunities"] if is_current(item)]
    source_ids = {
        source_id
        for item in (*opportunities, *dataset["roles"], *dataset["resource_links"])
        for source_id in item.source_ids
    }
    current = {
        **dataset,
        "sources": [source for source in dataset["sources"] if source.id in source_ids],
        "opportunities": opportunities,
    }
    validate_real_dataset(current)
    write_dataset(current, output)
    return current


def print_job_statuses(opportunities: list[Opportunity], now: datetime) -> None:
    print("Recruitment application states at", now.isoformat())
    for opportunity in opportunities:
        if opportunity.type != "job":
            continue
        application = opportunity.application
        state = application_state(application, now=now)
        closing = application.closes_at or application.closes_on
        deadline = closing.isoformat() if closing else "unlisted"
        print(
            f"{opportunity.id}: {state.status} | deadline={deadline} | "
            f"checked={opportunity.checked_at.isoformat()}"
        )
        for caution in state.cautions:
            print(f"  {caution}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/raw/dankook_recruitment.json")
    parser.add_argument("--output", type=Path, help="Override the default or expanded output directory.")
    parser.add_argument("--include-public", action="store_true",
                        help="Use the expanded batch with local Job-ALIO and organizer snapshots.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--validate-only", action="store_true", help="Check all four arrays without writing.")
    mode.add_argument("--as-of", type=parse_as_of, help="Check arrays and report job application states without writing.")
    mode.add_argument("--current-as-of", type=parse_as_of,
                      help="Export open and upcoming opportunities and active certifications from the expanded batch.")
    args = parser.parse_args()
    default_output = CURRENT_OUTPUT if args.current_as_of else EXPANDED_OUTPUT if args.include_public else DEFAULT_OUTPUT
    output = args.output if args.output is not None else default_output
    try:
        if args.validate_only or args.as_of is not None:
            dataset = read_dataset(output)
        elif args.current_as_of is not None:
            if output.resolve() in {DEFAULT_OUTPUT.resolve(), EXPANDED_OUTPUT.resolve()}:
                parser.error("use an output directory separate from the full dataset")
            dataset = export_current(read_dataset(EXPANDED_OUTPUT), output, now=args.current_as_of)
        else:
            public_batch = (
                ROOT / "data/raw/job_alio.json",
                ROOT / "data/raw/organizer_notices.json",
            ) if args.include_public else None
            dataset = normalize(args.input, output, public_batch=public_batch)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Dataset validation or update failed: {error}\n")
    print("Real dataset validated:", {name: len(records) for name, records in dataset.items()})
    if args.as_of is not None:
        print_job_statuses(dataset["opportunities"], args.as_of)


if __name__ == "__main__":
    main()
