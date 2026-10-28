import { useEffect, useState } from "react";

/**
 * Load data once per change of `deps`.
 * Returns { status: "loading" | "ready" | "error", data, error }.
 */
export function useApiResource(load, deps) {
  const [state, setState] = useState({ status: "loading", data: null, error: null });

  useEffect(() => {
    let active = true;
    setState({ status: "loading", data: null, error: null });
    load()
      .then((data) => active && setState({ status: "ready", data, error: null }))
      .catch((error) => active && setState({ status: "error", data: null, error }));
    return () => {
      active = false;
    };
    // `load` is recreated every render; the caller lists what it depends on.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}
