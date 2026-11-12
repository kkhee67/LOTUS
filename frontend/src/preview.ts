export const isPreview = Boolean(
  import.meta.env?.DEV && typeof window !== 'undefined' &&
    new URLSearchParams(window.location.search).get('preview') === '1',
);

export function showSource(item: {source_kind: 'real' | 'synthetic'}): boolean {
  return isPreview ? item.source_kind === 'synthetic' : item.source_kind === 'real';
}
