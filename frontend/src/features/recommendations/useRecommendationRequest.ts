import {recommend, type Capability, type RecommendationRequest, type RecommendationResponse} from '../../api';
import {useApiTask} from '../useApiTask';

type Submission = {kind: 'loading' | 'error'; message: string}
  | {kind: 'results'; response: RecommendationResponse};

export function useRecommendationRequest(capability: Capability | undefined) {
  const task = useApiTask<RecommendationResponse>();
  const submission: Submission | undefined = task.loading
    ? {kind: 'loading', message: '추천 요청을 보내고 있어요.'}
    : task.error ? {kind: 'error', message: task.error}
    : task.data ? {kind: 'results', response: task.data} : undefined;
  async function loadRecommendations(request: RecommendationRequest) {
    task.reset();
    await task.run(signal => recommend(capability, request, signal));
  }
  return {submission, clearSubmission: task.reset, loadRecommendations};
}
