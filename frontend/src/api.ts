import type { components, paths } from './generated/api';
import { apiBase } from './api-url.ts';
import { isPreview } from './preview.ts';

export type Health = components['schemas']['HealthResponse'];
export type Options = components['schemas']['OptionsResponse'];
export type Capability = components['schemas']['Capability'];
export type Capabilities = Record<string, Capability>;
export type RecommendationRequest = components['schemas']['RecommendationRequest'];
export type RecommendationResponse = components['schemas']['RecommendationApiResponse'];
export type Opportunity = components['schemas']['Opportunity'];
export type GuidanceFeature = 'career-roles' | 'activity-plan' | 'interview-guide';
type GuidanceOperation<T extends GuidanceFeature> = paths[`/api/v1/${T}`]['post'];
export type GuidanceResponse<T extends GuidanceFeature> =
  GuidanceOperation<T>['responses'][200]['content']['application/json'];
type GuidanceBody<T extends GuidanceFeature> = GuidanceOperation<T>['requestBody']['content']['application/json'];

type ApiErrorKind = 'configuration' | 'validation' | 'unavailable' | 'temporary' | 'network' | 'server' | 'not-found';

const errorMessages: Record<ApiErrorKind, string> = {
  configuration: '서버 주소 설정을 확인해 주세요.',
  validation: '서버에서 입력 형식을 확인하지 못했어요. 입력 내용을 확인해 주세요.',
  unavailable: '이 기능을 준비 중이에요.',
  temporary: '일시적으로 불러오지 못했어요. 다시 시도해 주세요.',
  'not-found': '현재 이 공고를 찾을 수 없어요.',
  network: '서버에 연결할 수 없어요. 연결을 확인하고 다시 시도해 주세요.',
  server: '서버에서 요청을 처리하지 못했어요. 잠시 후 다시 시도해 주세요.',
};

export class ApiError extends Error {
  readonly kind: ApiErrorKind;

  constructor(kind: ApiErrorKind) {
    super(errorMessages[kind]);
    this.kind = kind;
  }
}

export function apiErrorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : errorMessages.server;
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetchResponse(path, init);
  } catch (error) {
    if (error instanceof ApiError || init.signal?.aborted) throw error;
    throw new ApiError('network');
  }

  if (response.status === 422) throw new ApiError('validation');
  // Disabled capabilities are handled before calling the API. A 503 can also
  // mean a transient failure, and the server code is shared by both cases.
  if (response.status === 503) throw new ApiError('temporary');
  if (response.status === 404) throw new ApiError('not-found');
  if (!response.ok) throw new ApiError('server');
  try {
    return await response.json() as T;
  } catch (error) {
    if (init.signal?.aborted) throw error;
    throw new ApiError('server');
  }
}

async function fetchResponse(path: string, init: RequestInit): Promise<Response> {
  if (import.meta.env?.DEV && isPreview) {
    const {previewResponse} = await import('./preview-api');
    init.signal?.throwIfAborted();
    return previewResponse(path, init);
  }

  let base: string;
  try {
    base = apiBase(import.meta.env?.VITE_API_BASE_URL);
  } catch {
    throw new ApiError('configuration');
  }
  return fetch(`${base}${path}`, init);
}

export function getApi<T>(path: '/health' | '/options' | '/capabilities', signal: AbortSignal): Promise<T> {
  return request(path, {signal});
}

export function canRecommend(capability: Capability | undefined): boolean {
  return capability?.enabled === true && capability.implemented === true;
}

export async function recommend(
  capability: Capability | undefined,
  body: RecommendationRequest,
  signal: AbortSignal,
): Promise<RecommendationResponse> {
  return post('/recommendations', capability, body, signal);
}

function post<T>(path: string, capability: Capability | undefined, body: unknown, signal: AbortSignal): Promise<T> {
  if (!canRecommend(capability)) throw new ApiError('unavailable');
  return request(path, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
    signal,
  });
}

export async function getGuidance<T extends GuidanceFeature>(
  feature: T, capability: Capability | undefined, body: GuidanceBody<T>, signal: AbortSignal,
): Promise<GuidanceResponse<T>> {
  return post(`/${feature}`, capability, body, signal);
}

type ListFeature = 'opportunities' | 'resource-links';
type ListResponse<T extends ListFeature> = paths[`/api/v1/${T}`]['get']['responses'][200]['content']['application/json'];

export type OpportunitySearch = Pick<
  NonNullable<paths['/api/v1/opportunities']['get']['parameters']['query']>, 'q' | 'types'
>;
export const maxOpportunityQueryLength = 200;

export async function getList<T extends ListFeature>(
  feature: T, capability: Capability | undefined, offset: number, signal: AbortSignal,
  ...[search]: T extends 'opportunities' ? [search?: OpportunitySearch] : []
): Promise<ListResponse<T>> {
  if (!canRecommend(capability)) throw new ApiError('unavailable');
  const params = new URLSearchParams({limit: '20', offset: String(offset)});
  if (feature === 'opportunities' && search) {
    const query = search.q?.trim();
    if (query && Array.from(query).length > maxOpportunityQueryLength) throw new ApiError('validation');
    if (query) params.set('q', query);
    for (const type of search.types ?? []) params.append('types', type);
  }
  return request(`/${feature}?${params}`, {signal});
}

export async function getOpportunity(id: string, capability: Capability | undefined, signal: AbortSignal): Promise<Opportunity> {
  if (!canRecommend(capability)) throw new ApiError('unavailable');
  return request(`/opportunities/${encodeURIComponent(id)}`, {signal});
}
