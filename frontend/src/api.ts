import type { components } from './generated/api';
import { apiBase } from './api-url';

export type Health = components['schemas']['HealthResponse'];
export type Options = components['schemas']['OptionsResponse'];
export type Capability = components['schemas']['Capability'];

export async function getApi<T>(path: '/health' | '/options' | '/capabilities', signal: AbortSignal): Promise<T> {
  const base = apiBase(import.meta.env.VITE_API_BASE_URL);
  const response = await fetch(`${base}${path}`, {signal});
  if (!response.ok) throw new Error(`서버 연결 실패 (${response.status})`);
  return response.json() as Promise<T>;
}
