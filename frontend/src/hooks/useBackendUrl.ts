import { useEffect, useState } from 'react';
import { backendBase, resolveBackendUrl } from '../lib/backend';

/** Resolved backend base URL ('' in web mode). Re-renders once resolved so that
 *  media URLs (video feed, thumbnails) point at the right origin under Tauri. */
export function useBackendUrl(): string {
  const [base, setBase] = useState<string>(backendBase());
  useEffect(() => {
    let active = true;
    resolveBackendUrl().then((resolved) => {
      if (active) setBase(resolved);
    });
    return () => {
      active = false;
    };
  }, []);
  return base;
}
