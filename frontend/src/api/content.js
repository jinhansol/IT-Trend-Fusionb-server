// src/api/content.js
// Home (news) and Dev (posts, questions) read API. Public; collection runs separately.
import { apiClient } from "./client";

const seg = encodeURIComponent;
const clean = (params) => Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== ""));

export async function fetchNews({ page = 1, size = 12, tech } = {}) {
  const { data } = await apiClient.get("/news", { params: clean({ page, size, tech }) });
  return data; // { items, page, size, total }
}

export async function fetchDevChannels() {
  const { data } = await apiClient.get("/dev/channels");
  return data.items; // [{ slug, name, kind, has_metrics, sources }]
}

export async function fetchChannelPosts(channel, { sort = "latest", days = 7, page = 1, size = 12, tech } = {}) {
  const { data } = await apiClient.get(`/dev/channels/${seg(channel)}/posts`, {
    params: clean({ sort, days, page, size, tech }),
  });
  return data; // { items, page, size, total }
}

export async function fetchTrends(scope, days = 7) {
  const { data } = await apiClient.get("/trends", { params: { scope, days } });
  return data; // { scope, days, total, fields, technologies, daily, daily_technologies }
}

export async function fetchFeedStatus(scope) {
  const { data } = await apiClient.get("/feed-status", { params: { scope } });
  return data; // { scope, last_updated_at, stale, sources }
}

/** Published Career units that teach a technology (technology-level link). */
export async function fetchTechnologyUnits(slug) {
  const { data } = await apiClient.get(`/technologies/${seg(slug)}/units`);
  return data; // { technology: { slug, name }, units: [{ track, slug, position, title, ... }] }
}
