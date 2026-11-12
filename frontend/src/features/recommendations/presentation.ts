import type { components } from '../../generated/api';

type Application = components['schemas']['ApplicationInfo'];
const seoulDate = new Intl.DateTimeFormat('sv-SE', {
  timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
});

export function applicationStatus(application: Application, now: Date): Application['status'] {
  const today = seoulDate.format(now);
  if (application.status === 'closed' ||
    (application.closes_at && now.getTime() >= Date.parse(application.closes_at)) ||
    (application.closes_on && today > application.closes_on)) return 'closed';

  if (application.status === 'unknown') return 'unknown';
  if ((application.opens_at && now.getTime() < Date.parse(application.opens_at)) ||
    (application.opens_on && today < application.opens_on)) return 'upcoming';
  if (application.status === 'upcoming' && (application.opens_at || application.opens_on)) return 'open';
  return application.status;
}

export function closesToday(application: Application, now: Date): boolean {
  return application.closes_on === seoulDate.format(now) && applicationStatus(application, now) !== 'closed';
}

export function nextApplicationBoundary(application: Application, now: Date): number | undefined {
  if (applicationStatus(application, now) === 'closed') return undefined;

  const {opens_at, opens_on, closes_at, closes_on} = application;
  const midnight = closes_on ? Date.parse(`${closes_on}T00:00:00+09:00`) : NaN;
  const start = opens_at ? Date.parse(opens_at) : opens_on ? Date.parse(`${opens_on}T00:00:00+09:00`) : NaN;
  const boundaries = [Date.parse(closes_at ?? ''), midnight, midnight + 86_400_000];
  if (application.status !== 'unknown') boundaries.push(start);

  const next = Math.min(...boundaries.filter(value => value > now.getTime()));
  return Number.isFinite(next) ? next : undefined;
}

export function sourceHref(value: string): string | undefined {
  try {
    const url = new URL(value);
    if (['http:', 'https:'].includes(url.protocol) && !url.username && !url.password) return url.href;
  } catch {
    return undefined;
  }
}
