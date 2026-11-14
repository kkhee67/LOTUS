import {useRef, useState, type FormEvent, type Ref} from 'react';
import type {Options, RecommendationRequest} from '../../api';
import {ExampleField, WorkRegionField, ExperienceFields} from './ProfileFields';
import {buildRequest, hasAcademicYear, maxExperiences, removeExperience, updateExperience,
  type EducationChoice, type EmptyExperienceStatus, type ExperienceInput} from './profile';

const educationLabels: Record<EducationChoice, string> = {
  unknown: '선택 안 함', enrolled: '재학', leave: '휴학', graduating: '졸업 예정',
  graduated: '졸업', high_school_graduated: '고등학교 졸업', other: '해당 없음 / 기타',
};


export function ProfileEditor({visible, headingRef, options, confirmed, onConfirm, onChange, onNext, retryConnection}: {
  visible: boolean;
  headingRef: Ref<HTMLHeadingElement>;
  options: {data?: Options; error?: string};
  confirmed?: RecommendationRequest;
  onConfirm: (request: RecommendationRequest | undefined) => void;
  onChange: () => void;
  onNext: () => void;
  retryConnection: () => void;
}) {
  const [educationStatus, setEducationStatus] = useState<EducationChoice>('unknown');
  const [emptyExperienceStatus, setEmptyExperienceStatus] = useState<EmptyExperienceStatus>('unknown');
  const [experiences, setExperiences] = useState<ExperienceInput[]>([]);
  const [inputError, setInputError] = useState<string>();
  const experienceId = useRef(0);
  const educationChoices: EducationChoice[] = (options.data?.education_statuses ?? ['unknown', 'enrolled', 'leave', 'graduating', 'graduated', 'other'])
    .flatMap((status): EducationChoice[] => status === 'graduated' ? [status, 'high_school_graduated'] : [status]);
  const emptyExperienceChoices = (options.data?.experience_statuses ?? ['unknown', 'none'])
    .filter(status => status === 'unknown' || status === 'none');


  function changeProfile() {
    setInputError(undefined);
    onChange();
  }
  function addExperience() {
    changeProfile();
    setEmptyExperienceStatus('unknown');
    const id = `activity-${++experienceId.current}`;
    setExperiences(items => updateExperience(items, {id, kind: 'other', title: ''}));
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const {request, error} = buildRequest(
      new FormData(event.currentTarget), educationStatus, emptyExperienceStatus, experiences,
    );
    onConfirm(request);
    setInputError(error);
  }

  return (
      <main className="page" hidden={!visible}>
        <div className="intro">
          <h1 ref={headingRef} tabIndex={-1}>어떤 일을 준비하고 있나요?</h1>
          <p>지금의 관심이나 목표를 알려주세요. 네 가지 중 하나만 입력해도 시작할 수 있어요.</p>
        </div>

        <form id="profile" className="profile-form" noValidate autoComplete="off" onSubmit={submit} onChange={changeProfile}>
          <section className="basic-section" aria-labelledby="basic-heading">
            <h2 id="basic-heading">기본 정보</h2>
            <div className="fields">
              <label>
                전공
                <input name="major" maxLength={200} placeholder="예: 산업디자인" />
              </label>
              <ExampleField name="interests" label="관심 분야" placeholder="예: 디자인, 데이터" choices={options.data?.fields} />
              <ExampleField name="preferred_job_fields" label="희망 직무·취업 분야" placeholder="직접 입력 예: 웹 개발자" choices={options.data?.fields} />
              <p id="entry-hint" className="field-hint">
                추천 표현을 선택하거나 직접 입력하세요. 여러 항목은 쉼표로 나눠 주세요.
                관심 분야나 희망 직무와 관련된 내용이 공고에서 확인되면 추천에 반영해요.
              </p>
              <label className="wide">
                자유 목표
                <textarea name="goal" maxLength={4000} rows={3} placeholder="예: 다음 학기 전에 첫 포트폴리오를 만들고 싶어요." />
              </label>
            </div>
          </section>

          <details className="optional-section">
            <summary>상세 정보 <span>선택 입력</span></summary>
            <div className="fields">
              <label>
                나이
                <input name="age" inputMode="numeric" maxLength={3} placeholder="예: 24" />
              </label>
              <label>
                학교
                <input name="school_name" maxLength={200} placeholder="고등학교 또는 대학교 이름" />
              </label>
              <label>
                <span id="education-label">학적</span>
                <select aria-labelledby="education-label" value={educationStatus}
                  onChange={event => setEducationStatus(event.target.value as EducationChoice)}>
                  {educationChoices.map(status => <option key={status} value={status}>{educationLabels[status]}</option>)}
                  {!educationChoices.some(status => status === educationStatus) &&
                    <option value={educationStatus}>{educationLabels[educationStatus]}</option>}
                </select>
              </label>
              {hasAcademicYear(educationStatus) && (
                <label>
                  학년
                  <input name="academic_year" inputMode="numeric" maxLength={1} placeholder="1~8" />
                </label>
              )}
              <label>
                거주지역
                <input name="residence_region" maxLength={200} placeholder="예: 부산" />
              </label>
              <WorkRegionField onRemove={changeProfile} />
            </div>
            <fieldset className="experience-section">
              <legend>활동·경험</legend>
              {experiences.length === 0 && (
                <label>
                  <span id="experience-status-label">활동 입력 상태</span>
                  <select aria-labelledby="experience-status-label" value={emptyExperienceStatus}
                    onChange={event => setEmptyExperienceStatus(event.target.value as EmptyExperienceStatus)}>
                    {emptyExperienceChoices.map(status => (
                      <option key={status} value={status}>{status === 'unknown' ? '아직 입력하지 않음' : '활동 없음'}</option>
                    ))}
                  </select>
                </label>
              )}
              {experiences.map((entry, index) => (
                <ExperienceFields key={entry.id} entry={entry} index={index}
                  onEdit={updated => setExperiences(items => updateExperience(items, updated))}
                  onRemove={() => {
                    changeProfile();
                    setExperiences(items => removeExperience(items, entry.id));
                  }} />
              ))}
              <button type="button" className="secondary" onClick={addExperience} disabled={experiences.length >= maxExperiences}>
                활동 추가
              </button>
            </fieldset>
          </details>

          <footer className="form-footer">
            <p className="privacy-note">입력 내용은 이 화면에만 보관돼요. 자유 입력에 연락처나 학번 같은 개인정보를 적지 마세요.</p>
            {options.error && <p className="error" role="alert">선택지를 불러오지 못했어요. 기본 정보는 직접 입력할 수 있어요. {options.error}</p>}
            {inputError && <p className="error" role="alert">{inputError}</p>}
            {confirmed && <p className="feedback" role="status">입력을 확인했어요. 다음으로 이동할 수 있어요.</p>}
            <div className="actions">
              <button type="submit" className={confirmed ? 'secondary' : 'primary'}>입력 확인</button>
              {confirmed && <button type="button" className="primary" onClick={onNext}>다음</button>}
              {options.error && <button type="button" className="secondary" onClick={retryConnection}>연결 다시 확인</button>}
            </div>
          </footer>
        </form>
      </main>
  );
}
