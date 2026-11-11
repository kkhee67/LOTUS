# 공통 필드 명세 (자동 생성)

`python -m scripts.export_contracts`로 갱신한다. 타입·길이·범위·null·기본값은 아래 JSON Schema 조각을 따른다.
교차 필드 검증과 의미는 CONTRACT.md 및 shared/models를 함께 읽는다.

## ActivityPlanRequest

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| profile | 예 | `{"$ref": "#/$defs/UserProfile"}` |
| role_ids | 아니요 | `{"items": {"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}, "maxItems": 100, "type": "array"}` |
| opportunity_ids | 아니요 | `{"items": {"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}, "maxItems": 100, "type": "array"}` |
| allow_external_ai | 아니요 | `{"default": false, "type": "boolean"}` |

## ActivityPlanResponse

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| steps | 예 | `{"items": {"$ref": "#/$defs/PlanStep"}, "maxItems": 20, "type": "array"}` |
| warnings | 아니요 | `{"items": {"maxLength": 200, "minLength": 1, "type": "string"}, "maxItems": 50, "type": "array"}` |

## AgeRule

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| kind | 예 | `{"const": "age", "type": "string"}` |
| operator | 예 | `{"enum": ["eq", "gte", "lte"], "type": "string"}` |
| value | 예 | `{"maximum": 120, "minimum": 0, "type": "integer"}` |

## AllRule

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|

## AnyRule

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|

## ApplicationInfo

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| status | 아니요 | `{"default": "unknown", "enum": ["open", "upcoming", "closed", "unknown"], "type": "string"}` |
| opens_on | 아니요 | `{"anyOf": [{"format": "date", "type": "string"}, {"type": "null"}], "default": null}` |
| closes_on | 아니요 | `{"anyOf": [{"format": "date", "type": "string"}, {"type": "null"}], "default": null}` |
| opens_at | 아니요 | `{"anyOf": [{"format": "date-time", "type": "string"}, {"type": "null"}], "default": null}` |
| closes_at | 아니요 | `{"anyOf": [{"format": "date-time", "type": "string"}, {"type": "null"}], "default": null}` |

## Capability

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| enabled | 예 | `{"type": "boolean"}` |
| implemented | 예 | `{"type": "boolean"}` |
| unavailable_reason | 아니요 | `{"anyOf": [{"maxLength": 200, "minLength": 1, "type": "string"}, {"type": "null"}], "default": null}` |

## CertificationInfo

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| status | 아니요 | `{"default": "unknown", "enum": ["active", "inactive", "unknown"], "type": "string"}` |
| issuer | 예 | `{"maxLength": 200, "minLength": 1, "type": "string"}` |
| exam_sessions | 아니요 | `{"items": {"$ref": "#/$defs/ExamSession"}, "maxItems": 100, "type": "array"}` |

## EducationRule

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| kind | 예 | `{"const": "education", "type": "string"}` |
| operator | 예 | `{"enum": ["in", "not_in"], "type": "string"}` |
| values | 예 | `{"items": {"enum": ["enrolled", "leave", "graduating", "graduated", "other", "unknown"], "type": "string"}, "maxItems": 7, "minItems": 1, "type": "array"}` |

## EligibilityRule

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| id | 예 | `{"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}` |
| summary | 예 | `{"maxLength": 4000, "minLength": 1, "type": "string"}` |
| expression | 예 | `{"discriminator": {"mapping": {"age": "#/$defs/AgeRule", "all": "#/$defs/AllRule", "any": "#/$defs/AnyRule", "education": "#/$defs/EducationRule", "exception": "#/$defs/ExceptionRule", "text": "#/$defs/TextRule"}, "propertyName": "kind"}, "oneOf": [{"$ref": "#/$defs/AgeRule"}, {"$ref": "#/$defs/TextRule"}, {"$ref": "#/$defs/EducationRule"}, {"$ref": "#/$defs/AllRule"}, {"$ref": "#/$defs/AnyRule"}, {"$ref": "#/$defs/ExceptionRule"}]}` |
| evidence_ids | 예 | `{"items": {"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}, "maxItems": 100, "minItems": 1, "type": "array"}` |

## ErrorBody

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| code | 예 | `{"maxLength": 200, "minLength": 1, "type": "string"}` |
| message | 예 | `{"maxLength": 200, "minLength": 1, "type": "string"}` |
| details | 아니요 | `{"items": {"$ref": "#/$defs/ErrorDetail"}, "type": "array"}` |

## ErrorDetail

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| field | 예 | `{"maxLength": 200, "minLength": 1, "type": "string"}` |
| message | 예 | `{"maxLength": 200, "minLength": 1, "type": "string"}` |

## ErrorResponse

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| error | 예 | `{"$ref": "#/$defs/ErrorBody"}` |

## EventSchedule

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| starts_on | 아니요 | `{"anyOf": [{"format": "date", "type": "string"}, {"type": "null"}], "default": null}` |
| ends_on | 아니요 | `{"anyOf": [{"format": "date", "type": "string"}, {"type": "null"}], "default": null}` |
| note | 아니요 | `{"anyOf": [{"maxLength": 4000, "minLength": 1, "type": "string"}, {"type": "null"}], "default": null}` |

## Evidence

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| id | 예 | `{"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}` |
| field | 예 | `{"enum": ["fields", "related_majors", "activities", "requirements", "eligibility_rules", "experience_required", "application", "certification", "regions", "event_schedule", "summary"], "type": "string"}` |
| fact | 예 | `{"maxLength": 4000, "minLength": 1, "type": "string"}` |
| source_url | 예 | `{"format": "uri", "maxLength": 2083, "minLength": 1, "type": "string"}` |

## ExamSession

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| id | 예 | `{"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}` |
| name | 예 | `{"maxLength": 200, "minLength": 1, "type": "string"}` |
| application | 예 | `{"$ref": "#/$defs/ApplicationInfo"}` |
| exam_on | 아니요 | `{"anyOf": [{"format": "date", "type": "string"}, {"type": "null"}], "default": null}` |
| schedule_note | 아니요 | `{"anyOf": [{"maxLength": 4000, "minLength": 1, "type": "string"}, {"type": "null"}], "default": null}` |
| source_url | 예 | `{"format": "uri", "maxLength": 2083, "minLength": 1, "type": "string"}` |
| checked_at | 예 | `{"format": "date-time", "type": "string"}` |

## ExceptionRule

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|

## Experience

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| id | 예 | `{"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}` |
| kind | 예 | `{"enum": ["course_project", "contest", "club", "volunteer", "internship", "employment", "other"], "type": "string"}` |
| title | 예 | `{"maxLength": 200, "minLength": 1, "type": "string"}` |
| description | 아니요 | `{"anyOf": [{"maxLength": 4000, "minLength": 1, "type": "string"}, {"type": "null"}], "default": null}` |
| skills | 아니요 | `{"items": {"maxLength": 200, "minLength": 1, "type": "string"}, "maxItems": 50, "type": "array"}` |
| start_month | 아니요 | `{"anyOf": [{"pattern": "^\\d{4}-(0[1-9]&#124;1[0-2])$", "type": "string"}, {"type": "null"}], "default": null}` |
| end_month | 아니요 | `{"anyOf": [{"pattern": "^\\d{4}-(0[1-9]&#124;1[0-2])$", "type": "string"}, {"type": "null"}], "default": null}` |

## FieldOption

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| code | 예 | `{"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}` |
| label | 예 | `{"maxLength": 200, "minLength": 1, "type": "string"}` |
| aliases | 아니요 | `{"items": {"maxLength": 200, "minLength": 1, "type": "string"}, "maxItems": 50, "type": "array"}` |

## HealthResponse

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| status | 예 | `{"const": "ok", "type": "string"}` |
| contract_version | 예 | `{"maxLength": 200, "minLength": 1, "type": "string"}` |

## InterviewGuideRequest

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| profile | 예 | `{"$ref": "#/$defs/UserProfile"}` |
| role_ids | 아니요 | `{"items": {"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}, "maxItems": 100, "type": "array"}` |
| opportunity_ids | 아니요 | `{"items": {"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}, "maxItems": 100, "type": "array"}` |
| allow_external_ai | 아니요 | `{"default": false, "type": "boolean"}` |
| experience_ids | 아니요 | `{"items": {"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}, "maxItems": 100, "type": "array"}` |

## InterviewGuideResponse

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| questions | 예 | `{"items": {"$ref": "#/$defs/PracticeQuestion"}, "maxItems": 20, "type": "array"}` |
| warnings | 아니요 | `{"items": {"maxLength": 200, "minLength": 1, "type": "string"}, "maxItems": 50, "type": "array"}` |

## Opportunity

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| id | 예 | `{"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}` |
| type | 예 | `{"enum": ["contest", "competition", "job", "certification", "event", "training", "project", "notice"], "type": "string"}` |
| subtype | 아니요 | `{"anyOf": [{"maxLength": 200, "minLength": 1, "type": "string"}, {"type": "null"}], "default": null}` |
| title | 예 | `{"maxLength": 200, "minLength": 1, "type": "string"}` |
| organization | 예 | `{"maxLength": 200, "minLength": 1, "type": "string"}` |
| summary | 예 | `{"maxLength": 4000, "minLength": 1, "type": "string"}` |
| fields | 아니요 | `{"items": {"maxLength": 200, "minLength": 1, "type": "string"}, "maxItems": 50, "type": "array"}` |
| related_majors | 아니요 | `{"items": {"maxLength": 200, "minLength": 1, "type": "string"}, "maxItems": 50, "type": "array"}` |
| tags | 아니요 | `{"items": {"maxLength": 200, "minLength": 1, "type": "string"}, "maxItems": 50, "type": "array"}` |
| regions | 아니요 | `{"items": {"maxLength": 200, "minLength": 1, "type": "string"}, "maxItems": 50, "type": "array"}` |
| work_mode | 아니요 | `{"default": "unknown", "enum": ["onsite", "remote", "hybrid", "unknown"], "type": "string"}` |
| activities | 아니요 | `{"items": {"maxLength": 200, "minLength": 1, "type": "string"}, "maxItems": 50, "type": "array"}` |
| requirements | 아니요 | `{"items": {"maxLength": 200, "minLength": 1, "type": "string"}, "maxItems": 50, "type": "array"}` |
| eligibility_rules | 아니요 | `{"items": {"$ref": "#/$defs/EligibilityRule"}, "maxItems": 50, "type": "array"}` |
| requirements_coverage | 아니요 | `{"default": "unknown", "enum": ["complete", "partial", "unknown"], "type": "string"}` |
| unresolved_conditions | 아니요 | `{"items": {"maxLength": 200, "minLength": 1, "type": "string"}, "maxItems": 50, "type": "array"}` |
| experience_required | 아니요 | `{"anyOf": [{"type": "boolean"}, {"type": "null"}], "default": null}` |
| application | 아니요 | `{"$ref": "#/$defs/ApplicationInfo"}` |
| certification | 아니요 | `{"anyOf": [{"$ref": "#/$defs/CertificationInfo"}, {"type": "null"}], "default": null}` |
| event_schedule | 아니요 | `{"anyOf": [{"$ref": "#/$defs/EventSchedule"}, {"type": "null"}], "default": null}` |
| source_ids | 예 | `{"items": {"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}, "maxItems": 100, "minItems": 1, "type": "array"}` |
| source_url | 예 | `{"format": "uri", "maxLength": 2083, "minLength": 1, "type": "string"}` |
| source_kind | 예 | `{"enum": ["real", "synthetic"], "type": "string"}` |
| published_on | 아니요 | `{"anyOf": [{"format": "date", "type": "string"}, {"type": "null"}], "default": null}` |
| published_at | 아니요 | `{"anyOf": [{"format": "date-time", "type": "string"}, {"type": "null"}], "default": null}` |
| checked_at | 예 | `{"format": "date-time", "type": "string"}` |
| evidence | 아니요 | `{"items": {"$ref": "#/$defs/Evidence"}, "maxItems": 100, "type": "array"}` |

## OptionsResponse

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| status | 예 | `{"enum": ["draft", "approved"], "type": "string"}` |
| opportunity_types | 예 | `{"items": {"enum": ["contest", "competition", "job", "certification", "event", "training", "project", "notice"], "type": "string"}, "type": "array"}` |
| education_statuses | 예 | `{"items": {"enum": ["enrolled", "leave", "graduating", "graduated", "other", "unknown"], "type": "string"}, "type": "array"}` |
| experience_statuses | 예 | `{"items": {"enum": ["none", "provided", "unknown"], "type": "string"}, "type": "array"}` |
| fields | 예 | `{"items": {"$ref": "#/$defs/FieldOption"}, "type": "array"}` |

## PlanStep

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| title | 예 | `{"maxLength": 200, "minLength": 1, "type": "string"}` |
| description | 예 | `{"maxLength": 4000, "minLength": 1, "type": "string"}` |
| kind | 예 | `{"enum": ["general_preparation", "opportunity"], "type": "string"}` |
| opportunity_id | 아니요 | `{"anyOf": [{"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}, {"type": "null"}], "default": null}` |

## PracticeQuestion

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| question | 예 | `{"maxLength": 4000, "minLength": 1, "type": "string"}` |
| preparation_tip | 예 | `{"maxLength": 4000, "minLength": 1, "type": "string"}` |
| experience_ids | 아니요 | `{"items": {"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}, "maxItems": 100, "type": "array"}` |
| kind | 아니요 | `{"const": "practice", "default": "practice", "type": "string"}` |

## RecommendationApiItem

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| recommendation | 예 | `{"$ref": "#/$defs/RecommendationItem"}` |
| opportunity | 예 | `{"$ref": "#/$defs/Opportunity"}` |

## RecommendationApiResponse

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| items | 예 | `{"items": {"$ref": "#/$defs/RecommendationApiItem"}, "maxItems": 20, "type": "array"}` |
| candidate_count | 예 | `{"minimum": 0, "type": "integer"}` |
| engine | 예 | `{"enum": ["rules", "rules+llm"], "type": "string"}` |
| warnings | 아니요 | `{"items": {"maxLength": 200, "minLength": 1, "type": "string"}, "maxItems": 50, "type": "array"}` |

## RecommendationItem

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| opportunity_id | 예 | `{"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}` |
| relevance_score | 예 | `{"maximum": 100, "minimum": 0, "type": "integer"}` |
| eligibility | 예 | `{"enum": ["eligible", "ineligible", "unknown"], "type": "string"}` |
| reasons | 예 | `{"items": {"$ref": "#/$defs/RecommendationReason"}, "maxItems": 20, "minItems": 1, "type": "array"}` |
| cautions | 아니요 | `{"items": {"maxLength": 200, "minLength": 1, "type": "string"}, "maxItems": 50, "type": "array"}` |
| explanation_source | 예 | `{"enum": ["template", "llm"], "type": "string"}` |

## RecommendationReason

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| text | 예 | `{"maxLength": 4000, "minLength": 1, "type": "string"}` |
| evidence_ids | 예 | `{"items": {"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}, "maxItems": 100, "minItems": 1, "type": "array"}` |

## RecommendationRequest

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| profile | 예 | `{"$ref": "#/$defs/UserProfile"}` |
| types | 아니요 | `{"items": {"enum": ["contest", "competition", "job", "certification", "event", "training", "project", "notice"], "type": "string"}, "maxItems": 8, "type": "array"}` |
| limit | 아니요 | `{"default": 8, "maximum": 20, "minimum": 1, "type": "integer"}` |
| allow_external_ai | 아니요 | `{"default": false, "type": "boolean"}` |

## RecommendationResponse

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| items | 예 | `{"items": {"$ref": "#/$defs/RecommendationItem"}, "maxItems": 20, "type": "array"}` |
| candidate_count | 예 | `{"minimum": 0, "type": "integer"}` |
| engine | 예 | `{"enum": ["rules", "rules+llm"], "type": "string"}` |
| warnings | 아니요 | `{"items": {"maxLength": 200, "minLength": 1, "type": "string"}, "maxItems": 50, "type": "array"}` |

## ResourceLink

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| id | 예 | `{"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}` |
| name | 예 | `{"maxLength": 200, "minLength": 1, "type": "string"}` |
| kind | 예 | `{"enum": ["official_site", "job_board", "mentoring_program"], "type": "string"}` |
| description | 예 | `{"maxLength": 4000, "minLength": 1, "type": "string"}` |
| url | 예 | `{"format": "uri", "maxLength": 2083, "minLength": 1, "type": "string"}` |
| source_ids | 예 | `{"items": {"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}, "maxItems": 100, "minItems": 1, "type": "array"}` |
| source_kind | 예 | `{"enum": ["real", "synthetic"], "type": "string"}` |
| checked_at | 예 | `{"format": "date-time", "type": "string"}` |

## RoleAdviceItem

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| role_id | 예 | `{"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}` |
| explanation | 예 | `{"maxLength": 4000, "minLength": 1, "type": "string"}` |
| source_ids | 예 | `{"items": {"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}, "maxItems": 100, "minItems": 1, "type": "array"}` |

## RoleAdviceRequest

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| profile | 예 | `{"$ref": "#/$defs/UserProfile"}` |
| limit | 아니요 | `{"default": 5, "maximum": 20, "minimum": 1, "type": "integer"}` |
| allow_external_ai | 아니요 | `{"default": false, "type": "boolean"}` |

## RoleAdviceResponse

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| items | 예 | `{"items": {"$ref": "#/$defs/RoleAdviceItem"}, "maxItems": 20, "type": "array"}` |
| warnings | 아니요 | `{"items": {"maxLength": 200, "minLength": 1, "type": "string"}, "maxItems": 50, "type": "array"}` |

## RoleProfile

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| id | 예 | `{"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}` |
| name | 예 | `{"maxLength": 200, "minLength": 1, "type": "string"}` |
| tasks | 예 | `{"items": {"maxLength": 200, "minLength": 1, "type": "string"}, "maxItems": 50, "type": "array"}` |
| fields | 예 | `{"items": {"maxLength": 200, "minLength": 1, "type": "string"}, "maxItems": 50, "type": "array"}` |
| preparation_skills | 예 | `{"items": {"maxLength": 200, "minLength": 1, "type": "string"}, "maxItems": 50, "type": "array"}` |
| source_ids | 예 | `{"items": {"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}, "maxItems": 100, "minItems": 1, "type": "array"}` |
| source_url | 예 | `{"format": "uri", "maxLength": 2083, "minLength": 1, "type": "string"}` |
| source_kind | 예 | `{"enum": ["real", "synthetic"], "type": "string"}` |
| checked_at | 예 | `{"format": "date-time", "type": "string"}` |

## Source

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| id | 예 | `{"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}` |
| name | 예 | `{"maxLength": 200, "minLength": 1, "type": "string"}` |
| url | 예 | `{"format": "uri", "maxLength": 2083, "minLength": 1, "type": "string"}` |
| kind | 예 | `{"enum": ["official", "school", "aggregator", "other"], "type": "string"}` |
| source_kind | 예 | `{"enum": ["real", "synthetic"], "type": "string"}` |
| checked_at | 예 | `{"format": "date-time", "type": "string"}` |

## TextRule

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| kind | 예 | `{"const": "text", "type": "string"}` |
| field | 예 | `{"enum": ["school_id", "major", "residence_region"], "type": "string"}` |
| operator | 예 | `{"enum": ["in", "not_in"], "type": "string"}` |
| values | 예 | `{"items": {"maxLength": 200, "minLength": 1, "type": "string"}, "maxItems": 50, "minItems": 1, "type": "array"}` |

## UserProfile

| 필드 | 필수 | 타입·기본값·제한 |
|---|---|---|
| age | 아니요 | `{"anyOf": [{"maximum": 120, "minimum": 0, "type": "integer"}, {"type": "null"}], "default": null}` |
| school_id | 아니요 | `{"anyOf": [{"maxLength": 100, "minLength": 1, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "type": "string"}, {"type": "null"}], "default": null}` |
| school_name | 아니요 | `{"anyOf": [{"maxLength": 200, "minLength": 1, "type": "string"}, {"type": "null"}], "default": null}` |
| education_status | 아니요 | `{"default": "unknown", "enum": ["enrolled", "leave", "graduating", "graduated", "other", "unknown"], "type": "string"}` |
| academic_year | 아니요 | `{"anyOf": [{"maximum": 8, "minimum": 1, "type": "integer"}, {"type": "null"}], "default": null}` |
| major | 아니요 | `{"anyOf": [{"maxLength": 200, "minLength": 1, "type": "string"}, {"type": "null"}], "default": null}` |
| interests | 아니요 | `{"items": {"maxLength": 200, "minLength": 1, "type": "string"}, "maxItems": 50, "type": "array"}` |
| residence_region | 아니요 | `{"anyOf": [{"maxLength": 200, "minLength": 1, "type": "string"}, {"type": "null"}], "default": null}` |
| experience_status | 아니요 | `{"default": "unknown", "enum": ["none", "provided", "unknown"], "type": "string"}` |
| experiences | 아니요 | `{"items": {"$ref": "#/$defs/Experience"}, "maxItems": 30, "type": "array"}` |
| preferred_job_fields | 아니요 | `{"items": {"maxLength": 200, "minLength": 1, "type": "string"}, "maxItems": 50, "type": "array"}` |
| preferred_job_regions | 아니요 | `{"items": {"maxLength": 200, "minLength": 1, "type": "string"}, "maxItems": 50, "type": "array"}` |
| goal | 아니요 | `{"anyOf": [{"maxLength": 4000, "minLength": 1, "type": "string"}, {"type": "null"}], "default": null}` |
