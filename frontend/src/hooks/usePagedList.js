import { useCallback, useEffect, useRef, useState } from "react";

/**
 * A list loaded page by page ("더 보기"). `load(page)` returns { items, total }.
 * Reloads from page 1 whenever `deps` change; stale responses are ignored.
 */
export function usePagedList(load, deps) {
  const [state, setState] = useState({ status: "loading", items: [], total: 0, page: 0, error: null });
  const generation = useRef(0);
  const loadRef = useRef(load);
  loadRef.current = load;

  const fetchPage = useCallback(async (page, gen) => {
    try {
      const data = await loadRef.current(page);
      if (gen !== generation.current) return;
      setState((prev) => ({
        status: "ready",
        items: page === 1 ? data.items : [...prev.items, ...data.items],
        total: data.total,
        page,
        error: null,
      }));
    } catch (error) {
      if (gen !== generation.current) return;
      setState((prev) => ({ ...prev, status: page === 1 ? "error" : "ready", error, moreFailed: page > 1 }));
    }
  }, []);

  useEffect(() => {
    generation.current += 1;
    setState({ status: "loading", items: [], total: 0, page: 0, error: null });
    fetchPage(1, generation.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  const loadMore = () => {
    setState((prev) => ({ ...prev, status: "loading-more", moreFailed: false }));
    fetchPage(state.page + 1, generation.current);
  };

  return { ...state, hasMore: state.items.length < state.total, loadMore };
}
