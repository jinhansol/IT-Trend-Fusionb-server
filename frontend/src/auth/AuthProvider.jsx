// src/auth/AuthProvider.jsx
// Single source of truth for "who is logged in". The server decides; nothing is
// read from localStorage. On page load the refresh cookie restores the session.
import { useCallback, useEffect, useMemo, useState } from "react";
import * as authApi from "../api/auth";
import { setSessionEndedListener } from "../api/client";
import { AuthContext } from "./AuthContext";

// Keys written by the legacy (school project) login. Removed so old screens do not
// keep using a token that belongs to the old database.
const LEGACY_STORAGE_KEYS = ["token", "user", "firstLogin"];

function clearLegacySession() {
  try {
    LEGACY_STORAGE_KEYS.forEach((key) => localStorage.removeItem(key));
  } catch {
    // Storage can be unavailable (private mode); nothing to clean then.
  }
}

const ANONYMOUS = { status: "anonymous", user: null };

export function AuthProvider({ children }) {
  const [session, setSession] = useState({ status: "loading", user: null });

  const loadUser = useCallback(async () => {
    const user = await authApi.fetchMe();
    setSession({ status: "authenticated", user });
    return user;
  }, []);

  useEffect(() => {
    let active = true;
    setSessionEndedListener(() => setSession(ANONYMOUS));

    (async () => {
      try {
        await authApi.restoreSession();
        const user = await authApi.fetchMe();
        if (active) setSession({ status: "authenticated", user });
      } catch {
        if (active) setSession(ANONYMOUS);
      }
    })();

    return () => {
      active = false;
      setSessionEndedListener(null);
    };
  }, []);

  const login = useCallback(
    async (credentials) => {
      await authApi.login(credentials);
      clearLegacySession();
      return loadUser();
    },
    [loadUser]
  );

  const register = useCallback(
    async (form) => {
      await authApi.register(form);
      clearLegacySession();
      return loadUser();
    },
    [loadUser]
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      clearLegacySession();
      setSession(ANONYMOUS);
    }
  }, []);

  const value = useMemo(
    () => ({ ...session, login, register, logout, reloadUser: loadUser }),
    [session, login, register, logout, loadUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
