import { http } from "../../../shared/api/httpClient.js";

export function getExam(maBoDe, signal) {
  return http.get(`/api/exams/${encodeURIComponent(maBoDe)}`, { signal });
}   