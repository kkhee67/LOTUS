import jobs from '../../../../shared/profile_jobs.json' with {type: 'json'};

export const interestGroups = {
  'IT·데이터': ['소프트웨어', '데이터 분석', '인공지능'],
  '디자인·미디어': ['디자인', '영상·콘텐츠', '광고·마케팅'],
  '경영·경제': ['경영·사업', '금융·회계', '유통·물류'],
  '공공·교육·복지': ['공공·행정', '교육', '보건·복지'],
  '공학·환경': ['기계·자동차', '전기·전자', '건축·인테리어', '환경·에너지'],
  '관광·생활': ['관광·서비스', '식품·외식'],
  '연구·진학': ['연구·진학'],
};
export const interestExamples = Object.values(interestGroups).flat();

export const jobExamples: Record<string, string[]> = Object.fromEntries(
  Object.entries(jobs).map(([group, roles]) => [group, Object.keys(roles)]),
);

export const workRegions = [
  '서울', '경기', '인천', '부산', '대구', '대전', '광주', '울산', '세종',
  '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주',
];
