// src/api/learning.js
// Public learning catalog (no login needed). Personal progress comes in Phase 4.
import { apiClient } from "./client";

export async function fetchTracks() {
  const { data } = await apiClient.get("/tracks");
  return data.items; // [{ slug, title, description, unit_count }]
}

export async function fetchTrack(trackSlug) {
  const { data } = await apiClient.get(`/tracks/${encodeURIComponent(trackSlug)}`);
  return data; // { slug, title, description, units: [...] }
}

export async function fetchUnit(trackSlug, unitSlug) {
  const { data } = await apiClient.get(
    `/tracks/${encodeURIComponent(trackSlug)}/units/${encodeURIComponent(unitSlug)}`
  );
  return data; // { slug, title, ..., track, activities: [...], prev, next }
}
