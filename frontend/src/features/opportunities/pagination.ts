export type Page<T> = {items: T[]; total: number; offset: number; limit: number};
export type LoadedPages<T> = {items: T[]; total: number; next: number};

/** Keep stable order, replace duplicate IDs with their latest returned value. */
export function appendPage<T extends {id: string}>(previous: LoadedPages<T> | undefined, page: Page<T>): LoadedPages<T> {
  return {
    items: [...new Map([...(previous?.items ?? []), ...page.items].map(item => [item.id, item])).values()],
    total: page.total,
    next: page.offset + (page.items.length || page.limit),
  };
}
