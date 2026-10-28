// src/api/client.js
// DevHub 2.0 shared API client. New API modules should import `apiClient` from here.
// The legacy modules (homeAPI.js, devAPI.js, ...) still call the old backend directly
// and are migrated domain by domain.
//
// Auth model: the short-lived access token lives only in memory (this module).
// The refresh token is an httpOnly cookie the browser sends to /api/auth/* only.
import axios from "axios";

const DEFAULT_TIMEOUT_MS = 15000;

export const apiClient = axios.create({
  // "/api" works with the Vite dev proxy locally and a same-origin reverse proxy in production.
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  timeout: DEFAULT_TIMEOUT_MS,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

/**
 * Error thrown by every apiClient call. Mirrors the backend error body:
 * {"error": {"code", "message", "details", "request_id"}}
 */
export class ApiError extends Error {
  constructor({ status, code, message, details = null, requestId = null }) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }
}

export function toApiError(error) {
  if (error instanceof ApiError) return error;

  const response = error?.response;
  if (!response) {
    const timedOut = error?.code === "ECONNABORTED";
    return new ApiError({
      status: 0,
      code: timedOut ? "TIMEOUT" : "NETWORK_ERROR",
      message: timedOut ? "The server took too long to respond." : "Could not reach the server.",
    });
  }

  const body = response.data?.error;
  return new ApiError({
    status: response.status,
    code: body?.code || "HTTP_ERROR",
    message: body?.message || `Request failed with status ${response.status}`,
    details: body?.details ?? null,
    requestId: body?.request_id || response.headers?.["x-request-id"] || null,
  });
}

// --- access token (memory only) ---------------------------------------------------------

let accessToken = null;
let sessionEndedListener = null;

export function setAccessToken(token) {
  accessToken = token || null;
}

export function getAccessToken() {
  return accessToken;
}

/** Called when the session can no longer be refreshed (logged out elsewhere, expired...). */
export function setSessionEndedListener(listener) {
  sessionEndedListener = listener;
}

// --- refresh (single flight) ------------------------------------------------------------

let refreshInFlight = null;

async function requestNewAccessToken() {
  // One retry covers a concurrent rotation by another tab (REFRESH_TOKEN_ROTATED):
  // by then the browser holds the newer cookie.
  for (let attempt = 0; ; attempt += 1) {
    try {
      const { data } = await apiClient.post("/auth/refresh", null, { skipAuthRefresh: true });
      setAccessToken(data.access_token);
      return data;
    } catch (error) {
      const apiError = toApiError(error);
      if (apiError.code === "REFRESH_TOKEN_ROTATED" && attempt === 0) continue;
      setAccessToken(null);
      throw apiError;
    }
  }
}

/** Exchange the refresh cookie for a new access token. Concurrent callers share one request. */
export function refreshAccessToken() {
  if (!refreshInFlight) {
    refreshInFlight = requestNewAccessToken().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

// --- interceptors -----------------------------------------------------------------------

apiClient.interceptors.request.use((config) => {
  if (accessToken && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error?.config;
    const canRetry =
      error?.response?.status === 401 &&
      original &&
      !original.skipAuthRefresh &&
      !original._authRetried;

    if (!canRetry) return Promise.reject(toApiError(error));

    original._authRetried = true;
    try {
      await refreshAccessToken();
    } catch {
      sessionEndedListener?.();
      return Promise.reject(toApiError(error));
    }
    original.headers.Authorization = `Bearer ${accessToken}`;
    return apiClient(original);
  }
);

export async function fetchHealth() {
  const { data } = await apiClient.get("/health/ready");
  return data; // { status: "ok", database: "ok" }
}
