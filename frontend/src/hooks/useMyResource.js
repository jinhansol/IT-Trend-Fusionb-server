import { useEffect, useState } from "react";
import { useAuth } from "../auth/useAuth";

const IDLE = { status: "idle", data: null };

/**
 * Load personal data only while logged in; reloads when the login state changes.
 * Returns { status: "idle" (logged out) | "loading" | "ready" | "error", data }.
 */
export function useMyResource(load, deps) {
  const { status: authStatus } = useAuth();
  const [state, setState] = useState(IDLE);

  useEffect(() => {
    let active = true;
    if (authStatus !== "authenticated") {
      setState(IDLE);
      return undefined;
    }
    setState({ status: "loading", data: null });
    load()
      .then((data) => active && setState({ status: "ready", data }))
      .catch(() => active && setState({ status: "error", data: null }));
    return () => {
      active = false;
    };
    // `load` is recreated every render; the caller lists what it depends on.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authStatus, ...deps]);

  return state;
}
