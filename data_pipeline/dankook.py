"""Convert manually verified notices from Dankook's recruitment board."""

import re
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode

from pydantic import AwareDatetime, BeforeValidator, Field, HttpUrl, StringConstraints, TypeAdapter, field_validator

from shared.models import ApplicationInfo, Evidence, LongText, Opportunity, Source, StrictModel, Text


BOARD_URL = "https://cms.dankook.ac.kr/ko/web/kor/apply_noti"
SOURCE_ID = "dankook-recruitment"
PostId = Annotated[str, StringConstraints(pattern=r"^[1-9][0-9]{0,19}$")]
DATE_PATTERN = r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
CapturedDate = Annotated[str, StringConstraints(strict=True, pattern=f"^{DATE_PATTERN}$")]


def require_timestamp_text(value: object) -> str:
    if not isinstance(value, str) or not re.search(r"(?:Z|[+-][0-9]{2}:?[0-9]{2})$", value):
        raise ValueError("use a timestamp with an explicit UTC offset")
    return value


CapturedTimestamp = Annotated[AwareDatetime, BeforeValidator(require_timestamp_text)]


class RecruitmentNotice(StrictModel):
    post_id: PostId
    subtype: Text | None = "contract"
    title: Text
    summary: LongText
    region: Text
    region_source_url: HttpUrl | None = None
    activities: list[Text] = Field(min_length=1, max_length=50)
    requirements: list[Text] = Field(min_length=1, max_length=50)
    experience_note: Text | None = None
    application: ApplicationInfo
    application_note: LongText
    # Keep the captured date string intact until the shared Opportunity validates it.
    published_on: CapturedDate
    checked_at: CapturedTimestamp

    @field_validator("application", mode="before")
    @classmethod
    def preserve_application_precision(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value

        for field in ("opens_on", "closes_on"):
            boundary = value.get(field)
            if boundary is not None and (
                not isinstance(boundary, str) or not re.fullmatch(DATE_PATTERN, boundary)
            ):
                raise ValueError(f"{field} requires YYYY-MM-DD without a time")
        for field in ("opens_at", "closes_at"):
            boundary = value.get(field)
            if boundary is not None:
                try:
                    require_timestamp_text(boundary)
                except ValueError as error:
                    raise ValueError(f"{field}: {error}") from error
        return value

    def to_opportunity(self) -> Opportunity:
        query = urlencode({
            "_dku_bbs_web_BbsPortlet_action": "view_message",
            "_dku_bbs_web_BbsPortlet_bbsMessageId": self.post_id,
            "p_p_id": "dku_bbs_web_BbsPortlet",
            "p_p_lifecycle": "0",
            "redirect": "/ko/web/kor/home",
        })
        url = f"{BOARD_URL}?{query}"
        evidence = [
            Evidence(id="duties", field="activities", fact=" / ".join(self.activities), source_url=url),
            Evidence(id="conditions", field="requirements", fact=" / ".join(self.requirements), source_url=url),
            Evidence(id="application", field="application", fact=self.application_note, source_url=url),
        ]
        if self.experience_note:
            evidence.append(Evidence(
                id="experience", field="experience_required", fact=self.experience_note, source_url=url,
            ))
        if self.region_source_url:
            evidence.append(Evidence(
                id="location", field="regions", fact=self.region, source_url=self.region_source_url,
            ))

        # The captured degree, disqualification and military-service conditions
        # have no equivalent in the shared rule expressions.
        return Opportunity(
            id=f"{SOURCE_ID}-{self.post_id}",
            type="job",
            subtype=self.subtype,
            title=self.title,
            organization="단국대학교",
            summary=self.summary,
            fields=[],
            regions=[self.region],
            activities=self.activities,
            requirements=self.requirements,
            requirements_coverage="partial",
            unresolved_conditions=self.requirements,
            experience_required=None,
            application=self.application,
            source_ids=[SOURCE_ID],
            source_url=url,
            source_kind="real",
            published_on=self.published_on,
            checked_at=self.checked_at,
            evidence=evidence,
        )


def load_dankook_batch(path: Path) -> tuple[Source, list[Opportunity]]:
    batch_type = Annotated[list[RecruitmentNotice], Field(min_length=1)]
    notices = TypeAdapter(batch_type).validate_json(path.read_text(encoding="utf-8"))
    source = Source(
        id=SOURCE_ID,
        name="단국대학교 채용공지",
        url=BOARD_URL,
        kind="school",
        source_kind="real",
        checked_at=max(notice.checked_at for notice in notices),
    )
    return source, [notice.to_opportunity() for notice in notices]
