import type { Opportunity } from '../../api';

export const recommendationCategories = {
  all: '전체',
  certifications: '자격증',
  languages: '어학 요건',
  internships: '인턴',
  portfolio: '포트폴리오 활동',
  research: '연구·진학',
  jobs: '채용·기업',
  notices: '학교·기관 공지',
  events: '설명회·박람회',
} as const;

export type RecommendationCategory = keyof typeof recommendationCategories;

const languageTerms = /토익|토플|오픽|텝스|아이엘츠|지텔프|TOEIC|TOEFL|OPIc|\bTEPS\b|IELTS|G[- ]?TELP|어학\s*(?:성적|요건|기준|점수|자격)|영어\s*(?:성적|시험|점수)/i;
const certificationTerms = /자격증|자격\s*보유|정보처리(?:기능사|산업기사|기사)|\b(?:SQLD|ADsP)\b/i;
const researchTerms = /학부\s*연구생|대학원|석사|박사|연구\s*(?:경험|경력|실적)|연구실\s*(?:경험|경력)|\b(?:master['’]?s|ph\.?d\.?|research experience)\b/i;
const researchOpportunities = /학부\s*연구생|연구\s*인턴|연구실\s*(?:인턴|모집|체험)|대학원(?:생)?\s*(?:신입생|입학|모집|설명회|진학)|(?:석사|박사|석박사)\s*과정\s*(?:모집|신입생|입학)|^대학원$/i;
type RequirementSource = Pick<Opportunity, 'requirements' | 'eligibility_rules'>;

function sourceRequirements(opportunity: RequirementSource, pattern: RegExp): string[] {
  const requirements = [...(opportunity.requirements ?? []), ...(opportunity.eligibility_rules ?? []).map(rule => rule.summary)];
  return [...new Set(requirements.filter(text => pattern.test(text)))];
}

export function languageRequirements(opportunity: RequirementSource): string[] {
  return sourceRequirements(opportunity, languageTerms);
}

export function certificationRequirements(opportunity: RequirementSource): string[] {
  return sourceRequirements(opportunity, certificationTerms);
}

export function researchRequirements(opportunity: RequirementSource): string[] {
  return sourceRequirements(opportunity, researchTerms);
}

export function inCategory(
  opportunity: Pick<Opportunity, 'type' | 'subtype' | 'requirements' | 'eligibility_rules' | 'tags'> &
    Partial<Pick<Opportunity, 'title'>>,
  category: RecommendationCategory,
): boolean {
  switch (category) {
    case 'all': return true;
    case 'certifications': return opportunity.type === 'certification' || certificationRequirements(opportunity).length > 0;
    case 'languages': return languageRequirements(opportunity).length > 0;
    case 'internships': return opportunity.type === 'job' && opportunity.subtype === 'internship';
    case 'portfolio': return ['contest', 'competition', 'project', 'training'].includes(opportunity.type);
    case 'research': return [opportunity.title ?? '', ...(opportunity.tags ?? [])].some(text => researchOpportunities.test(text))
      || researchRequirements(opportunity).length > 0;
    case 'jobs': return opportunity.type === 'job' && opportunity.subtype !== 'internship';
    case 'notices': return opportunity.type === 'notice';
    case 'events': return opportunity.type === 'event';
  }
}
