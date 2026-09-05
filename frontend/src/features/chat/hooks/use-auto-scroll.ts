import { useEffect, useRef } from "react";

/**
 * Returns a ref for a scroll container that is pinned to the bottom whenever
 * `dep` changes (e.g. a new message arrives).
 */
export function useAutoScroll<T extends HTMLElement>(dep: unknown) {
  const ref = useRef<T>(null);

  useEffect(() => {
    const el = ref.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [dep]);

  return ref;
}
