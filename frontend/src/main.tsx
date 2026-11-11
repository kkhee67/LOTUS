import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {getApi, type Health, type Capability, type Options} from './api';

function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [capabilities, setCapabilities] = useState<Record<string, Capability>>({});
  const [options, setOptions] = useState<Options | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  useEffect(() => {
    const controller = new AbortController();
    const failed = (label: string) => (error: unknown) => {
      if (!controller.signal.aborted) setErrors(old => [...old, `${label}: ${error instanceof Error ? error.message : '연결 실패'}`]);
    };
    void getApi<Health>('/health', controller.signal).then(setHealth).catch(failed('서버'));
    void getApi<Options>('/options', controller.signal).then(setOptions).catch(failed('선택지'));
    void getApi<Record<string, Capability>>('/capabilities', controller.signal).then(setCapabilities).catch(failed('기능 상태'));
    return () => controller.abort();
  }, []);
  return <main style={{maxWidth: 720, margin:'4rem auto', padding:'0 1rem', fontFamily:'sans-serif'}}>
    <h1>LOTUS</h1>
    <p>관심 분야에 맞는 기회와 진로 준비를 안내하는 서비스를 준비하고 있습니다.</p>
    <p role="status">{health ? '서버 연결됨' : '서버 연결 확인 중'}</p>
    {options && <p>지원할 기회 유형: {options.opportunity_types.join(', ')}</p>}
    <h2>개발 준비 상태</h2>
    <p>현재는 공통 기반 검토 단계입니다. 공고 조회와 추천은 아직 제공되지 않습니다.</p>
    <ul>{Object.entries(capabilities).map(([name, state]) => <li key={name}>{name}: {state.enabled && state.implemented ? '사용 가능' : '준비 중'}</li>)}</ul>
    {errors.map((error, i) => <p role="alert" key={i}>{error}</p>)}
  </main>;
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
