export function apiBase(value: string | undefined): string {
  const url = new URL(value || 'http://localhost:8000');
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password ||
      (url.pathname !== '/' && url.pathname !== '') || url.search || url.hash) {
    throw new Error('VITE_API_BASE_URL에는 경로 없이 서버 주소만 설정하세요.');
  }
  return `${url.origin}/api/v1`;
}
