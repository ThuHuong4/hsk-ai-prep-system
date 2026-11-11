import { http } from "../../../shared/api/httpClient.js";

export function getExams(maCapDo, signal) {
  return http.get(`/api/exams?ma_cap_do=${encodeURIComponent(maCapDo)}`, { signal });
}