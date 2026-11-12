import {useState} from 'react';
import {isPreview} from '../../preview';

const storageKey = 'lotus.saved-opportunity-ids';

function readSaved(): string[] {
  try {
    const values: unknown = JSON.parse(localStorage.getItem(storageKey) ?? '[]');
    return Array.isArray(values) ? [...new Set(values.filter(
      (value): value is string => typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,99}$/.test(value),
    ))] : [];
  } catch {
    return [];
  }
}

export function useSavedOpportunities() {
  const [ids, setIds] = useState(() => isPreview ? [] : readSaved());
  const [storageError, setStorageError] = useState(false);
  function toggle(id: string) {
    const next = ids.includes(id) ? ids.filter(value => value !== id) : [...ids, id];
    setIds(next);
    if (isPreview) return;
    try {
      localStorage.setItem(storageKey, JSON.stringify(next));
      setStorageError(false);
    } catch {
      setStorageError(true);
    }
  }
  return {ids, toggle, storageError};
}

export type SavedOpportunities = ReturnType<typeof useSavedOpportunities>;
