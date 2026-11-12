import {useEffect, useState} from 'react';
import type { components } from '../../generated/api';
import {nextApplicationBoundary} from './presentation';

type Application = components['schemas']['ApplicationInfo'];
const maxTimeout = 2_147_483_647;

export function useApplicationClock(application?: Application): Date {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    if (!application) return;
    const schedule = application;
    let timer: number | undefined;

    function refresh() {
      window.clearTimeout(timer);
      const current = new Date();
      setNow(current);
      const next = nextApplicationBoundary(schedule, current);
      if (next !== undefined) {
        timer = window.setTimeout(refresh, Math.min(next - current.getTime(), maxTimeout));
      }
    }

    function refreshOnReturn() {
      if (document.visibilityState === 'visible') refresh();
    }

    refresh();
    document.addEventListener('visibilitychange', refreshOnReturn);
    window.addEventListener('focus', refreshOnReturn);
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener('visibilitychange', refreshOnReturn);
      window.removeEventListener('focus', refreshOnReturn);
    };
  }, [application]);

  return now;
}
