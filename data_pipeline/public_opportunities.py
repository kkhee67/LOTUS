"""Normalize an official Job-ALIO listing snapshot and curated organizer notices."""

from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, HttpUrl, StringConstraints, TypeAdapter

from data_pipeline.dankook import CapturedTimestamp
from data_pipeline.json_input import read_unique_json
from shared.models import (
    ApplicationInfo, CertificationInfo, DateOnly, EventSchedule, Evidence, ExamSession, Id,
    LongText, Opportunity, OpportunityType, Source, StrictModel, Text, Texts,
)


ALIO_ID = "job-alio"
ALIO_LIST = "https://job.alio.go.kr/recruit.do"


class AlioListing(StrictModel):
    post_id: Annotated[str, StringConstraints(pattern=r"^[1-9][0-9]{0,19}$")]
    title: Text
    organization: Text
    regions: Texts
    employment: Text
    published_on: DateOnly
    closes_on: DateOnly
    closes_at: CapturedTimestamp | None = None
    status: Literal["open", "closed"] = "open"
    checked_at: CapturedTimestamp
    details_summary: LongText | None = None
    requirements: Texts = Field(default_factory=list)
    related_majors: Texts = Field(default_factory=list)

    def to_opportunity(self) -> Opportunity:
        url = f"https://job.alio.go.kr/recruitview.do?idx={self.post_id}"
        summary = self.details_summary or (
            f"{self.organization} 채용 공고입니다. 고용형태: {self.employment}. 지원 자격과 정확한 마감 시각은 원문에서 확인하세요."
        )
        deadline = self.closes_at or self.closes_on
        deadline_label = "공식 상세 공고의 접수 마감 시각" if self.closes_at else "공식 목록의 접수 마감일"
        evidence = [
            Evidence(id="listing", field="summary", fact=f"공식 채용 목록 제목: {self.title} / 고용형태: {self.employment}", source_url=url),
            Evidence(id="deadline", field="application", fact=f"{deadline_label}: {deadline.isoformat()}", source_url=url),
        ]
        if self.details_summary:
            evidence.append(Evidence(id="details", field="summary", fact=self.details_summary, source_url=url))
        details = {}
        if self.requirements:
            evidence.append(Evidence(id="requirements", field="requirements", fact=" / ".join(self.requirements), source_url=url))
            details.update(requirements=self.requirements, unresolved_conditions=self.requirements, requirements_coverage="partial")
        if self.related_majors:
            evidence.append(Evidence(id="related_majors", field="related_majors", fact=" / ".join(self.related_majors), source_url=url))
            details["related_majors"] = self.related_majors
        return Opportunity(
            id=f"{ALIO_ID}-{self.post_id}",
            type="job",
            subtype="internship" if self.employment in {"청년인턴(체험형)", "청년인턴(채용형)"} else None,
            title=self.title,
            organization=self.organization,
            summary=summary,
            regions=self.regions,
            application=ApplicationInfo(
                status=self.status, **({"closes_at": self.closes_at} if self.closes_at else {"closes_on": self.closes_on})
            ),
            published_on=self.published_on,
            checked_at=self.checked_at,
            source_ids=[ALIO_ID],
            source_url=url,
            source_kind="real",
            evidence=evidence,
            **details,
        )


class CapturedApplication(ApplicationInfo):
    opens_at: CapturedTimestamp | None = None
    closes_at: CapturedTimestamp | None = None


class CapturedExamSession(ExamSession):
    application: CapturedApplication
    checked_at: CapturedTimestamp


class CapturedCertification(CertificationInfo):
    exam_sessions: list[CapturedExamSession] = Field(default_factory=list, max_length=100)


class OrganizerNotice(StrictModel):
    id: Id
    type: OpportunityType
    subtype: Text | None = None
    organization: Text
    title: Text
    source_url: HttpUrl
    publisher: Text | None = None
    source_type: Literal["official", "school"] = "official"
    summary: LongText
    activities: Texts
    requirements: Texts = Field(default_factory=list)
    fields: Texts = Field(default_factory=list)
    related_majors: Texts = Field(default_factory=list)
    tags: Texts = Field(default_factory=list)
    published_on: DateOnly | None = None
    application: CapturedApplication = Field(default_factory=CapturedApplication)
    event_schedule: EventSchedule | None = None
    certification: CapturedCertification | None = None
    checked_at: CapturedTimestamp

    def to_opportunity(self) -> Opportunity:
        facts = {
            "activities": " / ".join(self.activities),
            "application": self.application.model_dump_json(exclude_none=True) if self.type != "certification" else "",
            "requirements": " / ".join(self.requirements),
            "related_majors": " / ".join(self.related_majors),
            "event_schedule": self.event_schedule.model_dump_json(exclude_none=True) if self.event_schedule else "",
            "certification": self.certification.issuer if self.certification else "",
        }
        evidence = [
            Evidence(id=field, field=field, fact=fact, source_url=self.source_url)
            for field, fact in facts.items() if fact
        ]
        excluded = {"publisher", "source_type"}
        excluded.update(name for name in ("related_majors", "tags") if name not in self.model_fields_set)
        return Opportunity(
            **self.model_dump(exclude=excluded),
            requirements_coverage="partial" if self.requirements else "unknown",
            unresolved_conditions=self.requirements,
            source_ids=[self.id],
            source_kind="real",
            evidence=evidence,
        )


def load_public_batch(alio_path: Path, organizer_path: Path) -> tuple[list[Source], list[Opportunity]]:
    listings = TypeAdapter(list[AlioListing]).validate_python(read_unique_json(alio_path))
    notices = TypeAdapter(list[OrganizerNotice]).validate_python(read_unique_json(organizer_path))
    sources = [
        Source(id=notice.id, name=notice.publisher or notice.organization, url=notice.source_url, kind=notice.source_type,
               source_kind="real", checked_at=notice.checked_at)
        for notice in notices
    ]
    opportunities = [notice.to_opportunity() for notice in notices]
    if listings:
        sources.append(Source(id=ALIO_ID, name="공공기관 채용정보시스템 잡알리오", url=ALIO_LIST,
                              kind="official", source_kind="real", checked_at=max(row.checked_at for row in listings)))
        opportunities.extend(row.to_opportunity() for row in listings)
    return sources, opportunities
