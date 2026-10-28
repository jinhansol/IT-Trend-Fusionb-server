// src/api/progress.js
// Personal learning progress (login required) and the public unit quiz.
// Every number shown on screen (XP, level, counts, scores) comes from these responses.
import { apiClient } from "./client";

const seg = encodeURIComponent;

export async function fetchMySummary() {
  const { data } = await apiClient.get("/me/summary");
  return data; // { xp, completed_units, in_progress_units, passed_quizzes, continue_unit }
}

export async function fetchMyTrackProgress(trackSlug) {
  const { data } = await apiClient.get(`/me/tracks/${seg(trackSlug)}/progress`);
  return data; // { track_slug, completed_units, total_units, units: [...] }
}

export async function fetchMyUnitProgress(trackSlug, unitSlug) {
  const { data } = await apiClient.get(`/me/tracks/${seg(trackSlug)}/units/${seg(unitSlug)}/progress`);
  return data; // { progress, confirmed_activity_ids, quiz }
}

export async function confirmActivity(activityId) {
  const { data } = await apiClient.post(`/me/activities/${activityId}/confirm`);
  return data; // { activity_id, confirmed_at, progress, granted_rewards, xp }
}

export async function fetchUnitQuiz(trackSlug, unitSlug) {
  const { data } = await apiClient.get(`/tracks/${seg(trackSlug)}/units/${seg(unitSlug)}/quiz`);
  return data; // { id, version, pass_score_percent, questions: [...] } — no answers
}

/** The same clientSubmissionId must be reused when retrying one submission. */
export async function submitQuiz(quizId, clientSubmissionId, answers) {
  const { data } = await apiClient.post(`/me/quizzes/${quizId}/attempts`, {
    client_submission_id: clientSubmissionId,
    answers, // [{ question_id, choice_ids }]
  });
  return data; // QuizResult
}
