import { http } from "../../../shared/api/httpClient.js";

export function requestPasswordReset(email) {
  return http.post("/api/auth/request-password-reset", { email });
}