// src/api/settings.js
// The caller's own settings. Only the fields sent are changed.
import { apiClient } from "./client";

/** learnerType: "beginner" | "developer" | "exploring" | null (clear). */
export async function updateLearnerType(learnerType) {
  const { data } = await apiClient.patch("/me/settings", { learner_type: learnerType });
  return data; // { personalization_enabled, learner_type }
}
