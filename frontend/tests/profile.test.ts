import assert from 'node:assert/strict';
import test from 'node:test';
import {buildRequest, updateExperience, removeExperience, type Experience} from '../src/features/profile/profile.ts';

function form(values: Record<string, string>) {
  const data = new FormData();
  for (const [key, value] of Object.entries(values)) data.set(key, value);
  return data;
}

for (const field of ['major', 'interests', 'preferred_job_fields', 'goal']) {
  test(`${field} alone is enough; optional values are omitted`, () => {
    const {request} = buildRequest(form({[field]: '  예시  ', school_name: ' '}), 'unknown', 'unknown', []);
    assert.ok(request);
    const serialized = JSON.parse(JSON.stringify(request));
    assert.deepEqual(serialized.profile[field], ['interests', 'preferred_job_fields'].includes(field) ? ['예시'] : '예시');
    for (const omitted of ['age', 'academic_year', 'school_name', 'school_id', 'residence_region']) {
      assert.ok(!(omitted in serialized.profile));
    }
    assert.equal(serialized.allow_external_ai, false);
    assert.equal(serialized.profile.experience_status, 'unknown');
  });
}

test('whitespace and empty list entries do not satisfy the minimum', () => {
  const result = buildRequest(form({major: '  ', interests: ' , ', preferred_job_fields: ',', goal: '\t'}), 'unknown', 'unknown', []);
  assert.match(result.error ?? '', /하나 이상/);
});

test('residence and preferred regions stay separate; academic year is optional', () => {
  const data = form({major: '디자인', academic_year: '2', residence_region: '부산', preferred_job_regions: '서울, 경기'});
  const {request} = buildRequest(data, 'graduated', 'none', []);
  assert.ok(request);
  assert.equal(request.profile.academic_year, undefined);
  assert.equal(request.profile.residence_region, '부산');
  assert.deepEqual(request.profile.preferred_job_regions, ['서울', '경기']);
  assert.equal(buildRequest(data, 'enrolled', 'unknown', []).request?.profile.academic_year, 2);
  assert.match(buildRequest(form({major: '디자인', age: '1.5'}), 'unknown', 'unknown', []).error ?? '', /나이/);
});

test('adding, editing and deleting activities keeps status and kind consistent', () => {
  const data = form({goal: '포트폴리오'});
  const activity: Experience = {id: 'activity-1', kind: 'course_project', title: ' 팀 과제 '};
  assert.equal(buildRequest(data, 'unknown', 'none', []).request?.profile.experience_status, 'none');
  const added = updateExperience([], activity);
  const edited = updateExperience(added, {...activity, title: ' 수정 ', description: '  '});
  const profile = buildRequest(data, 'unknown', 'unknown', edited).request?.profile;
  assert.equal(profile?.experience_status, 'provided');
  assert.deepEqual(profile?.experiences, [{id: 'activity-1', kind: 'course_project', title: '수정', description: undefined}]);
  const removed = removeExperience(edited, activity.id);
  assert.equal(buildRequest(data, 'unknown', 'unknown', removed).request?.profile.experience_status, 'unknown');
  assert.match(buildRequest(data, 'unknown', 'unknown', [{...activity, title: ' '}]).error ?? '', /활동의 이름/);
});

test('high school graduation uses the contract graduate status without an academic year', () => {
  const data = form({goal: '취업', school_name: '예시고등학교', academic_year: '3'});
  const profile = buildRequest(data, 'high_school_graduated', 'unknown', []).request?.profile;
  assert.equal(profile?.education_status, 'graduated');
  assert.equal(profile?.school_name, '예시고등학교');
  assert.equal(profile?.academic_year, undefined);
});

test('certificate and English test drafts preserve their labels in the existing other kind', () => {
  const profile = buildRequest(form({goal: '취업'}), 'unknown', 'unknown', [
    {id: 'activity-1', kind: 'certificate', title: ' 정보처리기능사 '},
    {id: 'activity-2', kind: 'english_test', title: '토익', description: ' 850점 '},
  ]).request?.profile;
  assert.equal(profile?.experience_status, 'provided');
  assert.deepEqual(profile?.experiences, [
    {id: 'activity-1', kind: 'other', title: '자격증 · 정보처리기능사', description: undefined},
    {id: 'activity-2', kind: 'other', title: '영어시험 · 토익', description: '850점'},
  ]);
});
