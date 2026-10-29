// src/api/personalization.js
// The user's own personalization data (P4): interests and self-rated skills.
// Editable with personalization ON or OFF; there are no recommendations yet.
import { apiClient } from "./client";

export async function fetchTechnologies() {
  const { data } = await apiClient.get("/technologies");
  return data.items; // [{ slug, name, kind }] published, ordered by kind and name
}

export async function fetchMyPersonalization() {
  const { data } = await apiClient.get("/me/personalization");
  return data; // { enabled, profile_status: "off"|"empty"|"ready", interests, skills, limits }
}

export async function setPersonalizationEnabled(enabled) {
  const { data } = await apiClient.patch("/me/settings", { personalization_enabled: enabled });
  return data; // { personalization_enabled, learner_type }
}

export async function replaceInterests(slugs) {
  const { data } = await apiClient.put("/me/personalization/interests", { technologies: slugs });
  return data;
}

export async function replaceSkills(skills) {
  // skills: [{ technology, level: "learning" | "used" | "confident" }]
  const { data } = await apiClient.put("/me/personalization/skills", { skills });
  return data;
}

export async function resetPersonalization() {
  await apiClient.post("/me/personalization/reset");
}
