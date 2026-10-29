// src/api/careers.js
// Career exploration (P3). Roles are public; saved candidates are the user's own records.
import { apiClient } from "./client";

const seg = encodeURIComponent;

export async function fetchCareerRoles() {
  const { data } = await apiClient.get("/careers/roles");
  return data.items; // [{ slug, name, summary, core_technologies, technology_count }] in fixed order
}

export async function fetchCareerRole(slug) {
  const { data } = await apiClient.get(`/careers/roles/${seg(slug)}`);
  return data; // { slug, name, summary, description_md, tasks, references, technologies: [{ ..., units }] }
}

export async function fetchMyCandidates() {
  const { data } = await apiClient.get("/me/career-candidates");
  return data; // { items: [{ role: { slug, name, available }, note, saved_at }], limit }
}

export async function saveCandidate(slug, note = null) {
  const { data } = await apiClient.put(`/me/career-candidates/${seg(slug)}`, { note });
  return data;
}

export async function removeCandidate(slug) {
  await apiClient.delete(`/me/career-candidates/${seg(slug)}`);
}
