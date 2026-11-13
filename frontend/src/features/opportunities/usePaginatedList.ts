import {useApiTask} from '../useApiTask';
import {appendPage, type LoadedPages, type Page} from './pagination';

export function usePaginatedList<T extends {id: string}>(fetchPage: (offset: number, signal: AbortSignal) => Promise<Page<T>>) {
  const task = useApiTask<LoadedPages<T>>();
  function load() {
    return task.run(async signal => appendPage(task.data, await fetchPage(task.data?.next ?? 0, signal)));
  }
  return {...task, load};
}
