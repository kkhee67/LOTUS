import {useEffect, useState} from 'react';
import type { components } from '../../generated/api';
import {nextApplicationBoundary} from './presentation';

type Application = components['schemas']['ApplicationInfo'];
const maxTimeout = 2_147_483_647;

export function useApplicationClock(application?: Application, sessions?: components['schemas']['ExamSession'][]): Date {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const schedules = sessions ? sessions.map(session => session.application).filter((a): a is Application => !!a)
      : application ? [application] : [];
    if (!schedules.length) return;
    let timer: number | undefined;

    function refresh() {
      window.clearTimeout(timer);
      const current = new Date();
      setNow(current);
      const boundaries = schedules.map(schedule => nextApplicationBoundary(schedule, current))
        .filter((time): time is number => time !== undefined);
      // A countdown also changes at each Seoul midnight before the deadline.
      const day = 86_400_000;
      const midnight = (Math.floor((current.getTime() + 9 * 3600_000) / day) + 1) * day - 9 * 3600_000;
      const next = boundaries.length ? Math.min(midnight, ...boundaries) : undefined;
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
  }, [application, sessions]);

  return now;
}
