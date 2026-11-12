import type { components } from '../../generated/api';

type Profile = components['schemas']['UserProfile'];
export type Experience = components['schemas']['Experience'];
export type EducationStatus = Profile['education_status'];
export type EducationChoice = EducationStatus | 'high_school_graduated';
export type ExperienceInput = Omit<Experience, 'kind'> & {
  kind: Experience['kind'] | 'certificate' | 'english_test';
};
export const experiencePrefixes = {certificate: '자격증 · ', english_test: '영어시험 · '};
export type EmptyExperienceStatus = Exclude<Profile['experience_status'], 'provided'>;
export const maxExperiences = 30;

export function hasAcademicYear(status: EducationChoice): boolean {
  return status === 'enrolled' || status === 'leave' || status === 'graduating';
}

export function splitEntries(value: string): string[] {
  return value.split(',').map(entry => entry.trim()).filter(Boolean);
}

export function updateExperience(experiences: ExperienceInput[], entry: ExperienceInput): ExperienceInput[] {
  if (experiences.some(item => item.id === entry.id)) {
    return experiences.map(item => item.id === entry.id ? entry : item);
  }
  return [...experiences, entry];
}

export function removeExperience(experiences: ExperienceInput[], id: string): ExperienceInput[] {
  return experiences.filter(item => item.id !== id);
}

type BuildResult =
  | {request: components['schemas']['RecommendationRequest']; error?: never}
  | {error: string; request?: never};

export function buildRequest(
  data: FormData,
  educationStatus: EducationChoice,
  emptyExperienceStatus: EmptyExperienceStatus,
  experiences: ExperienceInput[],
): BuildResult {
  const read = (name: string) => String(data.get(name) ?? '').trim();
  const major = read('major');
  const interests = splitEntries(read('interests'));
  const preferredJobFields = splitEntries(read('preferred_job_fields'));
  const goal = read('goal');
  const school = read('school_name');
  const residence = read('residence_region');
  const preferredRegions = splitEntries(read('preferred_job_regions'));
  const ageInput = read('age');
  const yearInput = hasAcademicYear(educationStatus) ? read('academic_year') : '';
  const age = Number(ageInput);
  const year = Number(yearInput);

  if (!major && !interests.length && !preferredJobFields.length && !goal) {
    return {error: '전공, 관심 분야, 희망 직무, 목표 중 하나 이상 입력해 주세요.'};
  }
  if (ageInput && (!/^\d+$/.test(ageInput) || age > 120)) {
    return {error: '나이는 0~120 사이의 정수로 입력해 주세요.'};
  }
  if (yearInput && !/^[1-8]$/.test(yearInput)) {
    return {error: '학년은 1~8 사이의 정수로 입력해 주세요.'};
  }
  if ([major, school, residence].some(value => value.length > 200) || goal.length > 4000) {
    return {error: '입력 길이 제한을 확인해 주세요.'};
  }
  if ([interests, preferredJobFields, preferredRegions].some(
    entries => entries.length > 50 || entries.some(value => value.length > 200),
  )) {
    return {error: '쉼표로 나눈 항목은 최대 50개, 각 200자까지 입력할 수 있어요.'};
  }
  if (experiences.length > maxExperiences || experiences.some(entry => !entry.title.trim())) {
    return {error: '추가한 활동의 이름을 모두 입력해 주세요. 활동은 최대 30개까지 추가할 수 있어요.'};
  }
  const normalizedExperiences = experiences.map((entry): Experience => {
    const title = entry.title.trim();
    const description = entry.description?.trim() || undefined;
    if (entry.kind === 'certificate' || entry.kind === 'english_test') {
      return {...entry, kind: 'other', title: experiencePrefixes[entry.kind] + title, description};
    }
    return {...entry, kind: entry.kind, title, description};
  });
  if (normalizedExperiences.some(entry => entry.title.length > 200 ||
    (entry.description?.length ?? 0) > 4000 ||
    (entry.skills?.length ?? 0) > 50 || entry.skills?.some(skill => skill.length > 200))) {
    return {error: '활동 이름, 설명 또는 사용한 기술의 입력 길이를 확인해 주세요.'};
  }

  return {
    request: {
      profile: {
        major: major || undefined,
        interests,
        preferred_job_fields: preferredJobFields,
        goal: goal || undefined,
        age: ageInput ? age : undefined,
        school_name: school || undefined,
        education_status: educationStatus === 'high_school_graduated' ? 'graduated' : educationStatus,
        academic_year: yearInput ? year : undefined,
        residence_region: residence || undefined,
        preferred_job_regions: preferredRegions,
        experience_status: experiences.length ? 'provided' : emptyExperienceStatus,
        experiences: normalizedExperiences,
      },
      limit: 8,
      allow_external_ai: false,
    },
  };
}
