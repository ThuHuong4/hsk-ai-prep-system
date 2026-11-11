import { http } from "../../../../shared/api/httpClient.js";

export function previewExam(maBoDe, token, signal) {
  return http.get(`/api/admin/exams/${maBoDe}/preview`, { token, signal });
}