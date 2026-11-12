import {useEffect, useRef, useState} from 'react';
import {apiErrorMessage} from '../api';

export function useApiTask<T>() {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(false);
  const current = useRef<AbortController | null>(null);

  useEffect(() => () => current.current?.abort(), []);

  async function run(load: (signal: AbortSignal) => Promise<T>) {
    current.current?.abort();
    const controller = new AbortController();
    current.current = controller;
    setLoading(true);
    setError(undefined);
    try {
      const result = await load(controller.signal);
      if (!controller.signal.aborted) setData(result);
    } catch (failure) {
      if (!controller.signal.aborted) setError(apiErrorMessage(failure));
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  return {data, error, loading, run};
}
