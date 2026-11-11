from __future__ import annotations
from datetime import date
from typing import Annotated, Generic, Literal, TypeVar
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
Id = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100, pattern=r'^[A-Za-z0-9][A-Za-z0-9_.:-]*$')]
Month = Annotated[str, StringConstraints(pattern=r'^\d{4}-(0[1-9]|1[0-2])$')]
Texts = Annotated[list[Text], Field(max_length=50)]
Ids = Annotated[list[Id], Field(max_length=100)]
OpportunityType = Literal['contest', 'competition', 'job', 'certification', 'event', 'training', 'project', 'notice']
EducationStatus = Literal['enrolled', 'leave', 'graduating', 'graduated', 'other', 'unknown']
SourceKind = Literal['real', 'synthetic']

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class Experience(StrictModel):
    id: Id
    kind: Literal['course_project', 'contest', 'club', 'volunteer', 'internship', 'employment', 'other']
    title: Text
    description: LongText | None = None
    skills: Texts = Field(default_factory=list)
    start_month: Month | None = None
    end_month: Month | None = None

    @model_validator(mode='after')
    def dates(self):
        if self.start_month and self.end_month and self.start_month > self.end_month:
            raise ValueError('start_month must precede end_month')
        return self

class UserProfile(StrictModel):
    age: Annotated[int, Field(strict=True, ge=0, le=120)] | None = None
    school_id: Id | None = None
    school_name: Text | None = None
    education_status: EducationStatus = 'unknown'
    academic_year: Annotated[int, Field(strict=True, ge=1, le=8)] | None = None
    major: Text | None = None
    interests: Texts = Field(default_factory=list)
    residence_region: Text | None = None
    experience_status: Literal['none', 'provided', 'unknown'] = 'unknown'
    experiences: list[Experience] = Field(default_factory=list, max_length=30)
    preferred_job_fields: Texts = Field(default_factory=list)
    preferred_job_regions: Texts = Field(default_factory=list)
    goal: LongText | None = None

    @model_validator(mode='after')
    def consistent(self):
        if not (self.major or self.interests or self.preferred_job_fields or self.goal):
            raise ValueError('전공·관심 분야·희망 직무·목표 중 하나가 필요합니다')
        if (self.experience_status == 'provided') != bool(self.experiences):
            raise ValueError('활동 상태와 활동 목록이 일치해야 합니다')
        if len({x.id for x in self.experiences}) != len(self.experiences):
            raise ValueError('duplicate experience IDs')
        return self

class Source(StrictModel):
    id: Id
    name: Text
    url: HttpUrl
    kind: Literal['official', 'school', 'aggregator', 'other']
    source_kind: SourceKind
    checked_at: AwareDatetime

class Evidence(StrictModel):
    id: Id
    field: Literal['fields', 'related_majors', 'activities', 'requirements', 'eligibility_rules', 'experience_required', 'application', 'certification', 'regions', 'event_schedule', 'summary']
    fact: LongText
    source_url: HttpUrl

class AgeRule(StrictModel):
    kind: Literal['age']
    operator: Literal['eq', 'gte', 'lte']
    value: int = Field(strict=True, ge=0, le=120)

class TextRule(StrictModel):
    kind: Literal['text']
    field: Literal['school_id', 'major', 'residence_region']
    operator: Literal['in', 'not_in']
    values: list[Text] = Field(min_length=1, max_length=50)

class EducationRule(StrictModel):
    kind: Literal['education']
    operator: Literal['in', 'not_in']
    values: list[EducationStatus] = Field(min_length=1, max_length=7)

class AllRule(StrictModel):
    kind: Literal['all']
    rules: list[RuleExpression] = Field(min_length=1, max_length=20)

class AnyRule(StrictModel):
    kind: Literal['any']
    rules: list[RuleExpression] = Field(min_length=1, max_length=20)

class ExceptionRule(StrictModel):
    kind: Literal['exception']
    base: RuleExpression
    alternatives: list[RuleExpression] = Field(min_length=1, max_length=20)

RuleExpression = Annotated[AgeRule | TextRule | EducationRule | AllRule | AnyRule | ExceptionRule, Field(discriminator='kind')]
AllRule.model_rebuild()
AnyRule.model_rebuild()
ExceptionRule.model_rebuild()

class EligibilityRule(StrictModel):
    id: Id
    summary: LongText
    expression: RuleExpression
    evidence_ids: list[Id] = Field(min_length=1, max_length=100)

class ApplicationInfo(StrictModel):
    status: Literal['open', 'upcoming', 'closed', 'unknown'] = 'unknown'
    opens_on: date | None = None
    closes_on: date | None = None
    opens_at: AwareDatetime | None = None
    closes_at: AwareDatetime | None = None

    @model_validator(mode='after')
    def boundaries(self):
        from zoneinfo import ZoneInfo
        tz = ZoneInfo('Asia/Seoul')
        if self.opens_on and self.opens_at or self.closes_on and self.closes_at:
            raise ValueError('use either date or timestamp for each boundary')
        start = self.opens_at.astimezone(tz).date() if self.opens_at else self.opens_on
        end = self.closes_at.astimezone(tz).date() if self.closes_at else self.closes_on
        if start and end and start > end:
            raise ValueError('opening must not follow closing')
        if self.opens_at and self.closes_at and self.opens_at >= self.closes_at:
            raise ValueError('opening timestamp must precede closing')
        return self

class ExamSession(StrictModel):
    id: Id
    name: Text
    application: ApplicationInfo
    exam_on: date | None = None
    schedule_note: LongText | None = None
    source_url: HttpUrl
    checked_at: AwareDatetime

class CertificationInfo(StrictModel):
    status: Literal['active', 'inactive', 'unknown'] = 'unknown'
    issuer: Text
    exam_sessions: list[ExamSession] = Field(default_factory=list, max_length=100)

    @model_validator(mode='after')
    def unique_sessions(self):
        if len({x.id for x in self.exam_sessions}) != len(self.exam_sessions):
            raise ValueError('duplicate exam session IDs')
        return self

class EventSchedule(StrictModel):
    starts_on: date | None = None
    ends_on: date | None = None
    note: LongText | None = None

    @model_validator(mode='after')
    def ordered(self):
        if self.starts_on and self.ends_on and self.starts_on > self.ends_on:
            raise ValueError('event start must precede end')
        return self

class Opportunity(StrictModel):
    id: Id
    type: OpportunityType
    subtype: Text | None = None
    title: Text
    organization: Text
    summary: LongText
    fields: Texts = Field(default_factory=list)
    related_majors: Texts = Field(default_factory=list)
    tags: Texts = Field(default_factory=list)
    regions: Texts = Field(default_factory=list)
    work_mode: Literal['onsite', 'remote', 'hybrid', 'unknown'] = 'unknown'
    activities: Texts = Field(default_factory=list)
    requirements: Texts = Field(default_factory=list)
    eligibility_rules: list[EligibilityRule] = Field(default_factory=list, max_length=50)
    requirements_coverage: Literal['complete', 'partial', 'unknown'] = 'unknown'
    unresolved_conditions: Texts = Field(default_factory=list)
    experience_required: Annotated[bool, Field(strict=True)] | None = None
    application: ApplicationInfo = Field(default_factory=ApplicationInfo)
    certification: CertificationInfo | None = None
    event_schedule: EventSchedule | None = None
    source_ids: list[Id] = Field(min_length=1, max_length=100)
    source_url: HttpUrl
    source_kind: SourceKind
    published_on: date | None = None
    published_at: AwareDatetime | None = None
    checked_at: AwareDatetime
    evidence: list[Evidence] = Field(default_factory=list, max_length=100)

    @model_validator(mode='after')
    def references(self):
        evidence_ids = {e.id for e in self.evidence}
        if len(evidence_ids) != len(self.evidence):
            raise ValueError('duplicate evidence IDs')
        if len({r.id for r in self.eligibility_rules}) != len(self.eligibility_rules):
            raise ValueError('duplicate eligibility rule IDs')
        if any(not set(r.evidence_ids) <= evidence_ids for r in self.eligibility_rules):
            raise ValueError('unknown eligibility evidence')
        if (self.type == 'certification') != (self.certification is not None):
            raise ValueError('certification info is required only for certifications')
        if self.type == 'certification' and self.application != ApplicationInfo():
            raise ValueError('use exam_sessions for certification applications')
        if self.published_on and self.published_at:
            raise ValueError('use published_on or published_at')
        if self.requirements_coverage == 'complete' and self.unresolved_conditions:
            raise ValueError('unresolved conditions cannot have complete coverage')
        if self.experience_required is not None and not any(e.field == 'experience_required' for e in self.evidence):
            raise ValueError('experience requirement needs explicit evidence')
        return self

class RoleProfile(StrictModel):
    id: Id
    name: Text
    tasks: Texts
    fields: Texts
    preparation_skills: Texts
    source_ids: list[Id] = Field(min_length=1, max_length=100)
    source_url: HttpUrl
    source_kind: SourceKind
    checked_at: AwareDatetime

class ResourceLink(StrictModel):
    id: Id
    name: Text
    kind: Literal['official_site', 'job_board', 'mentoring_program']
    description: LongText
    url: HttpUrl
    source_ids: list[Id] = Field(min_length=1, max_length=100)
    source_kind: SourceKind
    checked_at: AwareDatetime

class RecommendationRequest(StrictModel):
    profile: UserProfile
    types: list[OpportunityType] = Field(default_factory=list, max_length=8)
    limit: int = Field(default=8, strict=True, ge=1, le=20)
    allow_external_ai: bool = False

class RecommendationReason(StrictModel):
    text: LongText
    evidence_ids: list[Id] = Field(min_length=1, max_length=100)

class RecommendationItem(StrictModel):
    opportunity_id: Id
    relevance_score: int = Field(strict=True, ge=0, le=100)
    eligibility: Literal['eligible', 'ineligible', 'unknown']
    reasons: list[RecommendationReason] = Field(min_length=1, max_length=20)
    cautions: Texts = Field(default_factory=list)
    explanation_source: Literal['template', 'llm']

class RecommendationResponse(StrictModel):
    items: list[RecommendationItem] = Field(max_length=20)
    candidate_count: int = Field(strict=True, ge=0)
    engine: Literal['rules', 'rules+llm']
    warnings: Texts = Field(default_factory=list)

    @model_validator(mode='after')
    def consistent(self):
        if self.candidate_count < len(self.items):
            raise ValueError('candidate_count smaller than returned items')
        if len({x.opportunity_id for x in self.items}) != len(self.items):
            raise ValueError('duplicate recommendation IDs')
        if (self.engine == 'rules+llm') != any(x.explanation_source == 'llm' for x in self.items):
            raise ValueError('engine must reflect actual explanation source')
        if any(x.eligibility == 'ineligible' for x in self.items):
            raise ValueError('ineligible items cannot be recommended')
        return self

class RecommendationApiItem(StrictModel):
    recommendation: RecommendationItem
    opportunity: Opportunity

    @model_validator(mode='after')
    def references(self):
        if self.recommendation.opportunity_id != self.opportunity.id:
            raise ValueError('opportunity ID mismatch')
        ids = {x.id for x in self.opportunity.evidence}
        if any(not set(r.evidence_ids) <= ids for r in self.recommendation.reasons):
            raise ValueError('unknown recommendation evidence')
        return self

class RecommendationApiResponse(StrictModel):
    items: list[RecommendationApiItem] = Field(max_length=20)
    candidate_count: int = Field(strict=True, ge=0)
    engine: Literal['rules', 'rules+llm']
    warnings: Texts = Field(default_factory=list)

    @model_validator(mode='after')
    def consistent(self):
        RecommendationResponse(items=[x.recommendation for x in self.items], candidate_count=self.candidate_count, engine=self.engine, warnings=self.warnings)
        return self

class RoleAdviceRequest(StrictModel):
    profile: UserProfile
    limit: int = Field(default=5, strict=True, ge=1, le=20)
    allow_external_ai: bool = False

class RoleAdviceItem(StrictModel):
    role_id: Id
    explanation: LongText
    source_ids: list[Id] = Field(min_length=1, max_length=100)

class RoleAdviceResponse(StrictModel):
    items: list[RoleAdviceItem] = Field(max_length=20)
    warnings: Texts = Field(default_factory=list)

class ActivityPlanRequest(StrictModel):
    profile: UserProfile
    role_ids: Ids = Field(default_factory=list)
    opportunity_ids: Ids = Field(default_factory=list)
    allow_external_ai: bool = False

class PlanStep(StrictModel):
    title: Text
    description: LongText
    kind: Literal['general_preparation', 'opportunity']
    opportunity_id: Id | None = None

    @model_validator(mode='after')
    def link(self):
        if (self.kind == 'opportunity') != (self.opportunity_id is not None):
            raise ValueError('only opportunity steps need an opportunity ID')
        return self

class ActivityPlanResponse(StrictModel):
    steps: list[PlanStep] = Field(max_length=20)
    warnings: Texts = Field(default_factory=list)

class InterviewGuideRequest(ActivityPlanRequest):
    experience_ids: Ids = Field(default_factory=list)

    @model_validator(mode='after')
    def references(self):
        if not set(self.experience_ids) <= {x.id for x in self.profile.experiences}:
            raise ValueError('unknown user experience')
        return self

class PracticeQuestion(StrictModel):
    question: LongText
    preparation_tip: LongText
    experience_ids: Ids = Field(default_factory=list)
    kind: Literal['practice'] = 'practice'

class InterviewGuideResponse(StrictModel):
    questions: list[PracticeQuestion] = Field(max_length=20)
    warnings: Texts = Field(default_factory=list)

T = TypeVar('T')
class Page(StrictModel, Generic[T]):
    items: list[T]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)

class ErrorDetail(StrictModel):
    field: Text
    message: Text

class ErrorBody(StrictModel):
    code: Text
    message: Text
    details: list[ErrorDetail] = Field(default_factory=list)

class ErrorResponse(StrictModel):
    error: ErrorBody

class HealthResponse(StrictModel):
    status: Literal['ok']
    contract_version: Text

class Capability(StrictModel):
    enabled: bool
    implemented: bool
    unavailable_reason: Text | None = None

class FieldOption(StrictModel):
    code: Id
    label: Text
    aliases: Texts = Field(default_factory=list)

class OptionsResponse(StrictModel):
    status: Literal['draft', 'approved']
    opportunity_types: list[OpportunityType]
    education_statuses: list[EducationStatus]
    experience_statuses: list[Literal['none', 'provided', 'unknown']]
    fields: list[FieldOption]
