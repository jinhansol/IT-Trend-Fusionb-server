// src/api/goals.js
// The user's own learning goals (P3). Saved with personalization ON or OFF.
import { apiClient } from "./client";

export async function fetchMyGoals(status = null) {
  const { data } = await apiClient.get("/me/goals", { params: status ? { status } : {} });
  return data; // { items: [{ id, title, status, target_date, achieved_at, target, units }], active_limit }
}

export async function createGoal(goal) {
  const { data } = await apiClient.post("/me/goals", goal); // { title, role?|technology?|track?, target_date? }
  return data;
}

export async function updateGoal(id, changes) {
  const { data } = await apiClient.patch(`/me/goals/${id}`, changes); // { title?, target_date?, status? }
  return data;
}

export async function deleteGoal(id) {
  await apiClient.delete(`/me/goals/${id}`);
}
