import { AxiosError } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  apiClient,
  getAccessToken,
  refreshAccessToken,
  setAccessToken,
  setSessionEndedListener,
  toApiError,
} from "./client";

// Fake transport: `routes` maps "METHOD path" to a handler returning [status, body].
function installFakeServer(routes) {
  const calls = [];
  const originalAdapter = apiClient.defaults.adapter;
  apiClient.defaults.adapter = async (config) => {
    const key = `${config.method.toUpperCase()} ${config.url}`;
    calls.push({ key, authorization: config.headers.Authorization ?? null });
    const handler = routes[key];
    if (!handler) throw new Error(`unexpected request ${key}`);
    const [status, data] = await handler(config, calls);
    const response = { status, data, headers: {}, config, statusText: String(status) };
    if (status >= 400) {
      throw new AxiosError(`status ${status}`, "ERR_BAD_RESPONSE", config, null, response);
    }
    return response;
  };
  return { calls, restore: () => (apiClient.defaults.adapter = originalAdapter) };
}

const errorBody = (code) => ({ error: { code, message: code, details: null, request_id: "r1" } });

let server;

beforeEach(() => {
  setAccessToken(null);
  setSessionEndedListener(null);
});

afterEach(() => {
  server?.restore();
  server = null;
});

describe("apiClient", () => {
  it("attaches the in-memory access token", async () => {
    server = installFakeServer({ "GET /me": () => [200, { id: 1 }] });
    setAccessToken("token-1");
    await apiClient.get("/me");
    expect(server.calls[0].authorization).toBe("Bearer token-1");
  });

  it("refreshes once for concurrent 401s and retries every request", async () => {
    server = installFakeServer({
      "GET /me": (config) =>
        config.headers.Authorization === "Bearer fresh" ? [200, { id: 1 }] : [401, errorBody("UNAUTHORIZED")],
      "POST /auth/refresh": async () => {
        await new Promise((resolve) => setTimeout(resolve, 10));
        return [200, { access_token: "fresh", user: { id: 1 } }];
      },
    });
    setAccessToken("stale");

    const results = await Promise.all([apiClient.get("/me"), apiClient.get("/me"), apiClient.get("/me")]);

    expect(results.map((r) => r.data.id)).toEqual([1, 1, 1]);
    expect(server.calls.filter((c) => c.key === "POST /auth/refresh")).toHaveLength(1);
    expect(getAccessToken()).toBe("fresh");
  });

  it("ends the session when the refresh token is rejected", async () => {
    server = installFakeServer({
      "GET /me": () => [401, errorBody("UNAUTHORIZED")],
      "POST /auth/refresh": () => [401, errorBody("REFRESH_TOKEN_INVALID")],
    });
    const ended = vi.fn();
    setSessionEndedListener(ended);
    setAccessToken("stale");

    const error = await apiClient.get("/me").catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(401);
    expect(ended).toHaveBeenCalledTimes(1);
    expect(getAccessToken()).toBeNull();
  });

  it("retries the refresh once after a concurrent rotation", async () => {
    server = installFakeServer({
      "POST /auth/refresh": (_config, calls) =>
        calls.filter((c) => c.key === "POST /auth/refresh").length === 1
          ? [401, errorBody("REFRESH_TOKEN_ROTATED")]
          : [200, { access_token: "after-rotation" }],
    });

    await refreshAccessToken();

    expect(server.calls).toHaveLength(2);
    expect(getAccessToken()).toBe("after-rotation");
  });

  it("does not try to refresh for auth endpoints", async () => {
    server = installFakeServer({
      "POST /auth/login": () => [401, errorBody("INVALID_CREDENTIALS")],
    });

    const error = await apiClient
      .post("/auth/login", {}, { skipAuthRefresh: true })
      .catch((e) => e);

    expect(error.code).toBe("INVALID_CREDENTIALS");
    expect(server.calls.map((c) => c.key)).toEqual(["POST /auth/login"]);
  });

  it("normalizes network failures", () => {
    expect(toApiError(new Error("socket hang up"))).toMatchObject({ status: 0, code: "NETWORK_ERROR" });
    expect(toApiError({ code: "ECONNABORTED" })).toMatchObject({ code: "TIMEOUT" });
  });
});
