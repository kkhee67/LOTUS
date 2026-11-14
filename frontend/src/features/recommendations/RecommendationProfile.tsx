import type { RecommendationRequest } from '../../api';
import {experiencePrefixes} from '../profile/profile';

const education = {
  enrolled: '재학', leave: '휴학', graduating: '졸업 예정', graduated: '졸업', other: '', unknown: '',
};

export function RecommendationProfile({profile}: {profile: RecommendationRequest['profile']}) {
  const {major, interests, preferred_job_fields: roles, education_status: status, academic_year: year, school_name: school} = profile;
  const study = [school, major, year ? `${year}학년` : undefined, education[status]].filter(Boolean).join(' · ');
  const experience = profile.experiences?.map(activity =>
    activity.title.startsWith(experiencePrefixes.english_test) && activity.description
      ? `${activity.title} · ${activity.description}`
      : activity.title,
  ) ?? [];
  return <div className="recommendation-profile">
    <dl className="recommendation-profile-facts">
      {Boolean(roles?.length) && <div><dt>희망 직무</dt><dd>{roles?.join(' · ')}</dd></div>}
      {study && <div><dt>학교·학적</dt><dd>{study}</dd></div>}
      {Boolean(interests?.length) && <div><dt>관심 분야</dt><dd>{interests?.join(' · ')}</dd></div>}
      {profile.goal && <div><dt>목표</dt><dd>{profile.goal}</dd></div>}
      {Boolean(profile.preferred_job_regions?.length) &&
        <div><dt>희망 근무지역</dt><dd>{profile.preferred_job_regions?.join(' · ')}</dd></div>}
      <div><dt>활동·경험</dt><dd>{experience.length ? <ul className="experience-tags">
        {experience.map((name, index) => <li key={index}>{name}</li>)}
      </ul> : profile.experience_status === 'none' ? '활동 없음' : '아직 입력하지 않음'}</dd></div>
    </dl>
  </div>;
}
