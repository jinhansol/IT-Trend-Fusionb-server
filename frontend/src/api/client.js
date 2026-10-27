// src/api/client.js
// DevHub 2.0 shared API client. New API modules should import `apiClient` from here.
// The legacy modules (homeAPI.js, devAPI.js, ...) still call the old backend directly
// and are migrated domain by domain.
import axios from "axios";

const DEFAULT_TIMEOUT_MS = 15000;

export const apiClient = axios.create({
  // "/api" works with the Vite dev proxy locally and a same-origin reverse proxy in production.
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  timeout: DEFAULT_TIMEOUT_MS,
  headers: { "Content-Type": "application/json" },
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

apiClient.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(toApiError(error))
);

export async function fetchHealth() {
  const { data } = await apiClient.get("/health/ready");
  return data; // { status: "ok", database: "ok" }
}
