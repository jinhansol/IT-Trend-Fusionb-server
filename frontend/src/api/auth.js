// src/api/auth.js
// DevHub 2.0 authentication API. Tokens never touch localStorage.
import { apiClient, refreshAccessToken, setAccessToken } from "./client";

const NO_REFRESH = { skipAuthRefresh: true };

export async function register({ email, password, displayName }) {
  const { data } = await apiClient.post(
    "/auth/register",
    { email, password, display_name: displayName },
    NO_REFRESH
  );
  setAccessToken(data.access_token);
  return data.user;
}

export async function login({ email, password }) {
  const { data } = await apiClient.post("/auth/login", { email, password }, NO_REFRESH);
  setAccessToken(data.access_token);
  return data.user;
}

export async function logout() {
  try {
    await apiClient.post("/auth/logout", null, NO_REFRESH);
  } finally {
    setAccessToken(null);
  }
}

/** Restore a session from the refresh cookie (page load). Throws ApiError if there is none. */
export async function restoreSession() {
  await refreshAccessToken();
}

export async function fetchMe() {
  const { data } = await apiClient.get("/me");
  return data; // { id, email, display_name, role, created_at, settings: { personalization_enabled } }
}
