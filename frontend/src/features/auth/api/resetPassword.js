import { http } from "../../../shared/api/httpClient.js";

export function resetPassword(token, password) {
  return http.post("/api/auth/reset-password", { token, password });
}