from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class Experience(StrictModel):
    id: str = Field(min_length=1, max_length=100)
    kind: Literal["course_project", "contest", "club", "volunteer", "internship", "employment", "other"]
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    skills: list[str] = Field(default_factory=list, max_length=30)
    start_month: str | None = Field(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    end_month: str | None = Field(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")

class UserProfile(StrictModel):
    age: int | None = Field(default=None, ge=0, le=120)
    school_id: str | None = Field(default=None, max_length=100)
    school_name: str | None = Field(default=None, max_length=200)
    education_status: Literal["enrolled", "leave", "graduating", "graduated", "other", "unknown"] = "unknown"
    academic_year: int | None = Field(default=None, ge=1, le=8)
    major: str | None = Field(default=None, max_length=200)
    interests: list[str] = Field(default_factory=list, max_length=30)
    residence_region: str | None = Field(default=None, max_length=100)
    experience_status: Literal["none", "provided", "unknown"] = "unknown"
    experiences: list[Experience] = Field(default_factory=list, max_length=30)
    preferred_job_fields: list[str] = Field(default_factory=list, max_length=30)
    preferred_job_regions: list[str] = Field(default_factory=list, max_length=30)
    goal: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_profile(self):
        if not (self.major or any(x.strip() for x in self.interests) or any(x.strip() for x in self.preferred_job_fields) or self.goal):
            raise ValueError("전공·관심 분야·희망 직무·목표 중 하나가 필요합니다")
        if (self.experience_status == "provided") != bool(self.experiences):
            raise ValueError("활동 상태와 활동 목록이 일치해야 합니다")
        return self

class RecommendationRequest(StrictModel):
    profile: UserProfile
    allow_external_ai: bool = False
    types: list[Literal["contest", "competition", "job", "certification", "event", "training", "project", "notice"]] = Field(default_factory=list)
    limit: int = Field(default=8, ge=1, le=20)
