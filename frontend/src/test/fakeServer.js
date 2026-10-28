// Test helper: answer apiClient requests from a route table instead of the network.
import { AxiosError } from "axios";
import { apiClient } from "../api/client";

/** routes: { "GET /tracks": () => [status, body] }. Returns a restore function. */
export function installFakeServer(routes) {
  const originalAdapter = apiClient.defaults.adapter;
  apiClient.defaults.adapter = async (config) => {
    const handler = routes[`${config.method.toUpperCase()} ${config.url}`];
    const [status, data] = handler ? handler(config) : [404, { error: { code: "NOT_FOUND" } }];
    const response = { status, data, headers: {}, config, statusText: String(status) };
    if (status >= 400) throw new AxiosError("error", "ERR_BAD_RESPONSE", config, null, response);
    return response;
  };
  return () => {
    apiClient.defaults.adapter = originalAdapter;
  };
}
