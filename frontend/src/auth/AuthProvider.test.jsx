import { AxiosError } from "axios";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { apiClient, getAccessToken, setAccessToken } from "../api/client";
import { AuthProvider } from "./AuthProvider";
import { useAuth } from "./useAuth";

const ALICE = {
  id: 1,
  email: "alice@example.com",
  display_name: "Alice",
  role: "user",
  created_at: "2026-10-28T00:00:00",
  settings: { personalization_enabled: false },
};

function installFakeServer(routes) {
  const originalAdapter = apiClient.defaults.adapter;
  apiClient.defaults.adapter = async (config) => {
    const handler = routes[`${config.method.toUpperCase()} ${config.url}`];
    const [status, data] = handler ? handler(config) : [404, {}];
    const response = { status, data, headers: {}, config, statusText: String(status) };
    if (status >= 400) throw new AxiosError("error", "ERR_BAD_RESPONSE", config, null, response);
    return response;
  };
  return () => (apiClient.defaults.adapter = originalAdapter);
}

const denied = (code) => [401, { error: { code, message: code } }];

function Probe() {
  const auth = useAuth();
  return (
    <div>
      <span data-testid="status">{auth.status}</span>
      <span data-testid="email">{auth.user?.email ?? ""}</span>
      <button onClick={() => auth.login({ email: "alice@example.com", password: "pw" })}>login</button>
      <button onClick={() => auth.logout()}>logout</button>
    </div>
  );
}

const renderProbe = () =>
  render(
    <AuthProvider>
      <Probe />
    </AuthProvider>
  );

let restore;

beforeEach(() => {
  setAccessToken(null);
  localStorage.clear();
});

afterEach(() => {
  cleanup();
  restore?.();
});

describe("AuthProvider", () => {
  it("restores the session from the refresh cookie on load", async () => {
    restore = installFakeServer({
      "POST /auth/refresh": () => [200, { access_token: "a1" }],
      "GET /me": (config) =>
        config.headers.Authorization === "Bearer a1" ? [200, ALICE] : denied("UNAUTHORIZED"),
    });

    renderProbe();
    expect(screen.getByTestId("status").textContent).toBe("loading");
    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));
    expect(screen.getByTestId("email").textContent).toBe("alice@example.com");
  });

  it("is anonymous when there is no valid refresh cookie", async () => {
    restore = installFakeServer({ "POST /auth/refresh": () => denied("REFRESH_TOKEN_INVALID") });

    renderProbe();
    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("anonymous"));
    expect(getAccessToken()).toBeNull();
  });

  it("logs in, clears legacy storage and logs out", async () => {
    localStorage.setItem("token", "legacy-token");
    localStorage.setItem("user", "{}");
    restore = installFakeServer({
      "POST /auth/refresh": () => denied("REFRESH_TOKEN_INVALID"),
      "POST /auth/login": () => [200, { access_token: "a2", user: ALICE }],
      "GET /me": () => [200, ALICE],
      "POST /auth/logout": () => [204, null],
    });

    renderProbe();
    await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("anonymous"));

    await act(async () => fireEvent.click(screen.getByText("login")));
    expect(screen.getByTestId("status").textContent).toBe("authenticated");
    expect(getAccessToken()).toBe("a2");
    expect(localStorage.getItem("token")).toBeNull();
    expect(localStorage.getItem("user")).toBeNull();

    await act(async () => fireEvent.click(screen.getByText("logout")));
    expect(screen.getByTestId("status").textContent).toBe("anonymous");
    expect(getAccessToken()).toBeNull();
  });
});
