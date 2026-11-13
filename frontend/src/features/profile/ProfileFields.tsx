import {useState} from 'react';
import type {Options} from '../../api';
import {workRegions} from './choices';
import {splitEntries, experiencePrefixes, type ExperienceInput} from './profile';

const experienceLabels: Record<ExperienceInput['kind'], string> = {
  course_project: '수업 프로젝트', contest: '공모전·대회', club: '동아리', volunteer: '봉사',
  internship: '인턴', employment: '직장 경력', certificate: '자격증', english_test: '영어시험', other: '기타',
};

export function ExampleField({name, label, placeholder, choices}: {
  name: string;
  label: string;
  placeholder: string;
  choices?: Options['fields'];
}) {
  const [value, setValue] = useState('');
  const entries = splitEntries(value);
  return (
    <div className="choice-field">
      <label>{label}
        <input name={name} value={value} onChange={event => setValue(event.target.value)}
          placeholder={placeholder} aria-describedby="entry-hint" />
      </label>
      {Boolean(choices?.length) && <select aria-label={`${label} 등록 표현 선택`} aria-describedby="entry-hint"
        value="" onChange={event => setValue([...entries, event.target.value].join(', '))}>
        <option value="" disabled>등록된 추천 표현 선택</option>
        {choices?.map(field => <optgroup key={field.code} label={field.label}>
          {[...new Set([field.label, ...(field.aliases ?? [])])].map(choice =>
            <option key={choice} value={choice} disabled={entries.includes(choice)}>{choice}</option>,
          )}
        </optgroup>)}
      </select>}
    </div>
  );
}

export function WorkRegionField({onRemove}: {onRemove: () => void}) {
  const [regions, setRegions] = useState<string[]>([]);
  return (
    <div className="choice-field">
      <label>
        <span id="work-region-label">희망 근무지역</span>
        <select aria-labelledby="work-region-label" value="" onChange={event => {
          setRegions([...regions, event.target.value]);
        }}>
          <option value="" disabled>지역 선택 · 복수 가능</option>
          {workRegions.map(region => <option key={region} value={region} disabled={regions.includes(region)}>{region}</option>)}
        </select>
      </label>
      <input type="hidden" name="preferred_job_regions" value={regions.join(',')} />
      {regions.length > 0 && <ul className="chosen-regions" aria-label="선택한 희망 근무지역">
        {regions.map(region => <li key={region}><button type="button" className="secondary"
          aria-label={`${region} 삭제`} onClick={() => {
            setRegions(regions.filter(value => value !== region));
            onRemove();
          }}>{region} ×</button></li>)}
      </ul>}
    </div>
  );
}

export function ExperienceFields({entry, index, onEdit, onRemove}: {
  entry: ExperienceInput;
  index: number;
  onEdit: (entry: ExperienceInput) => void;
  onRemove: () => void;
}) {
  const prefix = entry.kind === 'certificate' || entry.kind === 'english_test' ? experiencePrefixes[entry.kind] : '';
  return (
    <fieldset className="activity">
      <legend>활동 {index + 1}</legend>
      <div className="fields">
        <label>
          <span id={`${entry.id}-kind-label`}>활동 유형</span>
          <select aria-labelledby={`${entry.id}-kind-label`} value={entry.kind}
            onChange={event => onEdit({...entry, kind: event.target.value as ExperienceInput['kind']})}>
            {Object.entries(experienceLabels).map(([kind, label]) => <option key={kind} value={kind}>{label}</option>)}
          </select>
        </label>
        <label>
          <span id={`${entry.id}-title-label`}>{entry.kind === 'certificate' ? '자격증 이름' : entry.kind === 'english_test' ? '영어시험 이름' : '활동 이름'}</span>
          <input value={entry.title} maxLength={200 - prefix.length} aria-required="true" aria-labelledby={`${entry.id}-title-label`}
            placeholder={entry.kind === 'english_test' ? '예: 토익, 토플, 오픽' : entry.kind === 'certificate' ? '예: 정보처리기능사' : undefined}
            onChange={event => onEdit({...entry, title: event.target.value})} />
        </label>
        <label className="wide">
          {entry.kind === 'english_test' ? '점수·등급 (선택)' : entry.kind === 'certificate' ? '취득일·등급 (선택)' : '활동 내용'}
          <textarea defaultValue={entry.description ?? ''} maxLength={4000} rows={2}
            onChange={event => onEdit({...entry, description: event.target.value})} />
        </label>
        <label className="wide">
          사용한 기술
          <input defaultValue={entry.skills?.join(', ')} placeholder="쉼표로 구분"
            onChange={event => onEdit({...entry, skills: splitEntries(event.target.value)})} />
        </label>
      </div>
      <button type="button" className="secondary" onClick={onRemove} aria-label={`활동 ${index + 1} 삭제`}>삭제</button>
    </fieldset>
  );
}
